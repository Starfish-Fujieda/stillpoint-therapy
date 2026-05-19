"""Chat interface for Stillpoint therapy sessions.

Provides the main therapy chat UI with:
- Chatbot message display
- Text input for user messages
- Session controls (start, end)
- Session status display
"""

import gradio as gr

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


def build_chat_view():
    """Build the chat interface view.

    Returns:
        Tuple of (on_load_fn, on_load_outputs) to wire app.load() in the caller.
    """
    # --- Header ---
    with gr.Row():
        gr.Markdown("## 🧘 Stillpoint")
        status_display = gr.Markdown(
            value=_get_status_text(),
            elem_id="session_status",
        )

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