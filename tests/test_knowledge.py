"""Tests for stillpoint.knowledge — no real notebooklm calls made."""

import subprocess
from subprocess import TimeoutExpired

import yaml

import stillpoint.knowledge as knowledge
from stillpoint.knowledge import (
    _ask_notebook,
    _extract_keywords,
    _load_static_knowledge,
    _query_static_knowledge,
    _static_kb_enabled,
    get_available_notebooks,
    get_grounding_status,
    query_knowledge,
    select_relevant_notebooks,
)

# ---------------------------------------------------------------------------
# get_available_notebooks
# ---------------------------------------------------------------------------

def test_get_available_notebooks_empty_when_no_config(project_root):
    assert get_available_notebooks() == []


def test_get_available_notebooks_returns_list(project_root, therapist_config):
    nbs = get_available_notebooks()
    assert len(nbs) == 2
    assert nbs[0]["topic"] == "Anxiety"


# ---------------------------------------------------------------------------
# select_relevant_notebooks
# ---------------------------------------------------------------------------

def test_select_relevant_notebooks_matches_keyword(project_root, therapist_config):
    matched = select_relevant_notebooks("managing worry and panic")
    assert len(matched) == 1
    assert matched[0]["topic"] == "Anxiety"


def test_select_relevant_notebooks_matches_second_notebook(project_root, therapist_config):
    matched = select_relevant_notebooks("client reports low mood")
    assert len(matched) == 1
    assert matched[0]["topic"] == "Depression"


def test_select_relevant_notebooks_no_match_returns_all(project_root, therapist_config):
    matched = select_relevant_notebooks("trauma and PTSD")
    assert len(matched) == 2  # falls back to full list


def test_select_relevant_notebooks_no_notebooks_returns_empty(project_root):
    assert select_relevant_notebooks("anxiety") == []


# ---------------------------------------------------------------------------
# _ask_notebook — subprocess patching
# ---------------------------------------------------------------------------

def _make_completed(returncode=0, stdout="Clinical answer.", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_ask_notebook_success(monkeypatch):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    monkeypatch.setattr(knowledge.subprocess, "run", lambda *a, **kw: _make_completed())
    result = _ask_notebook("nb-123", "What helps with anxiety?")
    assert result == "Clinical answer."


def test_ask_notebook_nonzero_returncode_retries_and_returns_ungrounded(monkeypatch):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    call_count = {"n": 0}

    def fake_run(*a, **kw):
        call_count["n"] += 1
        return _make_completed(returncode=1, stdout="", stderr="error")

    monkeypatch.setattr(knowledge.subprocess, "run", fake_run)
    result = _ask_notebook("nb-123", "question")
    assert result == "[UNGROUNDED]"
    assert call_count["n"] == 3  # retried _MAX_RETRIES times


def test_ask_notebook_timeout_retries_and_returns_ungrounded(monkeypatch):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    call_count = {"n": 0}

    def fake_run(*a, **kw):
        call_count["n"] += 1
        raise TimeoutExpired(cmd="notebooklm", timeout=60)

    monkeypatch.setattr(knowledge.subprocess, "run", fake_run)
    result = _ask_notebook("nb-123", "question")
    assert result == "[UNGROUNDED]"
    assert call_count["n"] == 3


def test_ask_notebook_succeeds_on_second_attempt(monkeypatch):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    call_count = {"n": 0}

    def fake_run(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TimeoutExpired(cmd="notebooklm", timeout=60)
        return _make_completed(stdout="Recovered answer.")

    monkeypatch.setattr(knowledge.subprocess, "run", fake_run)
    result = _ask_notebook("nb-123", "question")
    assert result == "Recovered answer."
    assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# query_knowledge — integration-level
# ---------------------------------------------------------------------------

def test_query_knowledge_no_binary_returns_ungrounded(project_root, therapist_config, monkeypatch):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: None)
    result = query_knowledge("What helps with anxiety?")
    assert result == "[UNGROUNDED]"


def test_query_knowledge_no_notebooks_returns_ungrounded(project_root, monkeypatch):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    result = query_knowledge("What helps with anxiety?")
    assert result == "[UNGROUNDED — no notebooks configured]"


def test_query_knowledge_returns_combined_responses(project_root, therapist_config, monkeypatch):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")

    answers = {"nb-anxiety-123": "CBT is effective for anxiety.", "nb-depression-456": "Ignored."}

    def fake_run(cmd, **kw):
        nb_id = cmd[cmd.index("-n") + 1]
        return _make_completed(stdout=answers.get(nb_id, ""))

    monkeypatch.setattr(knowledge.subprocess, "run", fake_run)
    result = query_knowledge("managing worry")
    # Only anxiety notebook matched
    assert "CBT is effective for anxiety." in result
    assert "Ignored." not in result


def test_query_knowledge_skips_notebook_with_no_id(project_root, monkeypatch):

    config = {
        "therapist": {
            "notebooks": [
                {"topic": "Anxiety", "when_to_query": "anxiety"},
                # notebook_id intentionally missing
            ]
        }
    }
    (project_root / "config" / "therapist.yaml").write_text(yaml.dump(config))
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    result = query_knowledge("anxiety")
    assert result == "[UNGROUNDED]"


def test_query_knowledge_all_notebooks_fail_returns_ungrounded(
    project_root, therapist_config, monkeypatch
):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    monkeypatch.setattr(
        knowledge.subprocess,
        "run",
        lambda *a, **kw: _make_completed(returncode=1, stdout=""),
    )
    result = query_knowledge("anxiety")
    assert result == "[UNGROUNDED]"


# ---------------------------------------------------------------------------
# Static knowledge base — loader, keywords, matching, feature flag
# ---------------------------------------------------------------------------

def test_load_static_knowledge_returns_expected_topics():
    """Static KB loads .md files from data/knowledge/ (excluding README.md)."""
    topics = _load_static_knowledge()
    assert "act_basics" in topics
    assert "intrusive_thoughts" in topics
    # README.md is excluded (it's review-process docs, not content)
    assert "README" not in topics
    # Each topic has non-empty content
    for key, content in topics.items():
        assert content.strip(), f"Topic {key} has empty content"
        assert content.startswith("# "), f"Topic {key} missing H1 title"


def test_extract_keywords_parses_comma_separated_list():
    content = "# Some Topic\n\nkeywords: foo, bar, baz\n\nMore content.\n"
    keywords = _extract_keywords(content)
    assert keywords == ["foo", "bar", "baz"]


def test_extract_keywords_returns_empty_when_no_keywords_line():
    content = "# Some Topic\n\nNo keywords line here.\n"
    assert _extract_keywords(content) == []


def test_extract_keywords_is_case_insensitive():
    content = "# Some Topic\n\nKEYWORDS: Alpha, Beta\n"
    assert _extract_keywords(content) == ["alpha", "beta"]


def test_query_static_knowledge_returns_tagged_content_for_match():
    """A question with matching keywords returns tagged content from that topic."""
    static_kb = {
        "test_topic": "# Test\n\nkeywords: alpha, beta, gamma\n\nTopic content here."
    }
    result = _query_static_knowledge("tell me about alpha and beta", static_kb)
    assert result is not None
    assert "[GROUNDED — static knowledge base, source: test_topic]" in result
    assert "Topic content here." in result


def test_query_static_knowledge_returns_none_for_no_match():
    """A question with no matching keywords returns None."""
    static_kb = {
        "test_topic": "# Test\n\nkeywords: alpha, beta, gamma\n\nTopic content here."
    }
    result = _query_static_knowledge("completely unrelated question", static_kb)
    assert result is None


def test_query_static_knowledge_returns_none_for_empty_kb():
    """An empty static KB returns None."""
    assert _query_static_knowledge("anything", {}) is None


def test_query_static_knowledge_picks_best_match_on_keyword_count():
    """When multiple topics match, the one with more keyword hits wins."""
    static_kb = {
        "weak": "# Weak\n\nkeywords: alpha\n\nWeak content.",
        "strong": "# Strong\n\nkeywords: alpha, beta, gamma\n\nStrong content.",
    }
    result = _query_static_knowledge("alpha beta gamma", static_kb)
    assert result is not None
    assert "source: strong" in result
    assert "Strong content." in result


def test_static_kb_enabled_by_default(monkeypatch):
    """The static KB is enabled when STILLPOINT_STATIC_KB is unset."""
    monkeypatch.delenv("STILLPOINT_STATIC_KB", raising=False)
    assert _static_kb_enabled() is True


def test_static_kb_disabled_by_env_var(monkeypatch):
    """Setting STILLPOINT_STATIC_KB=false disables the static KB."""
    for falsy in ("false", "False", "FALSE", "0", "no", "off", "No"):
        monkeypatch.setenv("STILLPOINT_STATIC_KB", falsy)
        assert _static_kb_enabled() is False, f"Expected False for {falsy!r}"


def test_static_kb_enabled_with_explicit_true(monkeypatch):
    """Setting STILLPOINT_STATIC_KB=true (or any non-falsy value) enables it."""
    for truthy in ("true", "True", "1", "yes", "on", "enabled"):
        monkeypatch.setenv("STILLPOINT_STATIC_KB", truthy)
        assert _static_kb_enabled() is True, f"Expected True for {truthy!r}"


def test_query_knowledge_falls_back_to_static_kb_when_no_binary(project_root, monkeypatch):
    """When the notebooklm binary is missing, the static KB provides grounding."""
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: None)
    result = query_knowledge("How do I defuse from the thought that I am a failure?")
    assert "[GROUNDED — static knowledge base, source: act_basics]" in result


def test_query_knowledge_falls_back_to_static_kb_when_no_notebooks(project_root, monkeypatch):
    """When no notebooks are configured, the static KB provides grounding."""
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    result = query_knowledge("I keep having unwanted intrusive thoughts about violence")
    assert "[GROUNDED — static knowledge base, source: intrusive_thoughts]" in result


def test_query_knowledge_falls_back_to_static_kb_when_all_queries_fail(
    project_root, therapist_config, monkeypatch
):
    """When all notebook queries fail, the static KB provides grounding."""
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    monkeypatch.setattr(
        knowledge.subprocess,
        "run",
        lambda *a, **kw: _make_completed(returncode=1, stdout=""),
    )
    # therapist_config provides notebooks that will all fail; question matches ACT
    result = query_knowledge("How do I defuse from the thought that I am a failure?")
    assert "[GROUNDED — static knowledge base, source: act_basics]" in result


def test_query_knowledge_static_kb_disabled_falls_through(project_root, monkeypatch):
    """When STILLPOINT_STATIC_KB=false, the static KB doesn't fire."""
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: None)
    monkeypatch.setenv("STILLPOINT_STATIC_KB", "false")
    result = query_knowledge("How do I defuse from the thought that I am a failure?")
    assert result == "[UNGROUNDED]"


def test_query_knowledge_off_topic_returns_ungrounded(project_root, monkeypatch):
    """A question with no static KB match falls through to [UNGROUNDED]."""
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: None)
    result = query_knowledge("What is the capital of France?")
    assert result == "[UNGROUNDED]"


# ---------------------------------------------------------------------------
# get_grounding_status — UI status indicator
# ---------------------------------------------------------------------------

def test_get_grounding_status_no_notebooks_static_available():
    """Without notebooks configured, the static KB provides grounding."""
    status = get_grounding_status()
    assert status["notebook_count"] == 0
    assert status["static_available"] is True
    assert "act_basics" in status["static_topics"]
    assert "intrusive_thoughts" in status["static_topics"]


def test_get_grounding_status_with_notebooks(project_root, therapist_config):
    """With configured notebooks, notebook_count reflects the config."""
    status = get_grounding_status()
    # therapist_config fixture provides 2 notebooks with IDs
    assert status["notebook_count"] == 2
    assert status["static_available"] is True


def test_get_grounding_status_static_disabled(monkeypatch):
    """When STILLPOINT_STATIC_KB=false, static_topics is empty."""
    monkeypatch.setenv("STILLPOINT_STATIC_KB", "false")
    status = get_grounding_status()
    assert status["static_available"] is False
    assert status["static_topics"] == []
