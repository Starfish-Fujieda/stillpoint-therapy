"""Chat interface for Stillpoint therapy sessions.

Provides the main therapy chat UI with:
- Chatbot message display
- Text input for user messages
- Session controls (start, end)
- Session status display
- Grounding status indicator (NotebookLM vs static KB vs none)
- API key warning banner (when the configured env var is unset)
"""

import os

import gradio as gr

from stillpoint import knowledge
from stillpoint.config import load_config
from stillpoint.memory import get_session_count
from stillpoint.session import SessionEngine

# Module-level session engine (persists across Gradio reruns within a session)
_session_engine: SessionEngine | None = None


def _get_engine() -> SessionEngine:
    """Get or create the session engine."""
    global _session_engine
    if _session_engine is None:
        _session_engine = SessionEngine()
    return _session_engine


def _api_key_status() -> str:
    """Return an API key warning if the configured env var is unset.

    Reads ``therapist.yaml`` to find the configured
    ``llm.api_key_env`` (e.g., ``ANTHROPIC_API_KEY``), then checks
    the environment. Returns the warning text if the env var is
    missing or empty; returns an empty string if everything is OK.

    Why this lives in chat (not in the wizard): Quick Start writes
    the API key into the current process's env (see
    ``generate_quick_start_config``), so this check is most useful
    as a chat-startup sanity check, not an onboarding-time check.
    """
    try:
        cfg = load_config("therapist.yaml")
    except FileNotFoundError:
        return ""
    llm_cfg = cfg.get("llm", {})
    api_key_env = llm_cfg.get("api_key_env", "")
    if not api_key_env:
        return ""
    if os.environ.get(api_key_env, "").strip():
        return ""
    return (
        f"⚠️ **API key required.** Set the environment variable "
        f"`{api_key_env}` before sending a message, or LLM calls will "
        f"fail. (See Settings → LLM Backend to confirm which env var "
        f"name Stillpoint expects.)"
    )


def build_chat_view():
    """Build the chat interface view.

    Returns:
        Tuple of (on_load_fn, on_load_outputs) to wire app.load() in the caller.
    """
    # --- API key warning banner (PR 2, Fix 3) ---
    # Visible only when the configured env var is missing/empty.
    # Helps the user understand why the first chat message might
    # fail when they used Quick Start without a key.
    gr.Markdown(
        value=_api_key_status(),
        visible=bool(_api_key_status()),
    )

    # --- Header ---
    with gr.Row():
        gr.Markdown("## 🧘 Stillpoint")
        status_display = gr.Markdown(
            value=_get_status_text(),
            elem_id="session_status",
        )
        # Grounding status: clickable accordion. Label shows the current
        # state (emoji + state name); expanded view shows topics, notebook
        # count, and a link to Settings.
        grounding_status = gr.Accordion(
            label=_get_grounding_label(),
            open=False,
        )
        with grounding_status:
            gr.Markdown(value=_get_grounding_details())

    # --- Chat area ---
    chatbot = gr.Chatbot(
        label="",
        height=500,
        buttons=["copy"],
        layout="bubble",
        avatar_images=(None, "🧘"),
    )

    # --- Input area ---
    with gr.Row():
        msg_input = gr.Textbox(
            label="Your message",
            placeholder="Type here...",
            lines=2,
            scale=4,
            autofocus=True,
        )
        with gr.Column(scale=1, min_width=80):
            send_btn = gr.Button("Send", variant="primary")
            end_btn = gr.Button("End Session", variant="stop")

    # --- Session info ---
    with gr.Row():
        session_info = gr.Markdown(value="")

    # --- Event handlers ---
    def start_new_session():
        """Start a new therapy session."""
        engine = _get_engine()
        result = engine.start_session()
        opening = result.get("opening_message", "Welcome. How are you arriving today?")
        count = result.get("session_count", 0)

        info_text = f"Session #{count + 1}"
        if result.get("meta_question_overdue"):
            info_text += " • Meta-question OVERDUE — asked before clinical work"
        elif result.get("meta_question_due"):
            info_text += " • Meta-question due this session"

        return (
            [(None, opening)],
            info_text,
            _format_usage_status(result.get("usage_signals", {}), active=True),
            "",
        )

    def send_message(message, history):
        """Send a user message and get the therapist response."""
        if not message or not message.strip():
            return history, "", _get_status_text()

        engine = _get_engine()

        # Start session if not active
        if not engine.session_active:
            result = engine.start_session()
            opening = result.get("opening_message", "Welcome. How are you arriving today?")
            history = history + [(None, opening)]

        # Get therapist response
        try:
            response = engine.process_message(message.strip())
            history = history + [(message.strip(), response)]
        except Exception as e:
            error_msg = f"I'm sorry, something went wrong. Please try again. (Error: {e})"
            history = history + [(message.strip(), error_msg)]

        return history, "", _get_status_text()

    def end_session(history):
        """End the current session."""
        engine = _get_engine()
        if engine.session_active:
            engine.end_session()
            count = get_session_count()
            history = history + [
                (None, "Session ended. Your notes have been saved. Take care of yourself. 💙")
            ]
            return (
                history,
                f"Session saved. Total sessions: {count}",
                _get_status_text(),
            )
        return history, "No active session.", _get_status_text()

    # --- Wire events ---
    # Send on button click
    send_btn.click(
        fn=send_message,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input, status_display],
    ).then(
        fn=lambda: gr.update(autofocus=True),
        outputs=[msg_input],
    )

    # Send on Enter key
    msg_input.submit(
        fn=send_message,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input, status_display],
    )

    # End session
    end_btn.click(
        fn=end_session,
        inputs=[chatbot],
        outputs=[chatbot, session_info, status_display],
    )

    return start_new_session, [chatbot, session_info, status_display, msg_input]


def _format_usage_status(usage: dict, active: bool) -> str:
    """Render the usage-signals status line shown in the chat header.

    Surfaces the user's own learning trajectory: sessions completed,
    contacts in the last week, trigger-time contacts, and the
    meta-question (exit-ramp) status.
    """
    sessions = usage.get("sessions_completed", 0)
    contacts = usage.get("contacts_last_week", 0)
    triggers = usage.get("trigger_time_contacts", 0)
    meta = usage.get("meta_question_status", "")

    parts = [
        "🟢 Session active" if active else "⚪",
        f"{sessions} session{'s' if sessions != 1 else ''} completed",
        f"{contacts} contact{'s' if contacts != 1 else ''} this week",
    ]
    if triggers:
        parts.append(f"{triggers} at trigger-time")
    if meta:
        parts.append(f"meta-question: {meta}")
    return " • ".join(parts)


def _get_status_text() -> str:
    """Get the current status display text."""
    try:
        count = get_session_count()
        engine = _get_engine()
        active = engine.session_active if engine else False

        if active:
            usage = engine.session_context.get("usage_signals", {})
            if usage:
                return _format_usage_status(usage, active=True)
            return "🟢 Session active"
        elif count > 0:
            return f"⚪ {count} session{'s' if count != 1 else ''} completed"
        else:
            return "⚪ Ready for first session"
    except Exception:
        return "⚪ Ready"


def _get_grounding_label() -> str:
    """Return the current grounding state as a short label for the accordion title."""
    status = knowledge.get_grounding_status()
    if status["notebook_count"] > 0:
        return "🟢 Grounded"
    if status["static_available"]:
        return "🟡 Basic grounding"
    return "🔴 Not grounded"


def _get_grounding_details() -> str:
    """Return the markdown body shown when the grounding accordion is expanded."""
    status = knowledge.get_grounding_status()
    static_topics = status["static_topics"]
    notebook_count = status["notebook_count"]
    total_notebooks = len(knowledge.get_available_notebooks())

    lines: list[str] = ["**Grounding status**", ""]

    if static_topics:
        pretty = ", ".join(t.replace("_", " ").title() for t in static_topics)
        lines.append(f"**Static KB topics:** {pretty}")
    else:
        lines.append("**Static KB topics:** none")

    lines.append(f"**Notebooks configured:** {notebook_count} of {total_notebooks}")

    if notebook_count == 0:
        lines.extend([
            "",
            "For deeper clinical grounding, configure NotebookLM in **Settings → Notebooks**.",
        ])

    return "\n".join(lines)
