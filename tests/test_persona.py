"""Tests for stillpoint.persona — persona generation and system prompt."""

import shutil
from pathlib import Path

import yaml

from stillpoint.persona import (
    generate_persona,
    get_system_prompt,
    load_persona,
    validate_persona,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _copy_templates(project_root):
    shutil.copytree(
        REPO_ROOT / "templates", project_root / "templates", dirs_exist_ok=True
    )


def _onboarding_data():
    return {
        "user_name": "Rich",
        "character_design": {
            "name": "Aiko",
            "directness": "Balanced",
            "structure": "Mixed",
            "humor": "Occasionally, when appropriate",
            "specializations": ["Anxiety & OCD", "ADHD & Executive Function"],
        },
        "notebooks": [
            {
                "topic": "Core Therapy Techniques",
                "notebook_id": "",
                "when_to_query": "ACT, IFS, CBT",
            }
        ],
        "llm": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
        "processing_style": {
            "alexithymia_adapted": False,
            "intellectualizing_redirects": False,
            "sensory_considerations": False,
            "communication_preference": "mixed",
        },
        "exit_ramp_cadence": 5,
    }


def test_generate_persona_writes_all_files(project_root):
    _copy_templates(project_root)
    generate_persona(_onboarding_data())

    assert (project_root / "personas" / "therapist.md").exists()
    assert (project_root / "config" / "therapist.yaml").exists()
    assert (project_root / "config" / "user_profile.yaml").exists()


def test_generate_persona_markdown_contains_name_and_specializations(project_root):
    _copy_templates(project_root)
    generate_persona(_onboarding_data())

    md = (project_root / "personas" / "therapist.md").read_text(encoding="utf-8")
    assert "Aiko" in md
    assert "Anxiety & OCD" in md


def test_generate_persona_yaml_round_trip(project_root):
    _copy_templates(project_root)
    generate_persona(_onboarding_data())

    therapist = yaml.safe_load(
        (project_root / "config" / "therapist.yaml").read_text(encoding="utf-8")
    )
    assert therapist["therapist"]["name"] == "Aiko"
    assert therapist["llm"]["provider"] == "anthropic"

    profile = yaml.safe_load(
        (project_root / "config" / "user_profile.yaml").read_text(encoding="utf-8")
    )
    assert profile is not None


def test_load_persona_returns_generated_content(project_root):
    _copy_templates(project_root)
    generate_persona(_onboarding_data())

    persona = load_persona()
    assert "Aiko" in str(persona)


def test_get_system_prompt_includes_persona(project_root):
    _copy_templates(project_root)
    generate_persona(_onboarding_data())

    prompt = get_system_prompt()
    assert "Aiko" in prompt


def test_validate_persona_passes_after_generation(project_root):
    _copy_templates(project_root)
    generate_persona(_onboarding_data())

    problems = validate_persona()
    assert problems == []


def test_validate_persona_reports_missing_files(project_root):
    problems = validate_persona()
    assert problems, "missing persona files must be reported"
