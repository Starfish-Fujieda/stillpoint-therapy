"""Tests for stillpoint.memory."""

import json
from pathlib import Path

import pytest

import stillpoint.memory as memory


@pytest.fixture(autouse=True)
def _redirect_memory(project_root, monkeypatch):
    sessions_dir = project_root / "config" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(memory, "get_project_root", lambda: project_root)


def test_save_session_notes_creates_files(project_root):
    result = memory.save_session_notes("First session content.")
    assert result is True

    sessions_dir = project_root / "config" / "sessions"
    session_files = list(sessions_dir.glob("session_*.json"))
    assert len(session_files) == 1

    data = json.loads(session_files[0].read_text())
    assert data["content"] == "First session content."
    assert "id" in data
    assert "timestamp" in data


def test_save_session_notes_updates_index(project_root):
    memory.save_session_notes("Session A.")
    memory.save_session_notes("Session B.")

    index_path = project_root / "config" / "sessions" / "index.json"
    index = json.loads(index_path.read_text())
    assert len(index) == 2
    assert index[0]["preview"] == "Session A."
    assert index[1]["preview"] == "Session B."


def test_get_session_count_empty(project_root):
    assert memory.get_session_count() == 0


def test_get_session_count_after_saves(project_root):
    memory.save_session_notes("One")
    memory.save_session_notes("Two")
    assert memory.get_session_count() == 2


def test_get_recent_sessions_returns_content(project_root, session_store):
    results = memory.get_recent_sessions(2)
    assert len(results) == 2
    assert "anxiety" in results[0]
    assert "depression" in results[1]


def test_get_recent_sessions_respects_count(project_root, session_store):
    results = memory.get_recent_sessions(1)
    assert len(results) == 1
    assert "depression" in results[0]


def test_get_recent_sessions_empty_store(project_root):
    assert memory.get_recent_sessions(3) == []


def test_search_sessions_finds_match(project_root, session_store):
    results = memory.search_sessions("anxiety")
    assert len(results) == 1
    assert "anxiety" in results[0]


def test_search_sessions_case_insensitive(project_root, session_store):
    results = memory.search_sessions("DEPRESSION")
    assert len(results) == 1


def test_search_sessions_no_match(project_root, session_store):
    results = memory.search_sessions("unicorn")
    assert results == []


def test_get_wake_up_context_first_session(project_root):
    ctx = memory.get_wake_up_context()
    assert "first session" in ctx.lower()


def test_get_wake_up_context_includes_count(project_root, session_store):
    ctx = memory.get_wake_up_context()
    assert "2" in ctx
    assert "Total sessions" in ctx
