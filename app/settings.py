"""Settings UI for Stillpoint configuration management.

Provides a Gradio tab for editing:
- LLM backend (provider, model, API key env var)
- NotebookLM notebook definitions (add/remove)
- Therapist preferences (from persona config)
- Processing style + human therapist modality (from user_profile.yaml)
- Referral resources (freeform markdown)
"""

import gradio as gr

from stillpoint.config import (
    load_config,
    load_referral_resources,
    save_config,
    get_project_root,
)

# LLM provider options
_PROVIDERS = ["anthropic", "openai", "google", "ollama"]

# Default model per provider (best-effort; user can override)
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "google": "gemini-1.5-pro",
    "ollama": "llama3",
}

# Human therapist modality choices (matches the original onboarding
# question that lived in character_design, moved to Settings in PR 2).
_HUMAN_THERAPIST_MODALITIES = [
    "ACT",
    "DBT",
    "CBT",
    "Psychodynamic",
    "Somatic",
    "Other / Mixed",
    "Not in human therapy",
]

# Communication preference choices (matches the new onboarding
# picker's labels, mapped to the existing communication_preference
# schema on save: concrete→direct, analytical→gentle, mixed→mixed).
_COMMUNICATION_PREFERENCES = ["concrete", "analytical", "mixed"]


def _load_therapist_config() -> dict:
    """Load therapist.yaml, returning empty dict on missing file."""
    try:
        return load_config("therapist.yaml")
    except FileNotFoundError:
        return {}


def _load_user_profile() -> dict:
    """Load user_profile.yaml, returning empty dict on missing file."""
    try:
        return load_config("user_profile.yaml")
    except FileNotFoundError:
        return {}


def _save_referral_resources(content: str) -> None:
    """Save referral resources to the project root markdown file."""
    path = get_project_root() / "referral_resources.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _notebooks_to_rows(notebooks: list[dict]) -> list[list[str]]:
    """Convert notebook dicts to display rows for gr.Dataframe."""
    return [
        [
            nb.get("topic", ""),
            nb.get("notebook_id", ""),
            nb.get("when_to_query", ""),
        ]
        for nb in notebooks
    ]


def _rows_to_notebooks(rows: list[list[str]]) -> list[dict]:
    """Convert dataframe rows back to notebook dicts, skipping empty rows."""
    result = []
    for row in rows:
        topic = str(row[0]).strip() if row[0] else ""
        nb_id = str(row[1]).strip() if row[1] else ""
        when = str(row[2]).strip() if row[2] else ""
        if topic:
            result.append({"topic": topic, "notebook_id": nb_id, "when_to_query": when})
    return result


def create_settings_tab() -> gr.Tab:
    """Build and return the Settings tab component.

    Returns:
        A gr.Tab containing all settings UI.
    """
    with gr.Tab("Settings") as tab:
        gr.Markdown("## Settings")
        gr.Markdown(
            "Changes take effect the next time you start a session. "
            "All data is stored locally — nothing is transmitted automatically."
        )

        status_msg = gr.Markdown(value="")

        # ------------------------------------------------------------------ #
        # Section 1: LLM Backend                                               #
        # ------------------------------------------------------------------ #
        with gr.Accordion("LLM Backend", open=True):
            cfg = _load_therapist_config()
            llm_cfg = cfg.get("llm", {})

            provider_dd = gr.Dropdown(
                label="Provider",
                choices=_PROVIDERS,
                value=llm_cfg.get("provider", "anthropic"),
                interactive=True,
            )
            model_input = gr.Textbox(
                label="Model",
                value=llm_cfg.get("model", _DEFAULT_MODELS["anthropic"]),
                placeholder="e.g. claude-sonnet-4-20250514",
                interactive=True,
            )
            api_key_env_input = gr.Textbox(
                label="API Key Env Var",
                value=llm_cfg.get("api_key_env", "ANTHROPIC_API_KEY"),
                placeholder="Name of environment variable (not the key itself)",
                interactive=True,
            )
            base_url_input = gr.Textbox(
                label="Base URL (Ollama only)",
                value=llm_cfg.get("base_url", ""),
                placeholder="http://localhost:11434",
                interactive=True,
                visible=llm_cfg.get("provider", "anthropic") == "ollama",
            )

            def on_provider_change(provider: str):
                """Update model default and show/hide base_url when provider changes."""
                default_model = _DEFAULT_MODELS.get(provider, "")
                show_base_url = provider == "ollama"
                return gr.update(value=default_model), gr.update(visible=show_base_url)

            provider_dd.change(
                fn=on_provider_change,
                inputs=[provider_dd],
                outputs=[model_input, base_url_input],
            )

        # ------------------------------------------------------------------ #
        # Section 2: Notebooks                                                 #
        # ------------------------------------------------------------------ #
        with gr.Accordion("Notebooks", open=True):
            gr.Markdown(
                "Add or remove NotebookLM notebooks. "
                "The **Topic** column is required; leave Notebook ID blank until you create the notebook."
            )
            gr.Markdown(
                "### How to connect NotebookLM\n\n"
                "NotebookLM is Google's research notebook tool. Each notebook "
                "contains your own sources (PDFs, web pages, etc.) that the "
                "therapist can query for clinical grounding. Without a notebook "
                "configured, the therapist falls back to the built-in static "
                "knowledge base (less specific than live grounding, but better "
                "than `[UNGROUNDED]`).\n\n"
                "**4 steps to set up:**\n\n"
                "1. **Create or sign in to a Google account** at "
                "[notebooklm.google.com](https://notebooklm.google.com).\n"
                "2. **Create a new notebook** — click the \"+ New notebook\" button.\n"
                "3. **Copy the notebook ID from the URL.** The URL looks like "
                "`https://notebooklm.google.com/notebook/<UUID>` — copy the UUID "
                "(the long string after `/notebook/`).\n"
                "4. **Paste the ID in the table below** — fill in the Topic "
                "(a name for the notebook), paste the Notebook ID, and describe "
                "when to query it."
            )

            therapist_cfg = cfg.get("therapist", {})
            existing_notebooks = therapist_cfg.get("notebooks", [])

            notebook_table = gr.Dataframe(
                headers=["Topic", "Notebook ID", "When to Query"],
                datatype=["str", "str", "str"],
                value=_notebooks_to_rows(existing_notebooks),
                row_count=(max(len(existing_notebooks), 3), "dynamic"),
                column_count=(3, "fixed"),
                interactive=True,
                label="Notebooks",
                wrap=True,
            )

        # ------------------------------------------------------------------ #
        # Section 3: Therapist Preferences                                     #
        # ------------------------------------------------------------------ #
        with gr.Accordion("Therapist Preferences", open=False):
            therapist_name_input = gr.Textbox(
                label="Therapist Name",
                value=therapist_cfg.get("name", ""),
                placeholder="e.g. Dr. Sarah Chen",
                interactive=True,
            )
            therapist_desc_input = gr.Textbox(
                label="Description",
                value=therapist_cfg.get("description", ""),
                placeholder="Brief description of the therapist's style",
                lines=3,
                interactive=True,
            )
            specializations_input = gr.Textbox(
                label="Specializations (comma-separated)",
                value=", ".join(therapist_cfg.get("specializations", [])),
                placeholder="anxiety, grief, trauma",
                interactive=True,
            )

        # ------------------------------------------------------------------ #
        # Section 4: Referral Resources                                        #
        # ------------------------------------------------------------------ #
        with gr.Accordion("Referral Resources", open=False):
            gr.Markdown(
                "Add your local crisis lines and referral contacts here. "
                "This is what the system uses if a safety concern arises — never fabricated."
            )
            referral_input = gr.Textbox(
                label="referral_resources.md",
                value=load_referral_resources(),
                lines=12,
                interactive=True,
            )

        # ------------------------------------------------------------------ #
        # Section 5: Processing Style & Human Therapist Modality (PR 2)        #
        # ------------------------------------------------------------------ #
        # These fields were moved out of the onboarding wizard in PR 2
        # (Fix 4) to keep onboarding short. They live in
        # user_profile.yaml and are read by the persona-generation
        # code via stillpoint.persona.generate_persona().
        with gr.Accordion("Processing Style", open=False):
            user_profile = _load_user_profile()
            user_section = user_profile.get("user", {})
            ps_section = user_profile.get("processing_style", {})

            human_therapist_modality_input = gr.Dropdown(
                label="Human Therapist Modality",
                choices=_HUMAN_THERAPIST_MODALITIES,
                value=user_section.get("human_therapist_modality", "")
                or None,
                allow_custom_value=False,
                interactive=True,
            )
            alexithymia_input = gr.Checkbox(
                label="Adapt for cognitive vs emotional processing",
                value=bool(ps_section.get("alexithymia_adapted", False)),
                interactive=True,
            )
            intellectualizing_input = gr.Checkbox(
                label="Redirect analysis toward experience when present",
                value=bool(ps_section.get("intellectualizing_redirects", False)),
                interactive=True,
            )
            communication_preference_input = gr.Dropdown(
                label="Communication Preference",
                choices=_COMMUNICATION_PREFERENCES,
                value=ps_section.get("communication_preference", "")
                or None,
                allow_custom_value=False,
                interactive=True,
            )

        # ------------------------------------------------------------------ #
        # Save button                                                          #
        # ------------------------------------------------------------------ #
        save_btn = gr.Button("Save Settings", variant="primary")

        def save_all_settings(
            provider: str,
            model: str,
            api_key_env: str,
            base_url: str,
            notebook_rows,
            therapist_name: str,
            therapist_desc: str,
            specializations_str: str,
            referral_content: str,
            human_therapist_modality: str,
            alexithymia_adapted: bool,
            intellectualizing_redirects: bool,
            communication_preference: str,
        ) -> str:
            """Validate and persist all settings."""
            # Validate notebooks: no blank topic names
            notebooks = _rows_to_notebooks(notebook_rows)
            for nb in notebooks:
                if not nb.get("topic"):
                    return "Notebook topic cannot be empty. Please fill in all Topic fields."

            # Validate model field
            if not model.strip():
                return "Model name cannot be empty."

            # Load current config (to avoid clobbering fields we don't manage here)
            try:
                current = load_config("therapist.yaml")
            except FileNotFoundError:
                current = {}

            # Update LLM section
            llm_section: dict = {
                "provider": provider,
                "model": model.strip(),
                "api_key_env": api_key_env.strip(),
            }
            if base_url.strip():
                llm_section["base_url"] = base_url.strip()
            current["llm"] = llm_section

            # Update therapist section (preserve existing keys we don't manage)
            therapist_section = current.get("therapist", {})
            if therapist_name.strip():
                therapist_section["name"] = therapist_name.strip()
            if therapist_desc.strip():
                therapist_section["description"] = therapist_desc.strip()
            specializations = [
                s.strip()
                for s in specializations_str.split(",")
                if s.strip()
            ]
            if specializations:
                therapist_section["specializations"] = specializations
            therapist_section["notebooks"] = notebooks
            current["therapist"] = therapist_section

            # Save therapist.yaml
            save_config("therapist.yaml", current)

            # Save user_profile.yaml (PR 2, Fix 4: processing style
            # + human therapist modality moved here from onboarding)
            try:
                user_profile = load_config("user_profile.yaml")
            except FileNotFoundError:
                user_profile = {}
            user_profile.setdefault("user", {})
            user_profile["user"]["human_therapist_modality"] = (
                human_therapist_modality or ""
            )
            user_profile.setdefault("processing_style", {})
            user_profile["processing_style"]["alexithymia_adapted"] = bool(
                alexithymia_adapted
            )
            user_profile["processing_style"]["intellectualizing_redirects"] = bool(
                intellectualizing_redirects
            )
            user_profile["processing_style"]["communication_preference"] = (
                communication_preference or ""
            )
            save_config("user_profile.yaml", user_profile)

            # Save referral resources
            _save_referral_resources(referral_content)

            return "Settings saved."

        save_btn.click(
            fn=save_all_settings,
            inputs=[
                provider_dd,
                model_input,
                api_key_env_input,
                base_url_input,
                notebook_table,
                therapist_name_input,
                therapist_desc_input,
                specializations_input,
                referral_input,
                human_therapist_modality_input,
                alexithymia_input,
                intellectualizing_input,
                communication_preference_input,
            ],
            outputs=[status_msg],
        )

    return tab
