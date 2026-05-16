"""Tests for stillpoint.knowledge — no real notebooklm calls made."""

import subprocess
from subprocess import TimeoutExpired

import pytest
import yaml

import stillpoint.knowledge as knowledge
from stillpoint.knowledge import (
    _ask_notebook,
    get_available_notebooks,
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
    import yaml

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


def test_query_knowledge_all_notebooks_fail_returns_ungrounded(project_root, therapist_config, monkeypatch):
    monkeypatch.setattr(knowledge.shutil, "which", lambda _: "/usr/bin/notebooklm")
    monkeypatch.setattr(knowledge.subprocess, "run", lambda *a, **kw: _make_completed(returncode=1, stdout=""))
    result = query_knowledge("anxiety")
    assert result == "[UNGROUNDED]"
