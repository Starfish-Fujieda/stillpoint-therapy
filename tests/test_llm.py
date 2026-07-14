"""Tests for stillpoint.llm — provider dispatch and the MiniMax backend.

The MiniMax tests monkeypatch ``openai.OpenAI`` to avoid real network calls,
following the pattern in tests/test_knowledge.py. The OpenAI SDK is imported
lazily inside ``_send_minimax()``, so patching the ``openai`` module attribute
is sufficient — the function's ``from openai import OpenAI`` resolves at call
time and picks up the patched class.
"""

import os
from types import SimpleNamespace

import pytest

import stillpoint.llm as llm

# ---- helpers ----------------------------------------------------------------


class _FakeCompletions:
    # Tests that want the fake to return reasoning set this before calling.
    # None (default) means the fake response has no reasoning_content, matching
    # what non-reasoning model calls look like.
    reasoning_content: str | None = None

    def create(self, model, messages, **kwargs):
        self.last_call = {"model": model, "messages": messages, **kwargs}
        message = SimpleNamespace(content="ok")
        if self.reasoning_content is not None:
            message.reasoning_content = self.reasoning_content
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeChat:
    def __init__(self):
        self.completions = _FakeCompletions()


class _FakeOpenAI:
    """Records construction args + exposes a fake chat.completions."""

    instances: list = []

    def __init__(self, api_key=None, base_url=None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.extra_kwargs = kwargs
        self.chat = _FakeChat()
        _FakeOpenAI.instances.append(self)


def _install_fake_openai(monkeypatch):
    """Patch openai.OpenAI and reset the recording list."""
    _FakeOpenAI.instances = []
    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    return _FakeOpenAI


# ---- dispatch --------------------------------------------------------------


def test_dispatch_routes_minimax(monkeypatch):
    """send_message('minimax', ...) routes to _send_minimax."""
    fake = _install_fake_openai(monkeypatch)
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    out = llm.send_message(
        "system",
        [{"role": "user", "content": "hi"}],
        {"provider": "minimax"},
    )

    assert out == "ok"
    assert len(fake.instances) == 1


def test_dispatch_unknown_provider_raises():
    """An unknown provider string raises ValueError (regression guard)."""
    with pytest.raises(ValueError, match="Unsupported LLM provider: bogus"):
        llm.send_message(
            "system",
            [{"role": "user", "content": "hi"}],
            {"provider": "bogus"},
        )


# ---- _send_minimax: success path -------------------------------------------


def test_minimax_success(monkeypatch):
    """Happy path: returns the assistant text and sends system+user messages."""
    fake = _install_fake_openai(monkeypatch)
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    out = llm.send_message(
        "be terse",
        [{"role": "user", "content": "ping"}],
        {"provider": "minimax"},
    )

    assert out == "ok"
    instance = fake.instances[0]
    # system prompt is prepended to the message list
    sent_messages = instance.chat.completions.last_call["messages"]
    assert sent_messages[0] == {"role": "system", "content": "be terse"}
    assert {"role": "user", "content": "ping"} in sent_messages
    assert instance.chat.completions.last_call["model"] == "MiniMax-M3"
    # reasoning_split is a MiniMax-specific option that separates the
    # model's thinking from the final answer in the response.
    assert instance.chat.completions.last_call["extra_body"] == {
        "reasoning_split": True
    }


def test_minimax_uses_default_base_url(monkeypatch):
    """No base_url in config → https://api.minimax.io/v1."""
    fake = _install_fake_openai(monkeypatch)
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    llm.send_message(
        "sys",
        [{"role": "user", "content": "x"}],
        {"provider": "minimax"},
    )

    assert fake.instances[0].base_url == "https://api.minimax.io/v1"


def test_minimax_uses_custom_base_url(monkeypatch):
    """Explicit base_url in config overrides the default."""
    fake = _install_fake_openai(monkeypatch)
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    llm.send_message(
        "sys",
        [{"role": "user", "content": "x"}],
        {"provider": "minimax", "base_url": "http://custom:1234/v1"},
    )

    assert fake.instances[0].base_url == "http://custom:1234/v1"


def test_minimax_custom_model(monkeypatch):
    """Custom model id in config is forwarded to the SDK call."""
    fake = _install_fake_openai(monkeypatch)
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    llm.send_message(
        "sys",
        [{"role": "user", "content": "x"}],
        {"provider": "minimax", "model": "minimax-m2.5"},
    )

    assert fake.instances[0].chat.completions.last_call["model"] == "minimax-m2.5"


# ---- _send_minimax: error paths --------------------------------------------


def test_minimax_missing_api_key_raises(monkeypatch):
    """No MINIMAX_API_KEY in env → RuntimeError with a helpful message."""
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    _install_fake_openai(monkeypatch)  # shouldn't even reach the SDK

    with pytest.raises(RuntimeError, match="MINIMAX_API_KEY"):
        llm.send_message(
            "sys",
            [{"role": "user", "content": "x"}],
            {"provider": "minimax"},
        )


def test_minimax_custom_env_var(monkeypatch):
    """If config specifies a different api_key_env, that env var is read."""
    fake = _install_fake_openai(monkeypatch)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("MY_OTHER_KEY", "alt-value")

    llm.send_message(
        "sys",
        [{"role": "user", "content": "x"}],
        {"provider": "minimax", "api_key_env": "MY_OTHER_KEY"},
    )

    assert fake.instances[0].api_key == "alt-value"


def test_minimax_show_thinking_default_off(monkeypatch):
    """With show_thinking absent/False, return only the final content.

    The reasoning content stays in the response object but is NOT
    surfaced to the caller — that's the default, opt-in behavior.
    """
    _install_fake_openai(monkeypatch)
    _FakeCompletions.reasoning_content = "internal scratchpad"
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    try:
        out = llm.send_message(
            "sys",
            [{"role": "user", "content": "x"}],
            {"provider": "minimax"},
        )
    finally:
        _FakeCompletions.reasoning_content = None

    assert out == "ok"
    assert "internal scratchpad" not in out
    assert "thinking" not in out.lower()


def test_minimax_show_thinking_on_includes_reasoning_block(monkeypatch):
    """show_thinking=True wraps the reasoning in a collapsible <details> block."""
    _install_fake_openai(monkeypatch)
    _FakeCompletions.reasoning_content = (
        "step 1: parse input\nstep 2: pick concise answer"
    )
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    try:
        out = llm.send_message(
            "sys",
            [{"role": "user", "content": "x"}],
            {"provider": "minimax", "show_thinking": True},
        )
    finally:
        _FakeCompletions.reasoning_content = None

    assert "ok" in out
    assert "Model thinking" in out
    assert "step 1: parse input" in out
    assert "step 2: pick concise answer" in out
    # It's collapsible (HTML <details>/<summary>) so it doesn't flood the chat
    assert "<details>" in out
    assert "<summary>💭 Model thinking</summary>" in out


def test_minimax_show_thinking_on_graceful_when_no_reasoning(monkeypatch):
    """If the model didn't emit reasoning, the toggle is a no-op."""
    _install_fake_openai(monkeypatch)
    # reasoning_content stays None — the fake won't set it
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    out = llm.send_message(
        "sys",
        [{"role": "user", "content": "x"}],
        {"provider": "minimax", "show_thinking": True},
    )

    assert out == "ok"
    assert "thinking" not in out.lower()


def test_minimax_api_error_is_wrapped(monkeypatch):
    """An exception from the SDK becomes RuntimeError('MiniMax error: ...')."""
    class _ExplodingOpenAI(_FakeOpenAI):
        def __init__(self, *a, **kw):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda *a, **kw: (_ for _ in ()).throw(
                        RuntimeError("upstream 500")
                    )
                )
            )

    monkeypatch.setattr("openai.OpenAI", _ExplodingOpenAI)
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    with pytest.raises(RuntimeError, match=r"MiniMax error: upstream 500"):
        llm.send_message(
            "sys",
            [{"role": "user", "content": "x"}],
            {"provider": "minimax"},
        )


def test_minimax_import_error_message(monkeypatch):
    """If the openai package is missing, raise a user-friendly ImportError."""
    import builtins

    real_import = builtins.__import__

    def _import_blocking_openai(name, *args, **kwargs):
        if name == "openai" or name.startswith("openai."):
            raise ImportError("simulated: openai not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import_blocking_openai)
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    with pytest.raises(ImportError, match="pip install openai"):
        llm.send_message(
            "sys",
            [{"role": "user", "content": "x"}],
            {"provider": "minimax"},
        )


# ---- onboarding integration -------------------------------------------------


def test_build_llm_config_minimax_branch():
    """stillpoint.onboarding.build_llm_config handles the new MiniMax choice."""
    from stillpoint.onboarding import build_llm_config

    cfg = build_llm_config({"infrastructure": {"llm_provider": "MiniMax (M3)"}})

    assert cfg == {
        "provider": "minimax",
        "model": "MiniMax-M3",
        "api_key_env": "MINIMAX_API_KEY",
        "base_url": "https://api.minimax.io/v1",
        "show_thinking": False,
    }


def test_build_llm_config_openrouter_branch():
    """build_llm_config now handles OpenRouter too (gap fix)."""
    from stillpoint.onboarding import build_llm_config

    cfg = build_llm_config({"infrastructure": {"llm_provider": "OpenRouter"}})

    assert cfg == {
        "provider": "openrouter",
        "model": "anthropic/claude-sonnet-4-5",
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
    }


# ---- quick start: provider-aware -------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_quick_start_env(monkeypatch):
    """Each test in this section gets a clean env for the keys it touches."""
    for var in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
        "MINIMAX_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def test_quick_start_anthropic_default(monkeypatch):
    """Default provider writes ANTHROPIC_API_KEY (preserves prior behavior)."""
    from stillpoint.onboarding import generate_quick_start_config

    state = generate_quick_start_config("sk-test")

    assert state["infrastructure"]["llm_provider"] == "Anthropic (Claude)"
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-test"


def test_quick_start_minimax_writes_correct_env(monkeypatch):
    """MiniMax choice writes MINIMAX_API_KEY and the right provider string."""
    from stillpoint.onboarding import generate_quick_start_config

    state = generate_quick_start_config("mini-test", "MiniMax (M3)")

    assert state["infrastructure"]["llm_provider"] == "MiniMax (M3)"
    assert os.environ.get("MINIMAX_API_KEY") == "mini-test"
    # Other envs untouched
    assert os.environ.get("ANTHROPIC_API_KEY") is None


def test_quick_start_openrouter_writes_correct_env(monkeypatch):
    """OpenRouter choice writes OPENROUTER_API_KEY (gap fix)."""
    from stillpoint.onboarding import generate_quick_start_config

    state = generate_quick_start_config("or-test", "OpenRouter")

    assert state["infrastructure"]["llm_provider"] == "OpenRouter"
    assert os.environ.get("OPENROUTER_API_KEY") == "or-test"


def test_quick_start_ollama_no_env_written(monkeypatch):
    """Ollama runs locally — no env var is set even when api_key is provided."""
    from stillpoint.onboarding import generate_quick_start_config

    state = generate_quick_start_config("ignored", "Ollama (local)")

    assert state["infrastructure"]["llm_provider"] == "Ollama (local)"
    # No provider env vars should be set
    for var in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
        "MINIMAX_API_KEY",
    ):
        assert os.environ.get(var) is None


def test_quick_start_blank_key_does_not_set_env(monkeypatch):
    """Empty / whitespace key → no env var, even for a non-Ollama provider."""
    from stillpoint.onboarding import generate_quick_start_config

    state = generate_quick_start_config("   ", "OpenAI (GPT-4)")

    assert state["infrastructure"]["llm_provider"] == "OpenAI (GPT-4)"
    assert os.environ.get("OPENAI_API_KEY") is None


def test_quick_start_invalid_provider_raises(monkeypatch):
    """Unknown provider string raises ValueError (defensive)."""
    from stillpoint.onboarding import generate_quick_start_config

    with pytest.raises(ValueError, match="Unknown Quick Start provider"):
        generate_quick_start_config("x", "BogusProvider")


# ---- settings UI: provider list --------------------------------------------


def test_settings_providers_includes_openrouter_and_minimax():
    """The Settings UI dropdown now includes every supported provider.

    Regression guard for the OpenRouter gap fix and the MiniMax
    addition — the dropdown must stay in sync with llm.py's dispatch.
    """
    from app.settings import _BASE_URL_PROVIDERS, _DEFAULT_KEY_ENVS, _PROVIDERS

    assert "openrouter" in _PROVIDERS
    assert "minimax" in _PROVIDERS
    assert _DEFAULT_KEY_ENVS["openrouter"] == "OPENROUTER_API_KEY"
    assert _DEFAULT_KEY_ENVS["minimax"] == "MINIMAX_API_KEY"
    # openrouter and minimax both need a base_url override
    assert "openrouter" in _BASE_URL_PROVIDERS
    assert "minimax" in _BASE_URL_PROVIDERS


# ---------------------------------------------------------------------------
# DeepSeek — provider dispatch and peak-hour pricing warning
# ---------------------------------------------------------------------------

def test_deepseek_peak_hours_morning_window():
    from datetime import datetime, timedelta, timezone

    from stillpoint.llm import is_deepseek_peak_hours
    beijing = timezone(timedelta(hours=8))
    assert is_deepseek_peak_hours(datetime(2026, 7, 20, 9, 0, tzinfo=beijing)) is True
    assert is_deepseek_peak_hours(datetime(2026, 7, 20, 11, 59, tzinfo=beijing)) is True


def test_deepseek_peak_hours_afternoon_window():
    from datetime import datetime, timedelta, timezone

    from stillpoint.llm import is_deepseek_peak_hours
    beijing = timezone(timedelta(hours=8))
    assert is_deepseek_peak_hours(datetime(2026, 7, 20, 14, 0, tzinfo=beijing)) is True
    assert is_deepseek_peak_hours(datetime(2026, 7, 20, 17, 59, tzinfo=beijing)) is True


def test_deepseek_off_peak_hours():
    from datetime import datetime, timedelta, timezone

    from stillpoint.llm import is_deepseek_peak_hours
    beijing = timezone(timedelta(hours=8))
    for hour in (0, 8, 12, 13, 18, 23):
        assert is_deepseek_peak_hours(
            datetime(2026, 7, 20, hour, 0, tzinfo=beijing)
        ) is False, f"hour {hour} Beijing should be off-peak"


def test_deepseek_peak_hours_converts_timezones():
    """10:00 JST (UTC+9) is 09:00 Beijing — inside the morning window."""
    from datetime import datetime, timedelta, timezone

    from stillpoint.llm import is_deepseek_peak_hours
    jst = timezone(timedelta(hours=9))
    assert is_deepseek_peak_hours(datetime(2026, 7, 20, 10, 0, tzinfo=jst)) is True
    assert is_deepseek_peak_hours(datetime(2026, 7, 20, 9, 0, tzinfo=jst)) is False


def test_deepseek_peak_warning_only_for_deepseek(monkeypatch):
    import stillpoint.llm as llm
    monkeypatch.setattr(llm, "is_deepseek_peak_hours", lambda now=None: True)
    assert llm.deepseek_peak_warning({"provider": "anthropic"}) == ""
    warning = llm.deepseek_peak_warning({"provider": "deepseek"})
    assert "2×" in warning
    assert "Beijing" in warning


def test_deepseek_peak_warning_empty_off_peak(monkeypatch):
    import stillpoint.llm as llm
    monkeypatch.setattr(llm, "is_deepseek_peak_hours", lambda now=None: False)
    assert llm.deepseek_peak_warning({"provider": "deepseek"}) == ""


def test_send_message_dispatches_deepseek(monkeypatch):
    import stillpoint.llm as llm
    called = {}

    def fake_send(system_prompt, messages, config):
        called["config"] = config
        return "ds reply"

    monkeypatch.setattr(llm, "_send_deepseek", fake_send)
    result = llm.send_message(
        "system", [{"role": "user", "content": "hi"}],
        {"provider": "deepseek", "model": "deepseek-chat"},
    )
    assert result == "ds reply"
    assert called["config"]["model"] == "deepseek-chat"


def test_deepseek_missing_api_key_raises(monkeypatch):
    import pytest as _pytest

    from stillpoint.llm import _send_deepseek
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with _pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        _send_deepseek("sys", [], {})


def test_deepseek_peak_warning_shows_jst_windows(monkeypatch):
    import stillpoint.llm as llm
    monkeypatch.setattr(llm, "is_deepseek_peak_hours", lambda now=None: True)
    warning = llm.deepseek_peak_warning({"provider": "deepseek"})
    assert "10:00–13:00 and 15:00–19:00 JST" in warning
