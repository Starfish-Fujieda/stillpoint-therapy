"""Tests for stillpoint.onboarding — onboarding phases, quick start, picker.

PR 2 reduced the onboarding from 6 phases to 4 + an end-of-wizard
picker, and added the Quick Start flow. These tests cover the new
shapes and the picker mapping.
"""

import os

import pytest

import stillpoint.onboarding as onboarding
from stillpoint.onboarding import (
    PHASES,
    PICKER_CHOICES,
    PICKER_TO_COMMUNICATION,
    generate_quick_start_config,
    get_phase_questions,
)


# ---------------------------------------------------------------------------
# PHASES — reduced from 6 to 4 (PR 2, Fix 4)
# ---------------------------------------------------------------------------

def test_phases_has_exactly_four_items():
    """The wizard now has 4 phases (was 6)."""
    assert len(PHASES) == 4


def test_phases_contains_expected_names():
    """The 4 phases are welcome, character_design, infrastructure, notebooks."""
    assert PHASES == [
        "welcome",
        "character_design",
        "infrastructure",
        "notebooks",
    ]


def test_phases_removed_sources():
    """The 'sources' phase was removed (moved to Settings, on-demand)."""
    assert "sources" not in PHASES


def test_phases_removed_processing_style():
    """The 'processing_style' phase was removed (most fields moved to Settings,
    communication_preference became the end-of-wizard picker)."""
    assert "processing_style" not in PHASES


# ---------------------------------------------------------------------------
# character_design — human_therapist_modality removed (moved to Settings)
# ---------------------------------------------------------------------------

def test_character_design_questions_no_human_therapist_modality():
    """The human_therapist_modality question moved to Settings in PR 2."""
    questions = get_phase_questions("character_design")
    question_ids = [q["id"] for q in questions]
    assert "human_therapist_modality" not in question_ids


# ---------------------------------------------------------------------------
# sources phase — fully removed
# ---------------------------------------------------------------------------

def test_sources_phase_returns_empty():
    """The 'sources' phase is gone; get_phase_questions should return []."""
    assert get_phase_questions("sources") == []


# ---------------------------------------------------------------------------
# processing_style phase — fully removed
# ---------------------------------------------------------------------------

def test_processing_style_phase_returns_empty():
    """The 'processing_style' phase is gone; questions are now in
    Settings (alexithymia, intellectualizing) or the picker
    (communication_preference)."""
    assert get_phase_questions("processing_style") == []


# ---------------------------------------------------------------------------
# generate_quick_start_config — PR 2, Fix 3
# ---------------------------------------------------------------------------

def test_quick_start_config_default_specializations(monkeypatch):
    """Quick Start defaults to ACT — Defusion & Values (matches PR 1's
    static KB scope)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    state = generate_quick_start_config(None)
    assert state["character_design"]["specializations"] == [
        "ACT — Defusion & Values"
    ]


def test_quick_start_config_default_therapist_name(monkeypatch):
    """Quick Start defaults therapist name to 'Your Therapist'."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    state = generate_quick_start_config(None)
    assert state["character_design"]["name"] == "Your Therapist"


def test_quick_start_config_default_directness_balanced(monkeypatch):
    """Quick Start defaults directness to 'Balanced'."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    state = generate_quick_start_config(None)
    assert state["character_design"]["directness"] == "Balanced"


def test_quick_start_config_default_structure_mixed(monkeypatch):
    """Quick Start defaults structure to 'Mixed'."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    state = generate_quick_start_config(None)
    assert state["character_design"]["structure"] == "Mixed"


def test_quick_start_config_default_llm_anthropic(monkeypatch):
    """Quick Start defaults LLM provider to Anthropic (Claude)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    state = generate_quick_start_config(None)
    assert state["infrastructure"]["llm_provider"] == "Anthropic (Claude)"


def test_quick_start_config_sets_consent(monkeypatch):
    """Quick Start implies consent (user clicked the button)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    state = generate_quick_start_config(None)
    assert state["welcome"]["consent"] is True


def test_quick_start_config_sets_env_var_when_key_provided(monkeypatch):
    """A non-blank API key is written to ANTHROPIC_API_KEY in the
    current process so the LLM call works in this Gradio session."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    generate_quick_start_config("sk-test-12345")
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-test-12345"


def test_quick_start_config_strips_whitespace(monkeypatch):
    """Leading/trailing whitespace in the API key is stripped before
    being written to the env var."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    generate_quick_start_config("  sk-test-stripped  ")
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-test-stripped"


def test_quick_start_config_handles_none_api_key(monkeypatch):
    """A None API key does NOT set the env var. Chat will show the
    'API key required' banner."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    generate_quick_start_config(None)
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_quick_start_config_handles_blank_api_key(monkeypatch):
    """An empty-string API key does NOT set the env var."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    generate_quick_start_config("")
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_quick_start_config_handles_whitespace_only_api_key(monkeypatch):
    """A whitespace-only API key does NOT set the env var."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    generate_quick_start_config("   ")
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_quick_start_config_notebooks_confirmed(monkeypatch):
    """Quick Start confirms the notebook plan (required by the
    notebooks phase's is_phase_complete check)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    state = generate_quick_start_config(None)
    assert state.get("notebooks_confirmed", {}).get("confirm_notebooks") is True


def test_quick_start_config_includes_required_sections(monkeypatch):
    """Quick Start state has all sections that generate_all_config expects:
    welcome, character_design, infrastructure, notebooks_confirmed."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    state = generate_quick_start_config(None)
    assert "welcome" in state
    assert "character_design" in state
    assert "infrastructure" in state
    assert "notebooks_confirmed" in state


# ---------------------------------------------------------------------------
# Picker — PR 2, Fix 4
# ---------------------------------------------------------------------------

def test_picker_choices_has_three_options():
    """The picker has 3 buttons: concrete, analytical, mixed."""
    assert len(PICKER_CHOICES) == 3
    assert set(PICKER_CHOICES) == {"concrete", "analytical", "mixed"}


def test_picker_to_communication_mapping():
    """Per the friction-reduction plan, the picker choice maps to
    the OLD communication_preference labels so build_processing_style
    can consume it unchanged."""
    assert (
        PICKER_TO_COMMUNICATION["concrete"] == "Direct and straightforward"
    )
    assert (
        PICKER_TO_COMMUNICATION["analytical"] == "Gentle and indirect"
    )
    assert PICKER_TO_COMMUNICATION["mixed"] == "It varies — read the room"


def test_picker_to_communication_has_entry_for_every_choice():
    """Every PICKER_CHOICES entry must have a mapping. Catches drift
    if a new choice is added without a label mapping."""
    for choice in PICKER_CHOICES:
        assert choice in PICKER_TO_COMMUNICATION


# ---------------------------------------------------------------------------
# is_phase_complete — only valid for the 4 remaining phases
# ---------------------------------------------------------------------------

def test_is_phase_complete_notebooks_requires_confirm():
    """The notebooks phase is complete when the user confirmed the plan."""
    from stillpoint.onboarding import is_phase_complete
    assert is_phase_complete("notebooks", {}) is False
    assert is_phase_complete(
        "notebooks", {"notebooks_confirmed": {"confirm_notebooks": True}}
    ) is True


def test_is_phase_complete_unknown_phase_returns_false():
    """Unknown phase names return False (defensive default)."""
    from stillpoint.onboarding import is_phase_complete
    assert is_phase_complete("nonexistent", {}) is False
