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
        status_code = 200
        text = ""

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


def test_upstream_error_body_is_surfaced(prov, monkeypatch):
    """A 404 from the provider must surface Google's own explanation,
    not a bare status code the user can't act on."""
    import httpx
    s = prov("gemini")
    monkeypatch.setattr(s, "GEMINI_API_KEY", "AIza" + "k" * 35)

    class _Resp:
        status_code = 404
        text = '{"error": {"message": "models/gemini-bogus is not found", "status": "NOT_FOUND"}}'

    monkeypatch.setattr(httpx, "post", lambda url, **kw: _Resp())
    with pytest.raises(RuntimeError, match="gemini-bogus"):
        get_ai_provider().complete("system", "user")


def test_api_key_whitespace_is_stripped(prov, monkeypatch):
    """Keys pasted from web consoles often carry trailing spaces/newlines -
    they must be stripped before hitting the provider (fix by Joel, Oct 3)."""
    import httpx
    s = prov("groq")
    monkeypatch.setattr(s, "GROQ_API_KEY", "  real-key-with-spaces  \n")

    class _Resp:
        status_code = 200
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}], "model": "m",
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    seen = {}

    def fake_post(url, **kw):
        seen["auth"] = kw["headers"]["Authorization"]
        return _Resp()

    monkeypatch.setattr(httpx, "post", fake_post)
    get_ai_provider().complete("s", "u")
    assert seen["auth"] == "Bearer real-key-with-spaces"


def test_wrong_key_shape_caught_before_api_call(prov, monkeypatch):
    """A key that isn't shaped like a Gemini key (AIza...) must be rejected
    with an actionable message BEFORE wasting a request - Joel's 404 case."""
    import httpx
    s = prov("gemini")
    monkeypatch.setattr(s, "GEMINI_API_KEY", "Ab8Rwrongkey" * 4)  # 48 chars, wrong prefix
    called = []
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: called.append(1))
    with pytest.raises(ProviderNotConfiguredError, match="AIza"):
        get_ai_provider().complete("s", "u")
    assert not called, "must not hit the API with a malformed key"


def test_correct_key_shape_passes_validation(prov, monkeypatch):
    import httpx
    s = prov("gemini")
    monkeypatch.setattr(s, "GEMINI_API_KEY", "AIza" + "x" * 35)
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: type("R", (), {
        "status_code": 200, "text": "",
        "json": lambda self: {"choices": [{"message": {"content": "ok"}}], "model": "m",
                              "usage": {}}})())
    get_ai_provider().complete("s", "u")  # no exception = shape accepted
