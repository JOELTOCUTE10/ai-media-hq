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


class OpenAICompatibleProvider(AIProvider):
    """Any OpenAI-compatible chat completions endpoint: OpenAI itself or the
    free-tier providers (Groq, Mistral, OpenRouter, Gemini's compat layer).
    Never fabricates success: missing keys raise ProviderNotConfiguredError."""
    TIMEOUT = 120.0

    def __init__(self, base_url: str, key_attr: str, provider_name: str, default_model: str):
        self.name = provider_name
        self.base_url = base_url.rstrip("/")
        self.key_attr = key_attr
        self.default_model = default_model

    def _credentials(self) -> tuple[str, str]:
        settings = get_settings()
        api_key = getattr(settings, self.key_attr, "")
        model = settings.AI_MODEL or self.default_model
        if not api_key:
            raise ProviderNotConfiguredError(
                f"'{self.name}' provider selected but {self.key_attr} is not set. "
                f"Add it to .env (get a free key, see docs/INTEGRATIONS.md)."
            )
        return api_key, model

    def complete(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2000) -> Completion:
        api_key, model = self._credentials()
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = httpx.post(f"{self.base_url}/chat/completions", json=payload,
                          headers={"Authorization": f"Bearer {api_key}"},
                          timeout=self.TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return Completion(
            text=data["choices"][0]["message"]["content"],
            model=data.get("model", model),
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
        model = settings.AI_MODEL or DEFAULT_MODELS["anthropic"]
        resp = httpx.post(
            self.API_URL,
            json={"model": model, "system": system,
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
            model=data.get("model", model),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )


class UnconfiguredProvider(AIProvider):
    name = "unconfigured"

    def complete(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2000) -> Completion:
        raise ProviderNotConfiguredError(
            "No AI provider configured. Set AI_PROVIDER in .env: openai|anthropic|groq|mistral|openrouter|gemini|openai_compatible (groq/mistral/openrouter/gemini have free tiers - see docs/INTEGRATIONS.md)."
        )


class FakeProvider(AIProvider):
    """Deterministic provider for TESTS ONLY. Never used in production configuration."""

    name = "fake"

    def complete(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 2000) -> Completion:
        return Completion(text=f"[fake-provider] processed: {user[:120]}", model="fake",
                          prompt_tokens=10, completion_tokens=5)


# Free-tier OpenAI-compatible providers (mnfst/awesome-free-llm-apis).
# name -> (base_url, settings key attr, default model when AI_MODEL is empty)
FREE_OPENAI_COMPATIBLE: dict[str, tuple[str, str, str]] = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-20b"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-small-latest"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openai/gpt-oss-20b:free"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-2.5-flash"),
}

PROVIDERS = {
    AnthropicProvider.name: AnthropicProvider,
    FakeProvider.name: FakeProvider,
    UnconfiguredProvider.name: UnconfiguredProvider,
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    **{name: default for name, (_, _, default) in FREE_OPENAI_COMPATIBLE.items()},
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
    name = settings.AI_PROVIDER.lower()
    if name in FREE_OPENAI_COMPATIBLE:
        base_url, key_attr, default_model = FREE_OPENAI_COMPATIBLE[name]
        return OpenAICompatibleProvider(base_url, key_attr, name, default_model)
    if name == "openai_compatible":
        if not settings.OPENAI_BASE_URL:
            raise ProviderNotConfiguredError(
                "openai_compatible selected but OPENAI_BASE_URL is not set. Point it at the endpoint's /v1 root."
            )
        return OpenAICompatibleProvider(settings.OPENAI_BASE_URL, "OPENAI_API_KEY", name, DEFAULT_MODELS["openai"])
    if name == "openai":
        base = settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
        return OpenAICompatibleProvider(base, "OPENAI_API_KEY", "openai", DEFAULT_MODELS["openai"])
    cls = PROVIDERS.get(name, UnconfiguredProvider)
    return cls()
