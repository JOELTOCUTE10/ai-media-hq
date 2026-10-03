"""AI provider abstraction (Section 46). Agents never embed provider logic.

Providers raise ProviderNotConfiguredError when credentials are missing -
the system NEVER fabricates a successful completion (rule: no fake results).
"""
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


class ProviderNotConfiguredError(RuntimeError):
    """Raised when the selected AI provider has no credentials / is not set up."""


@dataclass
class Completion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class AIProvider:
    name = "abstract"

    def complete(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2000) -> Completion:
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    name = "openai"
    API_URL = "https://api.openai.com/v1/chat/completions"
    TIMEOUT = 120.0

    def complete(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2000) -> Completion:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise ProviderNotConfiguredError(
                "OpenAI provider selected but OPENAI_API_KEY is not set. Add it to .env to enable agents."
            )
        payload = {
            "model": settings.AI_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = httpx.post(self.API_URL, json=payload,
                          headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                          timeout=self.TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return Completion(
            text=data["choices"][0]["message"]["content"],
            model=data.get("model", settings.AI_MODEL),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )


class AnthropicProvider(AIProvider):
    name = "anthropic"
    API_URL = "https://api.anthropic.com/v1/messages"
    TIMEOUT = 120.0

    def complete(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2000) -> Completion:
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            raise ProviderNotConfiguredError(
                "Anthropic provider selected but ANTHROPIC_API_KEY is not set. Add it to .env to enable agents."
            )
        resp = httpx.post(
            self.API_URL,
            json={"model": settings.AI_MODEL, "system": system,
                  "messages": [{"role": "user", "content": user}],
                  "temperature": temperature, "max_tokens": max_tokens},
            headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return Completion(
            text="".join(block.get("text", "") for block in data.get("content", [])),
            model=data.get("model", settings.AI_MODEL),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )


class UnconfiguredProvider(AIProvider):
    name = "unconfigured"

    def complete(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2000) -> Completion:
        raise ProviderNotConfiguredError(
            "No AI provider configured. Set AI_PROVIDER (openai|anthropic) and the matching API key in .env."
        )


class FakeProvider(AIProvider):
    """Deterministic provider for TESTS ONLY. Never used in production configuration."""

    name = "fake"

    def complete(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2000) -> Completion:
        return Completion(text=f"[fake-provider] processed: {user[:120]}", model="fake",
                          prompt_tokens=10, completion_tokens=5)


PROVIDERS = {
    OpenAIProvider.name: OpenAIProvider,
    AnthropicProvider.name: AnthropicProvider,
    FakeProvider.name: FakeProvider,
    UnconfiguredProvider.name: UnconfiguredProvider,
}

# Approximate USD per 1k tokens (prompt, completion) - used for cost records only.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "claude-3-5-haiku-20241022": (0.0008, 0.004),
    "claude-3-5-sonnet-20241022": (0.003, 0.015),
    "fake": (0.0, 0.0),
}


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    cls = PROVIDERS.get(settings.AI_PROVIDER.lower(), UnconfiguredProvider)
    return cls()
