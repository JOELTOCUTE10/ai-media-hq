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
    """Base: agents call complete(); Settings page calls test_connection()."""

    def test_connection(self) -> Completion:
        """Tiny real completion to verify credentials end-to-end."""
        return self.complete("You are a connection test.", "Say OK", temperature=0.0, max_tokens=5)
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

    # Minimum-length sanity check only. Google issues Gemini keys in at least
    # two valid formats ("AIza..." legacy, and newer "AQ...." keys from AI
    # Studio) so we must NOT hard-match a prefix - that previously rejected
    # genuine keys. The real failure mode worth catching is a key copied
    # from a UI that TRUNCATED it with a trailing "..." (visibly too short).
    MIN_KEY_LEN = {
        "gemini": (20, "https://aistudio.google.com/app/apikey"),
    }

    def _credentials(self) -> tuple[str, str]:
        settings = get_settings()
        api_key = getattr(settings, self.key_attr, "").strip()
        model = settings.AI_MODEL or self.default_model
        if not api_key:
            raise ProviderNotConfiguredError(
                f"'{self.name}' provider selected but {self.key_attr} is not set. "
                f"Add it to .env (get a free key, see docs/INTEGRATIONS.md)."
            )
        if api_key.endswith("...") or "…" in api_key:
            raise ProviderNotConfiguredError(
                f"{self.key_attr} looks truncated (ends with '...'). You likely copied "
                f"the shortened on-screen display instead of using the copy-icon button, "
                f"which copies the full key. Re-copy the full key from "
                f"{self.MIN_KEY_LEN.get(self.name, (None, 'the provider dashboard'))[1]}"
            )
        min_len = self.MIN_KEY_LEN.get(self.name)
        if min_len and len(api_key) < min_len[0]:
            raise ProviderNotConfiguredError(
                f"{self.key_attr} is only {len(api_key)} characters - too short to be a "
                f"real {self.name} key. Get the full key (use the copy-icon button, not "
                f"manual selection) at {min_len[1]}"
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
        if resp.status_code >= 400:
            # Surface the provider's own explanation (e.g. Google's 404
            # "model not found") instead of a bare status code.
            raise RuntimeError(
                f"'{self.name}' API error {resp.status_code} from {self.base_url}: {resp.text[:300]}"
            )
        data = resp.json()
        usage = data.get("usage", {})
        choices = data.get("choices") or []
        message = (choices[0].get("message") or {}) if choices else {}
        text = message.get("content")
        if not text and message.get("refusal"):
            raise RuntimeError(f"'{self.name}' refused the request: {message['refusal'][:200]}")
        if not text:
            # 200 but no usable content: surface the real provider payload
            # instead of crashing with a cryptic KeyError.
            raise RuntimeError(
                f"'{self.name}' returned no content (finish_reason="
                f"{choices[0].get('finish_reason') if choices else 'unknown'}): "
                f"{str(data)[:300]}"
            )
        return Completion(
            text=text,
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
        if resp.status_code >= 400:
            raise RuntimeError(
                f"'anthropic' API error {resp.status_code}: {resp.text[:300]}"
            )
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
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-3.8-flash"),
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
