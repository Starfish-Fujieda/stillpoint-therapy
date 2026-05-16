"""Report generation UI for Stillpoint.

Provides a Gradio tab for generating structured session reports suitable
for sharing with a human therapist.

Report generation delegates to `stillpoint.report.generate_session_report()`.
That module is implemented separately (Task 14) and merged independently.
"""

from __future__ import annotations

import datetime
import tempfile
from pathlib import Path
from typing import Any

import gradio as gr

# The 9 report sections defined in ARCHITECTURE.md
REPORT_SECTIONS = [
    "Themes Covered",
    "Goal Progress",
    "New Disclosures",
    "Coping Strategies Attempted",
    "Emotional Trajectory",
    "Red Flags",
    "Patterns Observed",
    "Homework / Practices Assigned",
    "Client's Own Assessment",
]


def _call_generate_report(
    since_last: bool,
    start_date: str | None,
    end_date: str | None,
    sections: list[str],
    anonymize: bool,
) -> str:
    """Delegate to stillpoint.report.generate_session_report().

    Import is done lazily so that an ImportError (module not yet merged)
    produces a clear, user-visible message rather than crashing the app.
    """
    try:
        from stillpoint.report import generate_session_report  # type: ignore[import]
    except ImportError:
        return (
            "**Report generation is not yet available.**\n\n"
            "`stillpoint.report` has not been installed. "
            "Ensure Task 14 is merged and run `pip install -e .` to activate this feature."
        )

    # Build session filter — pass None to mean "all since last report"
    sessions: list[str] | None = None
    if not since_last and start_date and end_date:
        # Pass date range as metadata hint in sessions list
        # (actual filtering is report.py's responsibility)
        sessions = [f"date_range:{start_date}:{end_date}"]

    return generate_session_report(sessions=sessions, anonymize=anonymize)


def _write_temp_markdown(content: str) -> str:
    """Write report content to a temporary .md file and return its path."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stillpoint_report_{timestamp}.md"
    tmp_dir = Path(tempfile.gettempdir())
    path = tmp_dir / filename
    path.write_text(content, encoding="utf-8")
    return str(path)


def create_reports_tab() -> gr.Tab:
    """Build and return the Reports tab component.

    Returns:
        A gr.Tab containing the full report generation UI.
    """
    with gr.Tab("Reports") as tab:
        gr.Markdown("## Session Report Generator")
        gr.Markdown(
            "Generate a structured summary of your sessions for sharing with a human therapist. "
            "All processing happens locally — nothing is transmitted automatically."
        )

        # ------------------------------------------------------------------ #
        # Section 1: Date range                                                #
        # ------------------------------------------------------------------ #
        with gr.Group():
            gr.Markdown("### Date Range")

            since_last_cb = gr.Checkbox(
                label="Since last report (recommended)",
                value=True,
            )

            with gr.Row(visible=False) as date_row:
                today = datetime.date.today()
                thirty_days_ago = today - datetime.timedelta(days=30)

                start_date_input = gr.Textbox(
                    label="Start Date (YYYY-MM-DD)",
                    value=str(thirty_days_ago),
                    placeholder="2026-01-01",
                )
                end_date_input = gr.Textbox(
                    label="End Date (YYYY-MM-DD)",
                    value=str(today),
                    placeholder="2026-12-31",
                )

            def toggle_date_range(since_last: bool):
                """Show/hide the date range inputs."""
                return gr.update(visible=not since_last)

            since_last_cb.change(
                fn=toggle_date_range,
                inputs=[since_last_cb],
                outputs=[date_row],
            )

        # ------------------------------------------------------------------ #
        # Section 2: Section toggles                                           #
        # ------------------------------------------------------------------ #
        with gr.Group():
            gr.Markdown("### Sections to Include")
            sections_cb = gr.CheckboxGroup(
                label="",
                choices=REPORT_SECTIONS,
                value=REPORT_SECTIONS,  # all on by default
            )

        # ------------------------------------------------------------------ #
        # Section 3: Privacy                                                   #
        # ------------------------------------------------------------------ #
        with gr.Group():
            gr.Markdown("### Privacy")
            anonymize_cb = gr.Checkbox(
                label="Anonymize identifying details",
                value=False,
            )

        # ------------------------------------------------------------------ #
        # Generate button + output                                             #
        # ------------------------------------------------------------------ #
        generate_btn = gr.Button("Generate Report", variant="primary", size="lg")

        status_msg = gr.Markdown(value="")

        report_output = gr.Markdown(
            value="",
            label="Generated Report",
            visible=False,
        )

        download_btn = gr.Button(
            "Download as Markdown",
            variant="secondary",
            visible=False,
        )
        download_file = gr.File(
            label="Download",
            visible=False,
            interactive=False,
        )

        # ------------------------------------------------------------------ #
        # Event: Generate                                                       #
        # ------------------------------------------------------------------ #
        def on_generate(
            since_last: bool,
            start_date: str,
            end_date: str,
            sections: list[str],
            anonymize: bool,
        ) -> tuple[Any, ...]:
            """Generate the report and surface it in the UI."""
            if not sections:
                return (
                    gr.update(value="Please select at least one section."),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                )

            content = _call_generate_report(
                since_last=since_last,
                start_date=start_date if not since_last else None,
                end_date=end_date if not since_last else None,
                sections=sections,
                anonymize=anonymize,
            )

            if not content:
                return (
                    gr.update(value="No sessions found for the selected range."),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                )

            return (
                gr.update(value="Report generated."),
                gr.update(value=content, visible=True),
                gr.update(visible=True),
                gr.update(visible=False),
            )

        generate_btn.click(
            fn=on_generate,
            inputs=[since_last_cb, start_date_input, end_date_input, sections_cb, anonymize_cb],
            outputs=[status_msg, report_output, download_btn, download_file],
        )

        # ------------------------------------------------------------------ #
        # Event: Download                                                       #
        # ------------------------------------------------------------------ #
        def on_download(report_content: str) -> tuple[Any, ...]:
            """Write the report to a temp file and expose for download."""
            if not report_content:
                return gr.update(visible=False)
            path = _write_temp_markdown(report_content)
            return gr.update(value=path, visible=True)

        download_btn.click(
            fn=on_download,
            inputs=[report_output],
            outputs=[download_file],
        )

    return tab
