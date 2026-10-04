"""Automatic AI provider failover (Section 46, AI_FAILOVER_ENABLED).

Guarantees tested here:
- a quota/auth/model error on the primary NEVER fails a task while another
  configured provider is alive - the chain answers transparently
- the serving provider is recorded on the Completion (costs, logs, audit)
- if EVERY provider fails, the last REAL provider error is raised - never a
  fabricated completion
- AI_FAILOVER_ENABLED=false restores single-provider behavior
- failover candidates run their own default model, so a provider-specific
  AI_MODEL (e.g. a gemini model on groq) can not 404 the whole chain
"""
import pytest

from app.core.config import get_settings
from app.integrations.ai_providers import (
    AIProvider,
    Completion,
    FailoverProvider,
    ProviderNotConfiguredError,
    get_ai_provider,
)


class RecordingProvider(AIProvider):
    """Configurable stub: raises a chosen error or answers with a fixed text."""

    def __init__(self, name: str, error: Exception | None = None, text: str = "done"):
        self.name = name
        self.error = error
        self.text = text
        self.calls = 0

    def complete(self, system, user, temperature=0.4, max_tokens=2000):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return Completion(text=self.text, model=f"{self.name}-model",
                          prompt_tokens=3, completion_tokens=4, provider=self.name)


def test_quota_error_falls_through_to_next_provider():
    dead = RecordingProvider("gemini", error=RuntimeError(
        "'gemini' API error 429 from https://generativelanguage.googleapis.com: "
        "You exceeded your current quota"))
    alive = RecordingProvider("groq", text="from groq")
    chain = FailoverProvider([dead, alive])

    result = chain.complete("system", "user")

    assert dead.calls == 1  # tried first, real error observed
    assert result.text == "from groq"
    assert result.provider == "groq"  # who actually served, recorded


def test_auth_and_model_errors_also_fail_over():
    """A revoked key (401/403) and a retired model (404) are provider-specific:
    the chain must keep going instead of failing the task."""
    quota = RecordingProvider("gemini", error=RuntimeError("'gemini' API error 429: quota"))
    revoked = RecordingProvider("mistral", error=RuntimeError("'mistral' API error 401: bad key"))
    retired = RecordingProvider("openrouter", error=RuntimeError("'openrouter' API error 404: model not found"))
    alive = RecordingProvider("groq", text="rescued")
    chain = FailoverProvider([quota, revoked, retired, alive])

    assert chain.complete("s", "u").text == "rescued"


def test_network_errors_fail_over():
    import httpx as _httpx
    flaky = RecordingProvider("gemini", error=_httpx.ConnectTimeout("timed out"))
    alive = RecordingProvider("groq", text="ok")
    assert FailoverProvider([flaky, alive]).complete("s", "u").text == "ok"


def test_unconfigured_candidates_are_skipped_not_fatal():
    missing = RecordingProvider("mistral", error=ProviderNotConfiguredError("MISTRAL_API_KEY not set"))
    alive = RecordingProvider("groq", text="ok")
    chain = FailoverProvider([missing, alive])
    assert chain.complete("s", "u").text == "ok"


def test_every_provider_failing_raises_the_last_real_error():
    errors = [
        RecordingProvider("gemini", error=RuntimeError("'gemini' API error 429: quota")),
        RecordingProvider("groq", error=RuntimeError("'groq' API error 429: rate limit")),
    ]
    chain = FailoverProvider(errors)
    with pytest.raises(RuntimeError, match="All AI providers failed"):
        chain.complete("s", "u")


def test_failover_disabled_returns_raw_primary(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "AI_PROVIDER", "groq")
    monkeypatch.setattr(s, "GROQ_API_KEY", "k")
    monkeypatch.setattr(s, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(s, "AI_FAILOVER_ENABLED", False)
    assert not hasattr(get_ai_provider(), "chain_names")


def test_failover_enabled_wraps_configured_providers(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(s, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(s, "GROQ_API_KEY", "k")
    monkeypatch.setattr(s, "OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(s, "AI_FAILOVER_ENABLED", True)
    p = get_ai_provider()
    assert isinstance(p, FailoverProvider)
    assert p.chain_names[0] == "gemini"  # primary keeps priority
    assert "groq" in p.chain_names and "openrouter" in p.chain_names
    assert "mistral" not in p.chain_names  # no key configured -> not in chain


def test_candidates_ignore_env_model(monkeypatch):
    """AI_MODEL=gemini-3.8-flash must not be sent to groq in the chain."""
    s = get_settings()
    monkeypatch.setattr(s, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(s, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(s, "GROQ_API_KEY", "k")
    monkeypatch.setattr(s, "AI_MODEL", "gemini-3.8-flash")
    monkeypatch.setattr(s, "AI_FAILOVER_ENABLED", True)
    p = get_ai_provider()
    by_name = {c.name: c for c in p.chain}
    assert by_name["gemini"].use_env_model is True      # primary honors AI_MODEL
    assert by_name["groq"].use_env_model is False      # fallback: own default
    assert by_name["groq"].default_model == "openai/gpt-oss-20b"


def test_primary_success_never_touches_backups():
    healthy = RecordingProvider("groq", text="primary fine")
    backup = RecordingProvider("gemini", text="backup")
    chain = FailoverProvider([healthy, backup])
    chain.complete("s", "u")
    assert backup.calls == 0  # backups are only paid for when actually used
