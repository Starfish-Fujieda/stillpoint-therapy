"""Tests for stillpoint.session — meta-question logic and usage signals."""

from datetime import datetime, timedelta

import pytest
import yaml

import stillpoint.session as session
from stillpoint.config import load_config
from stillpoint.session import SessionEngine


@pytest.fixture(autouse=True)
def _mock_session_deps(monkeypatch):
    """Stub out memory / LLM / persona calls so sessions run offline."""
    monkeypatch.setattr(session, "get_wake_up_context", lambda: "context")
    monkeypatch.setattr(session, "get_system_prompt", lambda: "system prompt")
    monkeypatch.setattr(session, "send_message", lambda *a, **kw: "Opening message.")
    monkeypatch.setattr(session, "save_session_notes", lambda *a, **kw: True)


def _write_plan(project_root, exit_ramp=None, usage_signals=None, session_log=None):
    """Write a minimal treatment_plan.yaml to the temp config dir."""
    plan = {
        "metadata": {"last_updated": ""},
        "exit_ramp": exit_ramp or {},
        "session_log": session_log or [],
    }
    if usage_signals is not None:
        plan["usage_signals"] = usage_signals
    path = project_root / "config" / "treatment_plan.yaml"
    path.write_text(yaml.dump(plan), encoding="utf-8")
    return plan


# --- meta-question: due vs OVERDUE -------------------------------------------

def test_meta_question_due_not_overdue(project_root, monkeypatch):
    monkeypatch.setattr(session, "get_session_count", lambda: 15)
    _write_plan(project_root, exit_ramp={
        "meta_question_cadence": 5,
        "last_meta_question_session": 10,
    })
    result = SessionEngine().start_session()
    assert result["meta_question_due"] is True
    assert result["meta_question_overdue"] is False


def test_meta_question_overdue(project_root, monkeypatch):
    monkeypatch.setattr(session, "get_session_count", lambda: 17)
    _write_plan(project_root, exit_ramp={
        "meta_question_cadence": 5,
        "last_meta_question_session": 10,
    })
    result = SessionEngine().start_session()
    assert result["meta_question_due"] is True
    assert result["meta_question_overdue"] is True
    assert result["usage_signals"]["meta_question_status"] == "overdue"


def test_meta_question_not_due(project_root, monkeypatch):
    monkeypatch.setattr(session, "get_session_count", lambda: 12)
    _write_plan(project_root, exit_ramp={
        "meta_question_cadence": 5,
        "last_meta_question_session": 10,
    })
    result = SessionEngine().start_session()
    assert result["meta_question_due"] is False
    assert result["meta_question_overdue"] is False


def test_meta_question_overdue_when_never_asked_past_cadence(project_root, monkeypatch):
    monkeypatch.setattr(session, "get_session_count", lambda: 8)
    _write_plan(project_root, exit_ramp={
        "meta_question_cadence": 5,
        "last_meta_question_session": None,
    })
    result = SessionEngine().start_session()
    assert result["meta_question_due"] is True
    assert result["meta_question_overdue"] is True


# --- usage signals -----------------------------------------------------------

def test_usage_signals_count_contacts_last_week(project_root, monkeypatch):
    monkeypatch.setattr(session, "get_session_count", lambda: 3)
    recent = (datetime.now() - timedelta(days=2)).isoformat()
    old = (datetime.now() - timedelta(days=30)).isoformat()
    _write_plan(
        project_root,
        exit_ramp={"meta_question_cadence": 5},
        session_log=[{"date": recent}, {"date": recent}, {"date": old}],
    )
    result = SessionEngine().start_session()
    usage = result["usage_signals"]
    assert usage["contacts_last_week"] == 2
    assert usage["sessions_completed"] == 3


def test_usage_signals_reads_trigger_time_contacts(project_root, monkeypatch):
    monkeypatch.setattr(session, "get_session_count", lambda: 1)
    _write_plan(
        project_root,
        exit_ramp={"meta_question_cadence": 5},
        usage_signals={"trigger_time_contacts": 4, "meta_question_status": ""},
    )
    result = SessionEngine().start_session()
    assert result["usage_signals"]["trigger_time_contacts"] == 4


def test_usage_signals_round_trip_through_treatment_plan(project_root, monkeypatch):
    monkeypatch.setattr(session, "get_session_count", lambda: 5)
    _write_plan(project_root, exit_ramp={
        "meta_question_cadence": 5,
        "last_meta_question_session": None,
    })
    engine = SessionEngine()
    engine.start_session()          # meta-question is due at session 5
    engine.end_session("session notes")

    plan = load_config("treatment_plan.yaml")
    assert "usage_signals" in plan
    assert "trigger_time_contacts" in plan["usage_signals"]
    # A due meta-question is marked addressed for this session.
    assert "session 5" in plan["usage_signals"]["meta_question_status"]
