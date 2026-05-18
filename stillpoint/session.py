"""Session protocol engine for Stillpoint.

Manages the therapy session lifecycle: start, process messages, end.
Ties together persona, memory, knowledge, and LLM components.
"""

import logging
from datetime import datetime, timedelta

from stillpoint.config import load_config, save_config
from stillpoint.knowledge import query_knowledge
from stillpoint.llm import send_message
from stillpoint.memory import (
    get_session_count,
    get_wake_up_context,
    save_session_notes,
)
from stillpoint.persona import get_system_prompt

logger = logging.getLogger(__name__)


class SessionEngine:
    """Manages the therapy session lifecycle."""

    def __init__(self) -> None:
        self.session_context: dict = {}
        self.conversation: list[dict] = []
        self.session_active: bool = False
        self.session_start_time: datetime | None = None

    def start_session(self) -> dict:
        """Run session start protocol.

        Loads memory context, treatment plan, and prepares the session.

        Returns:
            Dictionary with session context including wake-up info and opening message.
        """
        # Load memory context
        wake_up = get_wake_up_context()
        session_count = get_session_count()

        # Load treatment plan
        try:
            treatment_plan = load_config("treatment_plan.yaml")
        except FileNotFoundError:
            treatment_plan = {}

        exit_ramp_cadence = treatment_plan.get("exit_ramp", {}).get(
            "meta_question_cadence", 5
        )
        total_contacts = treatment_plan.get("exit_ramp", {}).get("total_contacts", 0)

        # Check if the meta-question is due — and distinguish due vs OVERDUE.
        # Due: the cadence interval has been reached.
        # Overdue: the cadence interval has been exceeded (or never asked past it).
        meta_due = False
        meta_overdue = False
        last_meta = treatment_plan.get("exit_ramp", {}).get("last_meta_question_session")
        if last_meta is None:
            if session_count >= exit_ramp_cadence:
                meta_due = True
                meta_overdue = session_count > exit_ramp_cadence
        else:
            sessions_since = session_count - last_meta
            if sessions_since >= exit_ramp_cadence:
                meta_due = True
                meta_overdue = sessions_since > exit_ramp_cadence

        # Build usage signals for the session-start status line.
        usage_signals = treatment_plan.get("usage_signals", {})
        session_log = treatment_plan.get("session_log", [])
        cutoff = datetime.now() - timedelta(days=7)
        contacts_last_week = 0
        for entry in session_log:
            try:
                entry_dt = datetime.fromisoformat(entry.get("date", ""))
            except (ValueError, TypeError):
                continue
            if entry_dt >= cutoff:
                contacts_last_week += 1

        if meta_overdue:
            meta_status = "overdue"
        elif meta_due:
            meta_status = "due"
        else:
            meta_status = usage_signals.get("meta_question_status") or "on track"

        usage = {
            "sessions_completed": session_count,
            "contacts_last_week": contacts_last_week,
            "trigger_time_contacts": usage_signals.get("trigger_time_contacts", 0),
            "meta_question_status": meta_status,
        }

        self.session_context = {
            "session_count": session_count,
            "wake_up_context": wake_up,
            "treatment_plan": treatment_plan,
            "meta_question_due": meta_due,
            "meta_question_overdue": meta_overdue,
            "usage_signals": usage,
        }

        self.conversation = []
        self.session_active = True
        self.session_start_time = datetime.now()

        # Build opening message
        system_prompt = get_system_prompt()

        # Include wake-up context as a system-level note
        context_note = ""
        if session_count == 0:
            context_note = "This is the user's first session. Welcome them warmly."
        else:
            context_note = f"Session context:\n{wake_up}"

        if meta_overdue:
            context_note += (
                "\n\nNOTE: The meta-question is OVERDUE. Before beginning clinical "
                "work this session, check in on the arrangement itself — ask "
                "something like: 'How is this arrangement fitting into your life?' "
                "Do not defer this to the end of the session."
            )
        elif meta_due:
            context_note += (
                "\n\nNOTE: A meta-question is due this session. "
                "At an appropriate moment, ask something like: "
                "'How is this arrangement fitting into your life?'"
            )

        # Send initial context to get the opening message
        opening_messages = [
            {
                "role": "user",
                "content": (
                    f"[SYSTEM CONTEXT: {context_note}]\n\n"
                    "Please begin the session with your opening."
                ),
            }
        ]

        try:
            opening_response = send_message(system_prompt, opening_messages)
        except Exception as e:
            logger.error("Failed to get opening message: %s", e)
            opening_response = "Welcome. I'm glad you're here. How are you arriving today?"

        self.conversation.append({"role": "assistant", "content": opening_response})

        return {
            "opening_message": opening_response,
            "session_count": session_count,
            "meta_question_due": meta_due,
            "meta_question_overdue": meta_overdue,
            "usage_signals": usage,
        }

    def process_message(self, user_message: str) -> str:
        """Process a user message through the full pipeline.

        1. Load persona as system prompt
        2. Load recent session context from memory
        3. Analyze message for clinical topics
        4. Query knowledge base for relevant grounding
        5. Assemble full prompt
        6. Send to LLM
        7. Return response

        Args:
            user_message: The user's message text.

        Returns:
            The therapist's response text.
        """
        if not self.session_active:
            return "No active session. Please start a session first."

        # Add user message to conversation
        self.conversation.append({"role": "user", "content": user_message})

        # Get system prompt
        system_prompt = get_system_prompt()

        # Query knowledge base for clinical grounding
        grounding = query_knowledge(user_message)
        if grounding and not grounding.startswith("[UNGROUNDED"):
            # Inject grounding as context (not shown to user)
            augmented_message = (
                f"[CLINICAL GROUNDING: {grounding}]\n\n"
                f"User says: {user_message}"
            )
            # Replace the last user message with the augmented version
            self.conversation[-1] = {"role": "user", "content": augmented_message}

        try:
            response = send_message(system_prompt, self.conversation)
            self.conversation.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            logger.error("LLM error during session: %s", e)
            # Restore original user message if we augmented it
            self.conversation[-1] = {"role": "user", "content": user_message}
            return (
                "I'm sorry, I encountered a technical issue. "
                "Could you try sending that again?"
            )

    def end_session(self, session_notes: str | None = None) -> bool:
        """Run session end protocol.

        1. Generate session notes if not provided
        2. Save notes to memory
        3. Update treatment plan
        4. Return success/failure

        Args:
            session_notes: Optional pre-written session notes.
                If None, generated from the conversation.

        Returns:
            True if session was successfully ended and saved.
        """
        if not self.session_active:
            return False

        # Generate notes from conversation if not provided
        if session_notes is None:
            session_notes = self._generate_session_notes()

        # Save to memory
        save_success = save_session_notes(session_notes)

        # Update treatment plan
        self._update_treatment_plan(session_notes)

        self.session_active = False
        self.session_start_time = None

        return save_success

    def _generate_session_notes(self) -> str:
        """Generate a brief summary of the session from the conversation.

        Returns:
            Session notes as a string.
        """
        parts = []
        parts.append(f"Session date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Extract user messages for a brief summary
        user_messages = [
            msg["content"] for msg in self.conversation
            if msg["role"] == "user" and not msg["content"].startswith("[SYSTEM CONTEXT")
            and not msg["content"].startswith("[CLINICAL GROUNDING")
        ]
        if user_messages:
            parts.append(f"User messages: {len(user_messages)}")
            # Include first user message as context
            parts.append(f"Opening topic: {user_messages[0][:200]}")

        # Extract assistant messages count
        assistant_messages = [
            msg for msg in self.conversation if msg["role"] == "assistant"
        ]
        parts.append(f"Therapist responses: {len(assistant_messages)}")

        if self.session_start_time:
            duration = datetime.now() - self.session_start_time
            minutes = int(duration.total_seconds() / 60)
            parts.append(f"Duration: ~{minutes} minutes")

        return "\n".join(parts)

    def _update_treatment_plan(self, session_notes: str) -> None:
        """Update the treatment plan with session data.

        Args:
            session_notes: The session notes to log.
        """
        try:
            plan = load_config("treatment_plan.yaml")
        except FileNotFoundError:
            logger.warning("Treatment plan not found, skipping update")
            return

        # Update metadata
        plan["metadata"]["last_updated"] = datetime.now().isoformat()

        # Update exit ramp contact count
        exit_ramp = plan.get("exit_ramp", {})
        exit_ramp["total_contacts"] = exit_ramp.get("total_contacts", 0) + 1
        plan["exit_ramp"] = exit_ramp

        # Add to session log
        session_log = plan.get("session_log", [])
        session_log.append({
            "date": datetime.now().isoformat(),
            "notes_preview": session_notes[:200],
        })
        plan["session_log"] = session_log

        # Maintain usage signals at session end.
        usage_signals = plan.get("usage_signals", {})
        usage_signals.setdefault("trigger_time_contacts", 0)
        if self.session_context.get("meta_question_due"):
            usage_signals["meta_question_status"] = (
                f"addressed (session {self.session_context.get('session_count', '?')})"
            )
        usage_signals.setdefault("meta_question_status", "")
        plan["usage_signals"] = usage_signals

        save_config("treatment_plan.yaml", plan)

    def check_exit_ramp(self) -> bool:
        """Check if a meta-question should be asked this session.

        Returns:
            True if a meta-question is due.
        """
        return self.session_context.get("meta_question_due", False)