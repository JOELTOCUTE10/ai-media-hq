"""Free-tier OpenAI-compatible LLM providers (Groq, Mistral, OpenRouter, Gemini).

Honesty rules tested here: a provider without a key raises
ProviderNotConfiguredError naming the exact env var - never a fake completion.
"""
import pytest

from app.core.config import get_settings
from app.integrations.ai_providers import (
    DEFAULT_MODELS,
    FREE_OPENAI_COMPATIBLE,
    OpenAICompatibleProvider,
    ProviderNotConfiguredError,
    get_ai_provider,
)


@pytest.fixture()
def prov():
    """Set AI_PROVIDER with auto-restore."""
    original = get_settings().AI_PROVIDER

    def _set(name):
        get_settings().AI_PROVIDER = name
        return get_settings()
    yield _set
    get_settings().AI_PROVIDER = original


def test_free_provider_registry_shapes():
    assert set(FREE_OPENAI_COMPATIBLE) == {"groq", "mistral", "openrouter", "gemini"}
    base_url, key_attr, default_model = FREE_OPENAI_COMPATIBLE["groq"]
    assert base_url == "https://api.groq.com/openai/v1"
    assert key_attr == "GROQ_API_KEY"
    assert default_model


def test_factory_builds_each_free_provider(prov):
    for name, (base_url, key_attr, default_model) in FREE_OPENAI_COMPATIBLE.items():
        prov(name)
        p = get_ai_provider()
        assert isinstance(p, OpenAICompatibleProvider), name
        assert p.name == name
        assert p.base_url == base_url.rstrip("/")
        assert p.default_model == default_model


def test_missing_key_raises_with_exact_env_var(prov, monkeypatch):
    s = prov("groq")
    monkeypatch.setattr(s, "GROQ_API_KEY", "")
    with pytest.raises(ProviderNotConfiguredError, match="GROQ_API_KEY"):
        get_ai_provider().complete("system", "user")


def test_default_model_used_when_ai_model_empty(prov, monkeypatch):
    s = prov("openrouter")
    monkeypatch.setattr(s, "AI_MODEL", "")
    monkeypatch.setattr(s, "OPENROUTER_API_KEY", "test-key")
    provider = get_ai_provider()
    _, model = provider._credentials()
    assert model == FREE_OPENAI_COMPATIBLE["openrouter"][2]


def test_ai_model_overrides_default(prov, monkeypatch):
    s = prov("mistral")
    monkeypatch.setattr(s, "MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(s, "AI_MODEL", "mistral-medium-latest")
    _, model = get_ai_provider()._credentials()
    assert model == "mistral-medium-latest"


def test_openai_compatible_requires_base_url(prov):
    prov("openai_compatible")
    with pytest.raises(ProviderNotConfiguredError, match="OPENAI_BASE_URL"):
        get_ai_provider()


def test_completion_hits_configured_endpoint(prov, monkeypatch):
    import httpx
    s = prov("groq")
    monkeypatch.setattr(s, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(s, "AI_MODEL", "openai/gpt-oss-120b")

    calls = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "real response"}}],
                    "model": "openai/gpt-oss-120b", "usage": {"prompt_tokens": 7, "completion_tokens": 3}}

    def fake_post(url, **kw):
        calls["url"] = url
        calls["json"] = kw["json"]
        calls["headers"] = kw["headers"]
        return _Resp()

    monkeypatch.setattr(httpx, "post", fake_post)
    result = get_ai_provider().complete("be brief", "say hi")
    assert calls["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert calls["json"]["model"] == "openai/gpt-oss-120b"
    assert calls["headers"]["Authorization"] == "Bearer test-key"
    assert result.text == "real response"
    assert result.prompt_tokens == 7


def test_unconfigured_message_lists_free_options(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "AI_PROVIDER", "unconfigured")
    with pytest.raises(ProviderNotConfiguredError, match="groq"):
        get_ai_provider().complete("s", "u")


def test_default_models_table_complete():
    for name in ("openai", "anthropic", *FREE_OPENAI_COMPATIBLE):
        assert DEFAULT_MODELS[name]
