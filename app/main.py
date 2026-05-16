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

    with gr.Blocks(
        title="Stillpoint",
        theme=gr.themes.Soft(),
        css="""
        .contain { max-width: 900px; margin: auto; padding: 20px; }
        """,
    ) as app:
        # Two mutually-exclusive containers
        with gr.Column(visible=not configured, elem_id="onboarding_col") as onboarding_col:
            from app.onboarding_wizard import build_onboarding_view
            onboarding_done = build_onboarding_view()

        with gr.Column(visible=configured, elem_id="main_col") as main_col:
            with gr.Tabs():
                with gr.Tab("Chat"):
                    from app.chat import build_chat_view
                    build_chat_view()

                from app.reports import create_reports_tab
                create_reports_tab()

                from app.settings import create_settings_tab
                create_settings_tab()

        # When onboarding finishes, switch views
        def finish_onboarding():
            """Switch from onboarding to main tabbed view."""
            return gr.update(visible=False), gr.update(visible=True)

        onboarding_done.click(
            fn=finish_onboarding,
            inputs=[],
            outputs=[onboarding_col, main_col],
        )

    return app


def main():
    """Launch the Gradio application."""
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )


if __name__ == "__main__":
    main()