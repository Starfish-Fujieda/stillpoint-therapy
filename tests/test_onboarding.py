"""Tests for stillpoint.onboarding — onboarding phases, quick start, picker.

PR 2 reduced the onboarding from 6 phases to 4 + an end-of-wizard
picker, and added the Quick Start flow. These tests cover the new
shapes and the picker mapping.
"""

import os

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


# ---------------------------------------------------------------------------
# build_llm_config — provider mapping
# ---------------------------------------------------------------------------

def _llm_state(provider_answer):
    return {"infrastructure": {"llm_provider": provider_answer}}


def test_build_llm_config_anthropic():
    from stillpoint.onboarding import build_llm_config
    cfg = build_llm_config(_llm_state("Anthropic (Claude)"))
    assert cfg["provider"] == "anthropic"
    assert cfg["api_key_env"] == "ANTHROPIC_API_KEY"


def test_build_llm_config_openai():
    from stillpoint.onboarding import build_llm_config
    cfg = build_llm_config(_llm_state("OpenAI (GPT-4)"))
    assert cfg["provider"] == "openai"
    assert cfg["api_key_env"] == "OPENAI_API_KEY"


def test_build_llm_config_google():
    from stillpoint.onboarding import build_llm_config
    assert build_llm_config(_llm_state("Google (Gemini)"))["provider"] == "google"


def test_build_llm_config_openrouter_has_base_url():
    from stillpoint.onboarding import build_llm_config
    cfg = build_llm_config(_llm_state("OpenRouter"))
    assert cfg["provider"] == "openrouter"
    assert cfg["base_url"].startswith("https://openrouter.ai")


def test_build_llm_config_ollama_needs_no_key():
    from stillpoint.onboarding import build_llm_config
    cfg = build_llm_config(_llm_state("Ollama (local)"))
    assert cfg["provider"] == "ollama"
    assert "api_key_env" not in cfg


def test_build_llm_config_minimax_thinking_off_by_default():
    from stillpoint.onboarding import build_llm_config
    cfg = build_llm_config(_llm_state("MiniMax (M3)"))
    assert cfg["provider"] == "minimax"
    assert cfg["show_thinking"] is False


def test_build_llm_config_defaults_to_anthropic():
    from stillpoint.onboarding import build_llm_config
    assert build_llm_config({})["provider"] == "anthropic"


# ---------------------------------------------------------------------------
# build_processing_style — answer mapping
# ---------------------------------------------------------------------------

def test_processing_style_direct():
    from stillpoint.onboarding import build_processing_style
    ps = build_processing_style(
        {"processing_style": {"communication_preference": "Direct and straightforward"}}
    )
    assert ps["communication_preference"] == "direct"


def test_processing_style_gentle():
    from stillpoint.onboarding import build_processing_style
    ps = build_processing_style(
        {"processing_style": {"communication_preference": "Gentle and indirect"}}
    )
    assert ps["communication_preference"] == "gentle"


def test_processing_style_defaults_to_mixed():
    from stillpoint.onboarding import build_processing_style
    assert build_processing_style({})["communication_preference"] == "mixed"


def test_processing_style_alexithymia_and_intellectualizing():
    from stillpoint.onboarding import build_processing_style
    ps = build_processing_style({
        "processing_style": {
            "alexithymia": "Mostly cognitive",
            "intellectualizing": "Sometimes",
        }
    })
    assert ps["alexithymia_adapted"] is True
    assert ps["intellectualizing_redirects"] is True


# ---------------------------------------------------------------------------
# recommend_notebooks — required notebooks + specialization mapping
# ---------------------------------------------------------------------------

def _write_real_source_library(project_root):
    """Copy the real source library so topic keys match production."""
    import shutil
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    shutil.copy(
        repo_root / "templates" / "source_library.yaml",
        project_root / "templates" / "source_library.yaml",
    )


def test_recommend_notebooks_always_includes_required(project_root):
    from stillpoint.onboarding import recommend_notebooks
    _write_real_source_library(project_root)
    notebooks = recommend_notebooks({})
    required = [nb["topic_key"] for nb in notebooks if nb["required"]]
    assert "core_therapy_techniques" in required
    assert "self_compassion_shame" in required


def test_recommend_notebooks_maps_specializations(project_root):
    from stillpoint.onboarding import recommend_notebooks
    _write_real_source_library(project_root)
    state = {"character_design": {"specializations": ["Anxiety & OCD"]}}
    keys = [nb["topic_key"] for nb in recommend_notebooks(state)]
    assert "anxiety_ocd" in keys


def test_recommend_notebooks_ignores_unknown_labels(project_root):
    from stillpoint.onboarding import recommend_notebooks
    _write_real_source_library(project_root)
    state = {"character_design": {"specializations": ["Not A Real Label"]}}
    keys = [nb["topic_key"] for nb in recommend_notebooks(state)]
    assert len(keys) == 2  # required only


def test_recommend_notebooks_have_empty_ids_for_later_setup(project_root):
    from stillpoint.onboarding import recommend_notebooks
    _write_real_source_library(project_root)
    assert all(nb["notebook_id"] == "" for nb in recommend_notebooks({}))


# ---------------------------------------------------------------------------
# generate_all_config — end to end config generation
# ---------------------------------------------------------------------------

def _full_state():
    return {
        "user_name": "Rich",
        "welcome": {"consent": True, "user_name": "Rich"},
        "character_design": {
            "name": "Aiko",
            "directness": "Balanced",
            "structure": "Mixed",
            "humor": "Occasionally, when appropriate",
            "specializations": ["Anxiety & OCD"],
            "description": "",
        },
        "infrastructure": {
            "llm_provider": "Anthropic (Claude)",
            "api_key_set": True,
        },
        "notebooks_confirmed": {"confirm_notebooks": True},
        "processing_style": {
            "communication_preference": "It varies — read the room"
        },
    }


def _copy_templates(project_root):
    import shutil
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    shutil.copytree(
        repo_root / "templates", project_root / "templates", dirs_exist_ok=True
    )


def test_generate_all_config_writes_all_files(project_root):
    import yaml as _yaml

    from stillpoint.onboarding import generate_all_config
    _copy_templates(project_root)

    generate_all_config(_full_state())

    for fname in ("therapist.yaml", "user_profile.yaml", "treatment_plan.yaml"):
        assert (project_root / "config" / fname).exists(), fname
    assert (project_root / "personas" / "therapist.md").exists()

    therapist = _yaml.safe_load(
        (project_root / "config" / "therapist.yaml").read_text(encoding="utf-8")
    )
    assert therapist["therapist"]["name"] == "Aiko"
    assert therapist["llm"]["provider"] == "anthropic"
    assert any(
        nb["topic_key" if "topic_key" in nb else "topic"]
        for nb in therapist["therapist"]["notebooks"]
    )


def test_generate_all_config_satisfies_is_configured(project_root):
    from stillpoint.config import is_configured
    from stillpoint.onboarding import generate_all_config
    _copy_templates(project_root)
    assert is_configured() is False
    generate_all_config(_full_state())
    assert is_configured() is True


def test_generate_all_config_treatment_plan_has_goals(project_root):
    import yaml as _yaml

    from stillpoint.onboarding import generate_all_config
    _copy_templates(project_root)
    generate_all_config(_full_state())
    plan = _yaml.safe_load(
        (project_root / "config" / "treatment_plan.yaml").read_text(encoding="utf-8")
    )
    goals = str(plan.get("intake_goals", ""))
    assert "Anxiety & OCD" in goals


def test_build_llm_config_deepseek():
    from stillpoint.onboarding import build_llm_config
    cfg = build_llm_config(_llm_state("DeepSeek (V4)"))
    assert cfg["provider"] == "deepseek"
    assert cfg["api_key_env"] == "DEEPSEEK_API_KEY"
    assert cfg["base_url"] == "https://api.deepseek.com"


def test_deepseek_is_a_wizard_choice():
    from stillpoint.onboarding import get_phase_questions
    q = get_phase_questions("infrastructure")[0]
    assert "DeepSeek (V4)" in q["choices"]
    assert "2×" in q["question"] and "peak hours" in q["question"]


def test_quick_start_supports_deepseek(monkeypatch):
    from stillpoint.onboarding import generate_quick_start_config
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    state = generate_quick_start_config("test-key", "DeepSeek (V4)")
    assert state["infrastructure"]["llm_provider"] == "DeepSeek (V4)"
    assert os.environ.get("DEEPSEEK_API_KEY") == "test-key"
