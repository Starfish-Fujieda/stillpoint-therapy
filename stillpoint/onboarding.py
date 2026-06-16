"""Onboarding interview engine for Stillpoint.

Manages the onboarding process (was 6 phases; reduced to 4 in PR 2
Fix 4). A 5th end-of-wizard button screen (the processing-style
picker) is rendered in ``app/onboarding_wizard.py``.

Phases:
1. Welcome — What is Stillpoint, consent
2. Character Design — Therapist preferences
3. Infrastructure — NotebookLM + memory setup
4. Notebooks — Clinical concerns → notebook topology

Removed in PR 2 Fix 4 (moved to Settings, with the exception of
communication preference which became the end-of-wizard picker):
- Sources phase — book/source recommendations; on-demand in
  Settings → Notebooks.
- Processing Style phase — alexithymia + intellectualizing moved
  to Settings; communication preference became the picker.
- human_therapist_modality — moved from character_design to
  Settings.
"""

import os
from datetime import datetime

import gradio as gr
from jinja2 import Environment, FileSystemLoader

from stillpoint.config import (
    get_templates_dir,
    load_source_library,
    save_config,
)

# Phase definitions (PR 2, Fix 4: 4 phases, down from 6)
PHASES = [
    "welcome",
    "character_design",
    "infrastructure",
    "notebooks",
]


def get_phase_index(phase: str) -> int:
    """Return the index of a phase name."""
    if phase in PHASES:
        return PHASES.index(phase)
    return 0


def get_next_phase(current_phase: str) -> str | None:
    """Return the next phase after the current one, or None if done."""
    idx = get_phase_index(current_phase)
    if idx < len(PHASES) - 1:
        return PHASES[idx + 1]
    return None


def get_phase_questions(phase: str) -> list[dict]:
    """Return the questions for a given onboarding phase.

    Each question is a dict with:
    - id: unique key for the answer
    - question: the text to display
    - type: 'text', 'textarea', 'choice', 'multiselect', 'info', 'confirm'
    - choices: list of options (for choice/multiselect types)
    - required: whether the answer is mandatory
    """
    if phase == "welcome":
        return [
            {
                "id": "welcome_info",
                "type": "info",
                "question": (
                    "# Welcome to Stillpoint\n\n"
                    "Stillpoint is an AI-assisted self-therapy framework. "
                    "It provides a customizable therapist persona, clinical knowledge grounding, "
                    "and persistent session memory for browser-based therapy sessions.\n\n"
                    "**What Stillpoint is NOT:**\n"
                    "- A substitute for professional therapy\n"
                    "- A diagnostic tool\n"
                    "- A crisis intervention service\n\n"
                    "**What it CAN do:**\n"
                    "- Provide a safe space for self-exploration between human therapy sessions\n"
                    "- Generate structured session reports to share with your therapist\n"
                    "- Offer clinically-grounded therapeutic conversations\n\n"
                    "The onboarding process takes about 15-20 minutes. "
                    "You'll design your therapist, set up your knowledge base, "
                    "and configure your preferences."
                ),
            },
            {
                "id": "consent",
                "type": "confirm",
                "question": (
                    "I understand that Stillpoint is not a replacement for professional therapy, "
                    "and I will not use it in a mental health emergency."
                ),
                "required": True,
            },
            {
                "id": "user_name",
                "type": "text",
                "question": "What would you like to be called? (You can leave this blank.)",
                "required": False,
            },
        ]

    elif phase == "character_design":
        return [
            {
                "id": "name",
                "type": "text",
                "question": (
                    "Let's design your therapist. First, what would you like to call them?\n\n"
                    "This can be any name that feels right — a first name, a full name, "
                    "or something creative. You'll be talking to this character regularly."
                ),
                "required": True,
            },
            {
                "id": "directness",
                "type": "choice",
                "question": (
                    "How direct should your therapist be?\n\n"
                    "- **Direct/challenging**: Tells it like it is, challenges you when needed\n"
                    "- **Gentle/unhurried**: Softer approach, lets things emerge at your pace\n"
                    "- **Balanced**: Adjusts based on the situation"
                ),
                "choices": ["Direct and challenging", "Gentle and unhurried", "Balanced"],
                "required": True,
            },
            {
                "id": "structure",
                "type": "choice",
                "question": (
                    "How structured should sessions be?\n\n"
                    "- **Structured**: The therapist has an agenda and guides the session\n"
                    "- **Organic**: You lead, the therapist follows your energy\n"
                    "- **Mixed**: Some structure, but flexible"
                ),
                "choices": ["Structured", "Organic (follows my lead)", "Mixed"],
                "required": True,
            },
            {
                "id": "humor",
                "type": "choice",
                "question": "Should your therapist use humor?",
                "choices": [
                    "Yes, humor helps me relax",
                    "Occasionally, when appropriate",
                    "No, I prefer a serious tone",
                ],
                "required": False,
            },
            {
                "id": "specializations",
                "type": "multiselect",
                "question": (
                    "What concerns would you like your therapist to specialize in?\n\n"
                    "Select all that apply. This affects which knowledge bases are set up."
                ),
                "choices": [
                    "Anxiety & OCD",
                    "Depression & Mood",
                    "CPTSD & Trauma",
                    "ADHD & Executive Function",
                    "ASD & Neurodivergence",
                    "Grief & Loss",
                    "Relationship & Attachment",
                    "Substance Use & Recovery",
                    "Compulsive Sexual Behavior",
                    "Anger & Emotional Regulation",
                    "Body Image & Eating Concerns",
                    "Digital Addiction",
                    "Sleep & Chronic Health",
                    "Identity & Life Transitions",
                ],
                "required": True,
            },
            {
                "id": "description",
                "type": "textarea",
                "question": (
                    "Describe your ideal therapist in your own words. (Optional)\n\n"
                    "What qualities matter most to you? What would make you feel "
                    "safe talking to them? You can be as brief or detailed as "
                    "you like."
                ),
                "required": False,
            },
        ]

    elif phase == "infrastructure":
        return [
            {
                "id": "llm_provider",
                "type": "choice",
                "question": (
                    "## LLM Provider\n\n"
                    "Which LLM service will you use as the brain behind your therapist?\n\n"
                    "- **Anthropic** (Claude) — Recommended for therapeutic conversations\n"
                    "- **OpenAI** (GPT-4) — Also excellent quality\n"
                    "- **Google** (Gemini) — Good alternative\n"
                    "- **OpenRouter** — Access many models via one key\n"
                    "- **MiniMax** (M3) — Frontier model via the MiniMax Token Plan\n"
                    "- **Ollama** — Run locally, no API costs, but requires a powerful machine"
                ),
                "choices": [
                    "Anthropic (Claude)",
                    "OpenAI (GPT-4)",
                    "Google (Gemini)",
                    "OpenRouter",
                    "MiniMax (M3)",
                    "Ollama (local)",
                ],
                "required": True,
            },
            {
                "id": "api_key_set",
                "type": "confirm",
                "question": (
                    "Make sure you have your API key set as an environment variable.\n\n"
                    "For Anthropic: `export ANTHROPIC_API_KEY=your-key`\n"
                    "For OpenAI: `export OPENAI_API_KEY=your-key`\n"
                    "For Google: `export GOOGLE_API_KEY=your-key`\n"
                    "For OpenRouter: `export OPENROUTER_API_KEY=your-key`\n"
                    "For MiniMax: `export MINIMAX_API_KEY=your-key`\n"
                    "For Ollama: No key needed, just make sure Ollama is running.\n\n"
                    "Have you set your API key?"
                ),
                "required": True,
            },
            {
                "id": "infrastructure_note",
                "type": "info",
                "question": (
                    "## Infrastructure Note\n\n"
                    "NotebookLM and MemPalace integration are configured after initial setup. "
                    "For now, your therapist will respond using their persona training "
                    "without clinical knowledge grounding.\n\n"
                    "You can add NotebookLM notebooks and connect MemPalace later via Settings."
                ),
            },
        ]

    elif phase == "notebooks":
        return [
            {
                "id": "notebook_info",
                "type": "info",
                "question": (
                    "## Knowledge Base Planning\n\n"
                    "Based on your specializations, here are the recommended notebooks. "
                    "Everyone gets the two required notebooks (Core Therapy Techniques and "
                    "Self-Compassion & Shame Resilience). Additional notebooks are tailored "
                    "to your concerns.\n\n"
                    "You can add NotebookLM notebook IDs later in Settings."
                ),
            },
            {
                "id": "confirm_notebooks",
                "type": "confirm",
                "question": "Does this notebook plan look good? You can modify it later.",
                "required": True,
            },
        ]

    return []


def process_answer(phase: str, question_id: str, answer: str, state: dict) -> dict:
    """Process a user's answer and update the onboarding state.

    Args:
        phase: Current onboarding phase.
        question_id: The question's unique ID.
        answer: The user's answer.
        state: Current onboarding state (mutated in place).

    Returns:
        Updated state dictionary.
    """
    if state is None:
        state = {}

    # Store answer in the appropriate section
    if phase == "welcome":
        state.setdefault("welcome", {})
        state["welcome"][question_id] = answer
        if question_id == "user_name":
            state["user_name"] = answer

    elif phase == "character_design":
        state.setdefault("character_design", {})
        state["character_design"][question_id] = answer

    elif phase == "infrastructure":
        state.setdefault("infrastructure", {})
        state["infrastructure"][question_id] = answer

    elif phase == "notebooks":
        state.setdefault("notebooks_confirmed", {})
        state["notebooks_confirmed"][question_id] = answer

    return state


def is_phase_complete(phase: str, state: dict) -> bool:
    """Check if a phase has enough answers to proceed.

    Args:
        phase: The phase to check.
        state: Current onboarding state.

    Returns:
        True if the phase is complete enough to move on.
    """
    if phase == "welcome":
        return state.get("welcome", {}).get("consent") in (True, "True", "yes", "Yes")

    elif phase == "character_design":
        cd = state.get("character_design", {})
        return bool(cd.get("name") and cd.get("specializations"))

    elif phase == "infrastructure":
        infra = state.get("infrastructure", {})
        return bool(infra.get("llm_provider") and infra.get("api_key_set"))

    elif phase == "notebooks":
        return bool(state.get("notebooks_confirmed", {}).get("confirm_notebooks"))

    return False


def recommend_notebooks(state: dict) -> list[dict]:
    """Build the recommended notebook topology from user's specializations.

    Args:
        state: Onboarding state containing character_design choices.

    Returns:
        List of notebook configuration dicts.
    """
    source_library = load_source_library()
    topics = source_library.get("topics", {})

    # Map UI choice labels to source_library topic keys
    label_to_key = {
        "Anxiety & OCD": "anxiety_ocd",
        "Depression & Mood": "depression_mood",
        "CPTSD & Trauma": "cptsd_trauma",
        "ADHD & Executive Function": "adhd_executive_function",
        "ASD & Neurodivergence": "asd_neurodivergence",
        "Grief & Loss": "grief_loss",
        "Relationship & Attachment": "relationship_attachment",
        "Substance Use & Recovery": "substance_use_recovery",
        "Compulsive Sexual Behavior": "compulsive_sexual_behavior",
        "Anger & Emotional Regulation": "anger_emotional_regulation",
        "Body Image & Eating Concerns": "body_image_eating",
        "Digital Addiction": "digital_addiction",
        "Sleep & Chronic Health": "sleep_chronic_health",
        "Identity & Life Transitions": "identity_life_transitions",
    }

    specializations = state.get("character_design", {}).get("specializations", [])

    # Start with required notebooks
    notebooks = []
    for key, topic_data in topics.items():
        if topic_data.get("required"):
            notebooks.append({
                "topic": topic_data["display_name"],
                "topic_key": key,
                "notebook_id": "",
                "when_to_query": topic_data["description"],
                "required": True,
            })

    # Add tailored notebooks based on specializations
    for label in specializations:
        key = label_to_key.get(label)
        if key and key in topics:
            topic_data = topics[key]
            notebooks.append({
                "topic": topic_data["display_name"],
                "topic_key": key,
                "notebook_id": "",
                "when_to_query": topic_data["description"],
                "required": False,
            })

    return notebooks


def recommend_sources(notebooks: list[dict]) -> list[dict]:
    """Get source recommendations for each notebook.

    Args:
        notebooks: List of notebook dicts from recommend_notebooks().

    Returns:
        List of dicts with notebook topic and its sources.
    """
    source_library = load_source_library()
    topics = source_library.get("topics", {})

    recommendations = []
    for nb in notebooks:
        key = nb.get("topic_key", "")
        topic_data = topics.get(key, {})
        if topic_data:
            recommendations.append({
                "topic": nb["topic"],
                "core_sources": topic_data.get("core_sources", []),
                "supplemental_sources": topic_data.get("supplemental_sources", []),
            })

    return recommendations


def build_llm_config(state: dict) -> dict:
    """Build the LLM config from onboarding answers.

    Args:
        state: Onboarding state with infrastructure answers.

    Returns:
        LLM configuration dict.
    """
    provider_answer = state.get("infrastructure", {}).get("llm_provider", "")

    if "Anthropic" in provider_answer:
        return {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key_env": "ANTHROPIC_API_KEY",
        }
    elif "OpenAI" in provider_answer:
        return {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_env": "OPENAI_API_KEY",
        }
    elif "Google" in provider_answer:
        return {
            "provider": "google",
            "model": "gemini-pro",
            "api_key_env": "GOOGLE_API_KEY",
        }
    elif "OpenRouter" in provider_answer:
        return {
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4-5",
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url": "https://openrouter.ai/api/v1",
        }
    elif "Ollama" in provider_answer:
        return {
            "provider": "ollama",
            "model": "llama3",
            "base_url": "http://localhost:11434/v1",
        }
    elif "MiniMax" in provider_answer:
        return {
            "provider": "minimax",
            "model": "MiniMax-M3",
            "api_key_env": "MINIMAX_API_KEY",
            "base_url": "https://api.minimax.io/v1",
            # M3 emits reasoning; user can opt in to seeing it. Off by default
            # so the chat surface stays clean.
            "show_thinking": False,
        }

    # Default
    return {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
    }


def build_processing_style(state: dict) -> dict:
    """Build the processing style config from onboarding answers.

    Args:
        state: Onboarding state with processing_style answers.

    Returns:
        Processing style configuration dict.
    """
    ps = state.get("processing_style", {})

    alexithymia_adapted = ps.get("alexithymia") == "Mostly cognitive"
    intellectualizing = ps.get("intellectualizing") in (
        "Yes, I tend to intellectualize", "Sometimes"
    )

    comm_pref = ""
    comm_answer = ps.get("communication_preference", "")
    if "Direct" in comm_answer:
        comm_pref = "direct"
    elif "Gentle" in comm_answer:
        comm_pref = "gentle"
    else:
        comm_pref = "mixed"

    return {
        "alexithymia_adapted": alexithymia_adapted,
        "intellectualizing_redirects": intellectualizing,
        "sensory_considerations": False,
        "communication_preference": comm_pref,
    }


def generate_all_config(state: dict) -> None:
    """Generate all configuration files from completed onboarding.

    Creates:
    - config/therapist.yaml
    - config/user_profile.yaml
    - config/treatment_plan.yaml
    - personas/therapist.md

    Args:
        state: Complete onboarding state from all phases.
    """
    from stillpoint.persona import generate_persona

    # Build notebooks
    notebooks = recommend_notebooks(state)

    # Build LLM config
    llm_config = build_llm_config(state)

    # Build processing style
    processing_style = build_processing_style(state)

    # Build goals from specializations
    specializations = state.get("character_design", {}).get("specializations", [])
    goals = []
    for spec in specializations:
        goals.append({"description": f"Explore and address concerns related to {spec}"})

    # Assemble onboarding data for persona generation
    onboarding_data = {
        "user_name": state.get("user_name", ""),
        "character_design": state.get("character_design", {}),
        "notebooks": notebooks,
        "llm": llm_config,
        "processing_style": processing_style,
        "exit_ramp_cadence": 5,
    }

    # Generate persona files (therapist.yaml, user_profile.yaml, therapist.md)
    generate_persona(onboarding_data)

    # Generate treatment plan
    env = Environment(
        loader=FileSystemLoader(str(get_templates_dir())),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("treatment_plan.yaml.tpl")
    treatment_plan_yaml = template.render(
        created_date=datetime.now().isoformat(),
        goals=goals,
        exit_ramp_cadence=5,
    )

    save_config("treatment_plan.yaml", __import__("yaml").safe_load(treatment_plan_yaml))


def generate_quick_start_config(
    api_key: str | None,
    provider_choice: str = "Anthropic (Claude)",
) -> dict:
    """Build a minimal valid state dict for Quick Start.

    Returns a state dict that ``generate_all_config()`` can consume
    to produce a working Stillpoint config in one click. The Quick
    Start panel in ``app/main.py`` wires this directly.

    Args:
        api_key: API key string pasted by the user. When non-blank,
            it's written to the appropriate env var (see
            ``_QUICK_START_PROVIDER_ENV_VARS``) in the current process
            so the LLM call works in this Gradio session. Env vars
            don't persist across processes, so the user still needs to
            set the env var externally for future sessions — but the
            immediate session works.
        provider_choice: Display name of the chosen provider, e.g.
            ``"Anthropic (Claude)"`` or ``"MiniMax (M3)"``. Must be
            one of ``_QUICK_START_PROVIDER_CHOICES``; raises
            ``ValueError`` otherwise.

    When ``api_key`` is None or blank, the env var is not set, and
    the chat surface displays an "API key required" banner so the
    user gets a clear message instead of a silent failure.

    Default config (per the friction-reduction plan, Fix 2):
        - Therapist name: "Your Therapist" (rename in Settings)
        - Directness: "Balanced"
        - Structure: "Mixed"
        - Specializations: ["ACT — Defusion & Values"]
          (matches what PR 1's static KB actually covers)
        - LLM provider: from ``provider_choice``
        - API key: from input, or blank if skipped
        - Notebooks: required notebooks with blank IDs
          (static KB handles grounding)
        - Processing style: defaults
    """
    if provider_choice not in _QUICK_START_PROVIDER_ENV_VARS:
        raise ValueError(
            f"Unknown Quick Start provider: {provider_choice!r}. "
            f"Expected one of {list(_QUICK_START_PROVIDER_ENV_VARS)}."
        )

    env_var = _QUICK_START_PROVIDER_ENV_VARS[provider_choice]
    if api_key and api_key.strip() and env_var:
        os.environ[env_var] = api_key.strip()
    return {
        "user_name": "",
        "welcome": {
            "consent": True,
            "user_name": "",
        },
        "character_design": {
            "name": "Your Therapist",
            "directness": "Balanced",
            "structure": "Mixed",
            "humor": "",
            "specializations": ["ACT — Defusion & Values"],
            "description": "",
        },
        "infrastructure": {
            "llm_provider": provider_choice,
            "api_key_set": True,
        },
        "notebooks_confirmed": {
            "confirm_notebooks": True,
        },
    }


# Quick Start provider choices (display names) and the env-var each one
# writes the API key into. Empty string means "no key" (Ollama runs locally).
_QUICK_START_PROVIDER_CHOICES = [
    "Anthropic (Claude)",
    "OpenAI (GPT-4)",
    "Google (Gemini)",
    "OpenRouter",
    "MiniMax (M3)",
    "Ollama (local)",
]

_QUICK_START_PROVIDER_ENV_VARS: dict[str, str] = {
    "Anthropic (Claude)": "ANTHROPIC_API_KEY",
    "OpenAI (GPT-4)": "OPENAI_API_KEY",
    "Google (Gemini)": "GOOGLE_API_KEY",
    "OpenRouter": "OPENROUTER_API_KEY",
    "MiniMax (M3)": "MINIMAX_API_KEY",
    "Ollama (local)": "",
}


# Picker choice labels (used by the picker UI and the build_processing_style
# mapping in app/onboarding_wizard.py).
PICKER_CHOICES = ["concrete", "analytical", "mixed"]

# Mapping from picker choice → OLD communication_preference labels
# (per user decision: zero schema change to therapist.yaml).
# The values here are the OLD human-readable labels that
# build_processing_style() already understands via substring
# matching. So the picker stores these full strings, and
# build_processing_style consumes them unchanged.
#
# The mapping (per plan): concrete → "Direct and straightforward",
# analytical → "Gentle and indirect", mixed → "It varies — read the
# room". The "analytical → Gentle" mapping is semantically imperfect
# but accepted in favor of no schema churn.
PICKER_TO_COMMUNICATION = {
    "concrete": "Direct and straightforward",
    "analytical": "Gentle and indirect",
    "mixed": "It varies — read the room",
}


def processing_style_picker() -> tuple:
    """Build the end-of-wizard 3-button processing-style picker.

    Returns:
        Tuple of (column, concrete_btn, analytical_btn, mixed_btn).
        The Column is invisible by default; the wizard makes it
        visible after the 4 phases complete.

    Wiring pattern: this function does NOT register click handlers.
    That happens in ``app/onboarding_wizard.py`` after this function
    returns its components, mirroring the ``done_btn.click`` pattern
    in ``app/main.py``. The click handler sets
    ``state["processing_style"]["communication_preference"]`` to the
    user's choice (mapped via ``PICKER_TO_COMMUNICATION``) and then
    advances to ``_finish_onboarding``.
    """
    picker_col = gr.Column(visible=False)
    with picker_col:
        gr.Markdown("## How do you prefer to communicate?")
        gr.Markdown(
            "Pick the style that fits you best. You can change this "
            "in Settings later."
        )
        with gr.Row():
            concrete_btn = gr.Button("Concrete", variant="primary")
            analytical_btn = gr.Button("Analytical", variant="primary")
            mixed_btn = gr.Button("Mixed", variant="primary")
    return picker_col, concrete_btn, analytical_btn, mixed_btn
