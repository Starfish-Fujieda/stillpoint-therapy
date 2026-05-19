"""Tests for stillpoint.report (non-LLM logic only)."""

import json
from datetime import datetime

import pytest
import yaml

import stillpoint.report as report
from stillpoint.report import (
    _INTERPRETATION_SECTIONS,
    _REPORT_SECTIONS,
    _SECTION_HEADINGS,
    _assemble_report,
    _build_analysis_prompt,
    _load_last_report_timestamp,
    _load_sessions_since,
    _save_last_report_timestamp,
)


@pytest.fixture(autouse=True)
def _redirect_report(project_root, monkeypatch):
    monkeypatch.setattr(report, "get_project_root", lambda: project_root)
    monkeypatch.setattr(report, "get_config_dir", lambda: project_root / "config")
    # Redirect load_config / save_config to use the tmp config dir
    import stillpoint.config as cfg
    monkeypatch.setattr(report, "load_config", cfg.load_config)
    monkeypatch.setattr(report, "save_config", cfg.save_config)


# --- Constants ----------------------------------------------------------------

def test_report_sections_count():
    # Therapist-facing report: raw sections only (interpretive sections moved
    # to the interpretation log).
    assert len(_REPORT_SECTIONS) == 7


def test_report_excludes_interpretive_sections():
    assert "emotional_trajectory" not in _REPORT_SECTIONS
    assert "patterns_observed" not in _REPORT_SECTIONS


def test_report_leads_with_safety():
    assert _REPORT_SECTIONS[0] == "red_flags"


def test_section_headings_match_sections():
    # Every report and interpretation section has a heading, and the headings
    # map covers exactly the union of the two section sets.
    assert set(_REPORT_SECTIONS) <= set(_SECTION_HEADINGS)
    assert set(_INTERPRETATION_SECTIONS) <= set(_SECTION_HEADINGS)
    assert set(_SECTION_HEADINGS) == set(_REPORT_SECTIONS) | set(_INTERPRETATION_SECTIONS)


# --- Timestamp persistence ---------------------------------------------------

def test_last_report_timestamp_none_when_no_file(project_root):
    assert _load_last_report_timestamp() is None


def test_last_report_timestamp_roundtrip(project_root):
    ts = datetime(2024, 3, 15, 12, 0, 0)
    _save_last_report_timestamp(ts)
    loaded = _load_last_report_timestamp()
    assert loaded == ts


# --- Session loading ---------------------------------------------------------

def test_load_sessions_since_no_index(project_root):
    result = _load_sessions_since(None)
    assert result == []


def test_load_sessions_since_returns_all_when_since_none(project_root, session_store):
    sessions_dir = project_root / "config" / "sessions"
    result = _load_sessions_since(None)
    assert len(result) == 2


def test_load_sessions_since_filters_by_date(project_root, session_store):
    cutoff = datetime(2024, 1, 10)
    result = _load_sessions_since(cutoff)
    assert len(result) == 1
    assert "depression" in result[0]["content"]


def test_load_sessions_since_excludes_exactly_at_cutoff(project_root, session_store):
    cutoff = datetime(2024, 1, 15, 14, 0, 0)
    result = _load_sessions_since(cutoff)
    assert result == []


# --- Prompt building ---------------------------------------------------------

def test_build_analysis_prompt_contains_section_keyword(session_store, project_root):
    sessions = [{"timestamp": "2024-01-01T10:00:00", "content": "Some notes."}]
    prompt = _build_analysis_prompt(sessions, "themes_covered", include_quotes=False)
    assert "themes" in prompt.lower()
    assert "Some notes." in prompt


def test_build_analysis_prompt_includes_quotes_flag():
    sessions = [{"timestamp": "2024-01-01", "content": "notes"}]
    with_quotes = _build_analysis_prompt(sessions, "clients_own_words", include_quotes=True)
    without_quotes = _build_analysis_prompt(sessions, "clients_own_words", include_quotes=False)
    assert "[quoted text]" in with_quotes
    assert "[quoted text]" not in without_quotes


def test_build_analysis_prompt_unknown_section_uses_fallback():
    sessions = [{"timestamp": "2024-01-01", "content": "notes"}]
    prompt = _build_analysis_prompt(sessions, "nonexistent_section", include_quotes=False)
    assert "Summarise this section" in prompt


# --- Report assembly ---------------------------------------------------------

def test_assemble_report_contains_frontmatter():
    sections = {"themes_covered": "Anxiety, sleep", "red_flags": "None identified."}
    enabled = ["themes_covered", "red_flags"]
    result = _assemble_report(
        sections, 2, ("2024-01-01", "2024-01-15"), enabled, tool_name="Dr. Test"
    )
    assert result.startswith("---")
    assert "report_date:" in result
    assert "session_count: 2" in result


def test_assemble_report_has_provenance_header():
    result = _assemble_report(
        {"red_flags": "None identified."},
        1,
        ("2024-01-01", "2024-01-01"),
        ["red_flags"],
        tool_name="Dr. Test",
    )
    assert "Provenance" in result
    assert "Dr. Test" in result


def test_assemble_report_includes_enabled_sections():
    sections = {k: f"Content for {k}" for k in _REPORT_SECTIONS}
    enabled = ["themes_covered", "goal_progress"]
    result = _assemble_report(
        sections, 1, ("2024-01-01", "2024-01-01"), enabled, tool_name="Dr. Test"
    )
    assert "Themes Covered" in result
    assert "Goal Progress" in result
    assert "Red Flags" not in result


def test_assemble_report_excludes_disabled_sections():
    sections = {k: f"Content for {k}" for k in _REPORT_SECTIONS}
    enabled = ["red_flags"]
    result = _assemble_report(
        sections, 1, ("2024-01-01", "2024-01-01"), enabled, tool_name="Dr. Test"
    )
    assert "Themes Covered" not in result
    assert "Red Flags" in result


def test_assemble_report_contains_footer():
    sections = {"themes_covered": "Some themes."}
    result = _assemble_report(
        sections, 1, ("2024-01-01", "2024-01-01"), ["themes_covered"], tool_name="Dr. Test"
    )
    assert "generated locally by Stillpoint" in result
    assert "has not been transmitted" in result


# --- generate_session_report (LLM mocked) -----------------------------------

def test_generate_session_report_empty_store_raises(project_root, monkeypatch):
    monkeypatch.setattr(report, "send_message", lambda *a, **kw: "mocked")
    with pytest.raises(ValueError, match="No sessions found"):
        report.generate_session_report(save_to_disk=False)


def test_generate_session_report_with_sessions(project_root, session_store, monkeypatch):
    monkeypatch.setattr(report, "send_message", lambda *a, **kw: "Generated content.")
    result = report.generate_session_report(save_to_disk=False)
    assert "Stillpoint Session Report" in result
    assert "Generated content." in result


def test_generate_session_report_saves_to_disk(project_root, session_store, monkeypatch):
    monkeypatch.setattr(report, "send_message", lambda *a, **kw: "content")
    report.generate_session_report(save_to_disk=True)
    reports_dir = project_root / "reports"
    assert reports_dir.exists()
    assert len(list(reports_dir.glob("*.md"))) == 1


def test_generate_session_report_respects_enabled_sections(
    project_root, session_store, monkeypatch
):
    monkeypatch.setattr(report, "send_message", lambda *a, **kw: "mocked")
    result = report.generate_session_report(
        enabled_sections=["themes_covered"], save_to_disk=False
    )
    assert "Themes Covered" in result
    assert "Red Flags" not in result


# --- generate_interpretation_log (LLM mocked) --------------------------------

def test_generate_interpretation_log_empty_store_raises(project_root, monkeypatch):
    monkeypatch.setattr(report, "send_message", lambda *a, **kw: "mocked")
    with pytest.raises(ValueError, match="No sessions found"):
        report.generate_interpretation_log(save_to_disk=False)


def test_generate_interpretation_log_with_sessions(
    project_root, session_store, monkeypatch
):
    monkeypatch.setattr(report, "send_message", lambda *a, **kw: "Interpretive content.")
    result = report.generate_interpretation_log(save_to_disk=False)
    assert "Interpretation Log" in result
    assert "Not for your therapist" in result
    assert "Emotional Trajectory" in result
    assert "Patterns Observed" in result
    assert "Interpretive content." in result


def test_generate_interpretation_log_saves_to_disk(
    project_root, session_store, monkeypatch
):
    monkeypatch.setattr(report, "send_message", lambda *a, **kw: "content")
    report.generate_interpretation_log(save_to_disk=True)
    reports_dir = project_root / "reports"
    logs = list(reports_dir.glob("interpretation_log_*.md"))
    assert len(logs) == 1


def test_generate_interpretation_log_does_not_advance_report_timestamp(
    project_root, session_store, monkeypatch
):
    # The interpretation log must not consume the report window — only
    # generate_session_report advances the last-report timestamp.
    monkeypatch.setattr(report, "send_message", lambda *a, **kw: "content")
    report.generate_interpretation_log(save_to_disk=True)
    assert _load_last_report_timestamp() is None
