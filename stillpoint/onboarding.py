"""Onboarding interview engine for Stillpoint.

Manages the 6-phase onboarding process:
1. Welcome — What is Stillpoint, consent
2. Character Design — Therapist preferences
3. Infrastructure — NotebookLM + memory setup
4. Notebooks — Clinical concerns → notebook topology
5. Sources — Book/source recommendations per notebook
6. Processing Style — Optional processing adaptations
"""

from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from stillpoint.config import (
    get_templates_dir,
    load_source_library,
    save_config,
)


# Phase definitions
PHASES = [
    "welcome",
    "character_design",
    "infrastructure",
    "notebooks",
    "sources",
    "processing_style",
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
                "id": "gender_preference",
                "type": "choice",
                "question": "Do you have a preference for the therapist's gender presentation?",
                "choices": [
                    "No preference",
                    "Same gender as me",
                    "Different gender from me",
                    "Prefer masculine presentation",
                    "Prefer feminine presentation",
                    "Prefer neutral/non-binary presentation",
                ],
                "required": False,
            },
            {
                "id": "age_preference",
                "type": "choice",
                "question": "Do you have an age preference for the therapist?",
                "choices": [
                    "No preference",
                    "Similar age to me",
                    "Older mentor figure",
                    "Younger peer energy",
                ],
                "required": False,
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
                    "What qualities matter most to you? What would make you feel safe talking to them? "
                    "You can be as brief or detailed as you like."
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
                    "- **Ollama** — Run locally, no API costs, but requires a powerful machine"
                ),
                "choices": ["Anthropic (Claude)", "OpenAI (GPT-4)", "Google (Gemini)", "Ollama (local)"],
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

    elif phase == "sources":
        return [
            {
                "id": "sources_info",
                "type": "info",
                "question": (
                    "## Source Recommendations\n\n"
                    "For each notebook, here are the recommended books and resources. "
                    "These are curated clinical sources that will ground your therapist's responses.\n\n"
                    "When you create notebooks in NotebookLM, upload PDFs or text from these sources."
                ),
            },
            {
                "id": "confirm_sources",
                "type": "confirm",
                "question": "Would you like to save these source recommendations for reference?",
                "required": True,
            },
        ]

    elif phase == "processing_style":
        return [
            {
                "id": "processing_style_info",
                "type": "info",
                "question": (
                    "## Processing Style (Optional)\n\n"
                    "These questions help adapt the therapist to your processing style. "
                    "You can skip this section entirely — the therapist will learn your style "
                    "during sessions."
                ),
            },
            {
                "id": "wants_processing_questions",
                "type": "choice",
                "question": "Would you like to answer questions about your processing style?",
                "choices": [
                    "Yes, let's do it",
                    "No, let the therapist figure it out",
                ],
                "required": True,
            },
            {
                "id": "alexithymia",
                "type": "choice",
                "question": (
                    "When someone asks 'how are you feeling?', is your answer usually:\n\n"
                    "- **Cognitive** ('I'm thinking about...', 'I'm processing...')\n"
                    "- **Emotional** ('I feel sad/angry/happy...')\n"
                    "- **Mixed** (it depends on the situation)"
                ),
                "choices": ["Mostly cognitive", "Mostly emotional", "Mixed"],
                "required": False,
            },
            {
                "id": "intellectualizing",
                "type": "choice",
                "question": (
                    "Do you tend to analyze your feelings rather than experience them? "
                    "(This is common and not a flaw — it's just useful for the therapist to know.)"
                ),
                "choices": [
                    "Yes, I tend to intellectualize",
                    "Sometimes",
                    "No, I feel things directly",
                    "I'm not sure",
                ],
                "required": False,
            },
            {
                "id": "communication_preference",
                "type": "choice",
                "question": "How do you prefer people communicate with you?",
                "choices": [
                    "Direct and straightforward",
                    "Gentle and indirect",
                    "It varies — read the room",
                ],
                "required": False,
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

    elif phase == "sources":
        state.setdefault("sources_confirmed", {})
        state["sources_confirmed"][question_id] = answer

    elif phase == "processing_style":
        state.setdefault("processing_style", {})
        state["processing_style"][question_id] = answer

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

    elif phase == "sources":
        return bool(state.get("sources_confirmed", {}).get("confirm_sources"))

    elif phase == "processing_style":
        # Processing style is always optional — phase is complete once they've seen it
        return True

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
    elif "Ollama" in provider_answer:
        return {
            "provider": "ollama",
            "model": "llama3",
            "base_url": "http://localhost:11434/v1",
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