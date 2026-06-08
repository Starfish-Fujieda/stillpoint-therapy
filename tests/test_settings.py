"""Tests for app.settings — Settings tab, including the PR 2 fields
that were moved from onboarding (human therapist modality,
alexithymia, intellectualizing, communication preference).
"""

import pytest


def test_settings_tab_builds_without_error(project_root):
    """The Settings tab builds (smoke test) — catches missing imports
    and broken Gradio component definitions. Wrapped in a gr.Blocks
    context because create_settings_tab() uses event .change() handlers
    that require a Blocks context."""
    import gradio as gr
    from app.settings import create_settings_tab
    with gr.Blocks():
        tab = create_settings_tab()
    # Should return a Gradio Tab component
    assert tab is not None


def test_human_therapist_modalities_constant():
    """The 7 modality choices match the original onboarding question
    (so users who already chose one see the same vocabulary)."""
    from app.settings import _HUMAN_THERAPIST_MODALITIES
    assert "ACT" in _HUMAN_THERAPIST_MODALITIES
    assert "DBT" in _HUMAN_THERAPIST_MODALITIES
    assert "CBT" in _HUMAN_THERAPIST_MODALITIES
    assert "Not in human therapy" in _HUMAN_THERAPIST_MODALITIES
    assert len(_HUMAN_THERAPIST_MODALITIES) == 7


def test_communication_preferences_constant():
    """The 3 communication preference choices match the new
    onboarding picker's labels (concrete / analytical / mixed)."""
    from app.settings import _COMMUNICATION_PREFERENCES
    assert _COMMUNICATION_PREFERENCES == ["concrete", "analytical", "mixed"]


def test_load_user_profile_returns_empty_on_missing_file(project_root):
    """When user_profile.yaml doesn't exist, _load_user_profile returns
    an empty dict (so Settings UI shows blank/default values)."""
    from app.settings import _load_user_profile
    assert _load_user_profile() == {}


def test_load_user_profile_returns_existing_data(project_root):
    """When user_profile.yaml exists, _load_user_profile returns its
    parsed contents."""
    import yaml
    from app.settings import _load_user_profile
    data = {
        "user": {"name": "Test", "human_therapist_modality": "ACT"},
        "processing_style": {
            "alexithymia_adapted": True,
            "intellectualizing_redirects": True,
            "communication_preference": "direct",
        },
    }
    (project_root / "config" / "user_profile.yaml").write_text(
        yaml.dump(data), encoding="utf-8"
    )
    loaded = _load_user_profile()
    assert loaded["user"]["human_therapist_modality"] == "ACT"
    assert loaded["processing_style"]["alexithymia_adapted"] is True
    assert loaded["processing_style"]["communication_preference"] == "direct"


def test_load_user_profile_handles_empty_file(project_root):
    """An empty user_profile.yaml returns an empty dict."""
    (project_root / "config" / "user_profile.yaml").write_text("", encoding="utf-8")
    from app.settings import _load_user_profile
    assert _load_user_profile() == {}
