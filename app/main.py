"""Stillpoint Gradio web application entry point.

Launch with: python -m app.main

If no config exists → shows onboarding wizard.
If config exists → shows tabbed interface (Chat, Reports, Settings).
"""

import gradio as gr

from stillpoint.config import is_configured


def build_app() -> gr.Blocks:
    """Build the Gradio application with conditional view.

    Returns:
        Gradio Blocks application.
    """
    configured = is_configured()

    with gr.Blocks(title="Stillpoint") as app:
        # Two mutually-exclusive containers
        with gr.Column(visible=not configured, elem_id="onboarding_col") as onboarding_col:
            # --- Quick Start panel (Fix 3, PR 2) ---
            # Above the wizard so a user with an API key can skip
            # the 15-20 minute onboarding and start chatting in
            # ~1 minute. The user can still customize in Settings
            # later. Below the wizard is also visible (the user
            # can choose either path).
            with gr.Column(elem_id="quick_start_col"):
                gr.Markdown("## ⚡ Quick Start")
                gr.Markdown(
                    "Already have an API key? Pick your provider, paste the "
                    "key below, and start chatting in seconds. You can customize "
                    "the therapist, configure NotebookLM, and adjust every "
                    "preference in **Settings** after your first session."
                )
                # Import here (not at top) so the panel degrades gracefully
                # if Gradio import-time issues prevent the constant from
                # loading. The same constant is also used by app.main's
                # smoke tests.
                from stillpoint.onboarding import _QUICK_START_PROVIDER_CHOICES
                provider_dd = gr.Dropdown(
                    label="Provider",
                    choices=_QUICK_START_PROVIDER_CHOICES,
                    value="Anthropic (Claude)",
                    interactive=True,
                )
                api_key_input = gr.Textbox(
                    label="API Key",
                    placeholder="paste your API key (leave blank to skip and use the wizard below)",
                    type="password",
                    interactive=True,
                )
                quick_start_btn = gr.Button(
                    "⚡ Quick Start", variant="primary", size="lg"
                )
                gr.Markdown(
                    "---\n\n"
                    "*Or set up the full therapist step by step ↓*"
                )

            # --- Onboarding wizard (4 phases after PR 2 Fix 4) ---
            from app.onboarding_wizard import build_onboarding_view
            done_btn, setup_later_btn = build_onboarding_view()

        with gr.Column(visible=configured, elem_id="main_col") as main_col:
            with gr.Tabs():
                with gr.Tab("Chat"):
                    from app.chat import build_chat_view
                    chat_load_fn, chat_load_outputs = build_chat_view()

                from app.reports import create_reports_tab
                create_reports_tab()

                from app.settings import create_settings_tab
                create_settings_tab()

        # --- Event handlers ---
        def finish_onboarding():
            """Switch from onboarding to main tabbed view (used by
            both the wizard's completion buttons and Quick Start)."""
            return gr.update(visible=False), gr.update(visible=True)

        def on_quick_start(api_key: str, provider_choice: str):
            """Handle Quick Start: build state, persist config, switch views."""
            from stillpoint.onboarding import (
                generate_all_config,
                generate_quick_start_config,
            )
            state = generate_quick_start_config(api_key, provider_choice)
            generate_all_config(state)
            return gr.update(visible=False), gr.update(visible=True)

        # Quick Start — uses the same view switch as the wizard's
        # completion buttons. No banner here; the chat surface
        # independently checks for a missing API key and shows one
        # if needed.
        quick_start_btn.click(
            fn=on_quick_start,
            inputs=[api_key_input, provider_dd],
            outputs=[onboarding_col, main_col],
        )

        # Both wizard completion buttons trigger the same view
        # switch. The "setup later" button is only shown when 0
        # notebooks are configured (post-onboarding conditional
        # message).
        done_btn.click(
            fn=finish_onboarding,
            inputs=[],
            outputs=[onboarding_col, main_col],
        )
        setup_later_btn.click(
            fn=finish_onboarding,
            inputs=[],
            outputs=[onboarding_col, main_col],
        )

        if configured:
            app.load(fn=chat_load_fn, outputs=chat_load_outputs)

    return app


def main():
    """Launch the Gradio application."""
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Soft(),
        # Center the app; the previous css only styled .contain (the
        # question display), leaving the page column uncentered.
        css=(
            ".gradio-container { max-width: 900px !important; "
            "margin: 0 auto !important; } "
            ".contain { max-width: 900px; margin: auto; padding: 20px; }"
        ),
    )


if __name__ == "__main__":
    main()
