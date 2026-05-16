"""Persona management for Stillpoint.

Handles loading, generating, and validating the therapist persona.
The persona is generated from onboarding data using Jinja2 templates.
"""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from stillpoint.config import (
    get_config_dir,
    get_personas_dir,
    get_templates_dir,
    load_config,
    save_config,
)


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment pointing at the templates directory."""
    return Environment(
        loader=FileSystemLoader(str(get_templates_dir())),
        autoescape=select_autoescape([]),
        keep_trailing_newline=True,
    )


def load_persona() -> dict:
    """Load the therapist persona from config and personas files.

    Returns:
        Dictionary with persona data including name, description, specializations,
        communication style, and the full persona markdown.
    """
    therapist_config = load_config("therapist.yaml")
    user_config = load_config("user_profile.yaml")

    persona_md_path = get_personas_dir() / "therapist.md"
    persona_md = ""
    if persona_md_path.exists():
        with open(persona_md_path, "r", encoding="utf-8") as f:
            persona_md = f.read()

    return {
        "therapist": therapist_config.get("therapist", {}),
        "llm": therapist_config.get("llm", {}),
        "user": user_config.get("user", {}),
        "processing_style": user_config.get("processing_style", {}),
        "persona_md": persona_md,
    }


def get_system_prompt() -> str:
    """Build the system prompt for the LLM from the persona markdown.

    Returns:
        The full system prompt string including persona, boundaries, and context.
    """
    persona = load_persona()
    persona_md = persona.get("persona_md", "")

    if not persona_md:
        # Fallback: build a minimal system prompt from config
        therapist = persona.get("therapist", {})
        name = therapist.get("name", "your therapist")
        return (
            f"You are {name}, a compassionate AI therapeutic companion. "
            "You follow evidence-based approaches (ACT + IFS). "
            "You are warm, curious, and non-judgmental. "
            "You never diagnose, prescribe, or replace professional therapy."
        )

    # Add processing style context if available
    processing_style = persona.get("processing_style", {})
    extras = []
    if processing_style.get("alexithymia_adapted"):
        extras.append(
            "IMPORTANT: This user has difficulty identifying emotions in real time. "
            "Use cognitive/experiential framing. Avoid somatic questions like 'where do you feel that in your body?'"
        )
    if processing_style.get("intellectualizing_redirects"):
        extras.append(
            "IMPORTANT: If the user intellectualizes for 3+ exchanges without new emotional disclosure, "
            "gently redirect to their direct experience."
        )
    comm_pref = processing_style.get("communication_preference", "")
    if comm_pref:
        extras.append(f"Communication preference: {comm_pref}")

    if extras:
        persona_md += "\n\n## User-Specific Adaptations\n\n" + "\n\n".join(extras)

    return persona_md


def generate_persona(onboarding_data: dict) -> None:
    """Generate persona files from onboarding interview data.

    Creates:
    - personas/therapist.md — Full persona markdown
    - config/therapist.yaml — Therapist configuration
    - config/user_profile.yaml — User profile and preferences

    Args:
        onboarding_data: Dictionary containing all onboarding answers.
    """
    env = _get_jinja_env()

    # Prepare template variables
    character = onboarding_data.get("character_design", {})
    name = character.get("name", "your therapist")
    description = character.get("description", f"A compassionate AI therapeutic companion named {name}.")
    specializations = character.get("specializations", [])
    approach = character.get("approach", "ACT + IFS (Acceptance and Commitment Therapy + Internal Family Systems)")

    communication = {
        "tone": character.get("tone", "warm, curious, non-judgmental"),
        "directness": character.get("directness", "balanced"),
        "structure": character.get("structure", "follows the client's lead"),
        "humor": character.get("humor", "uses gentle humor when appropriate"),
        "questioning": character.get("questioning", "asks questions before offering interpretations"),
        "formality": character.get("formality", "casual but professional"),
    }

    # Generate persona markdown
    template = env.get_template("therapist_persona.md.tpl")
    persona_md = template.render(
        name=name,
        age=character.get("age", ""),
        background=character.get("background", ""),
        description=description,
        specializations=specializations,
        approach=approach,
        communication=communication,
        speech_patterns=character.get("speech_patterns", ""),
        identity={
            "gender_preference": character.get("gender_preference", ""),
            "cultural_background": character.get("cultural_background", ""),
            "life_experience": character.get("life_experience", ""),
        },
        exit_ramp_cadence=onboarding_data.get("exit_ramp_cadence", 5),
    )

    # Save persona markdown
    personas_dir = get_personas_dir()
    with open(personas_dir / "therapist.md", "w", encoding="utf-8") as f:
        f.write(persona_md)

    # Build notebook configs
    notebooks = onboarding_data.get("notebooks", [])
    notebook_configs = []
    for nb in notebooks:
        notebook_configs.append({
            "topic": nb.get("topic", ""),
            "notebook_id": nb.get("notebook_id", ""),
            "when_to_query": nb.get("when_to_query", ""),
        })

    # Save therapist config
    llm_config = onboarding_data.get("llm", {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
    })

    therapist_config = {
        "therapist": {
            "name": name,
            "description": description,
            "specializations": specializations,
            "notebooks": notebook_configs,
        },
        "llm": llm_config,
        "memory": {
            "palace_path": "~/.stillpoint/palace",
            "collections": ["mempalace_drawers", "therapy"],
            "wing": "therapy",
            "agent_name": name.lower().replace(" ", "_"),
        },
        "session": {
            "exit_ramp_cadence": onboarding_data.get("exit_ramp_cadence", 5),
            "session_unit": "therapy-day",
        },
    }
    save_config("therapist.yaml", therapist_config)

    # Save user profile
    processing_style = onboarding_data.get("processing_style", {})
    user_profile = {
        "user": {
            "name": onboarding_data.get("user_name", ""),
        },
        "processing_style": {
            "alexithymia_adapted": processing_style.get("alexithymia_adapted", False),
            "intellectualizing_redirects": processing_style.get("intellectualizing_redirects", True),
            "sensory_considerations": processing_style.get("sensory_considerations", False),
            "communication_preference": processing_style.get("communication_preference", ""),
        },
        "adaptations": [],
    }
    save_config("user_profile.yaml", user_profile)


def validate_persona() -> list[str]:
    """Check that all required persona fields are present.

    Returns:
        List of issue descriptions. Empty list means persona is valid.
    """
    issues = []

    try:
        config = load_config("therapist.yaml")
    except FileNotFoundError:
        return ["therapist.yaml not found — run onboarding first"]

    therapist = config.get("therapist", {})
    if not therapist.get("name"):
        issues.append("Therapist name is missing")
    if not therapist.get("specializations"):
        issues.append("No specializations configured")
    if not therapist.get("notebooks"):
        issues.append("No notebooks configured")

    llm = config.get("llm", {})
    if not llm.get("provider"):
        issues.append("LLM provider not configured")
    if not llm.get("model"):
        issues.append("LLM model not configured")

    personas_dir = get_personas_dir()
    if not (personas_dir / "therapist.md").exists():
        issues.append("Persona markdown file not found")

    return issues