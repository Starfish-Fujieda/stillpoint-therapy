"""Onboarding wizard for Stillpoint Gradio UI.

Multi-step wizard that guides users through the onboarding process
(4 phases in PR 2, down from 6). A 5th end-of-wizard button screen
(the processing-style picker) lives below the wizard and is shown
after the 4 phases complete.

Returns the completion buttons (done_btn, setup_later_btn) for the
caller to wire to the view-switch in ``app/main.py``.
"""

import gradio as gr

from stillpoint.config import get_notebook_count
from stillpoint.onboarding import (
    PHASES,
    get_phase_questions,
    get_next_phase,
    is_phase_complete,
    process_answer,
    recommend_notebooks,
    generate_all_config,
    processing_style_picker,
)


def build_onboarding_view() -> tuple:
    """Build the onboarding wizard view.

    Returns:
        Tuple of (done_btn, setup_later_btn) for the caller to wire
        to the view-switch in ``app/main.py``.
    """
    # --- State ---
    state = gr.State(value={})
    current_phase = gr.State(value=PHASES[0])
    question_idx = gr.State(value=0)

    # --- Header ---
    gr.Markdown("# 🧘 Stillpoint Setup")
    progress_text = gr.Markdown(value=f"Step 1 of {len(PHASES)}: Welcome")

    # --- Question display area ---
    question_display = gr.Markdown(value="", elem_classes=["contain"])
    answer_input = gr.Textbox(
        label="Your answer",
        placeholder="Type your answer here...",
        visible=True,
        lines=2,
    )

    # For multiselect (checkboxes) - hidden by default
    answer_checkboxes = gr.CheckboxGroup(
        label="Select all that apply",
        choices=[],
        visible=False,
    )

    # For confirm buttons
    confirm_btn = gr.Button("Yes / Confirm", visible=False)
    skip_btn = gr.Button("Skip this question", visible=False)

    # Navigation
    with gr.Row():
        next_btn = gr.Button("Next →", variant="primary")
        back_btn = gr.Button("← Back", visible=True)

    # Status messages
    status_msg = gr.Markdown(value="")

    # --- Done button (hidden until onboarding completes) ---
    done_btn = gr.Button(
        "✅ Start Therapy",
        variant="primary",
        visible=False,
        size="lg",
    )

    # --- Secondary completion button — only shown when no notebooks
    # are configured. Both buttons trigger the same view-switch in
    # app/main.py. The "later" button exists so the user can
    # acknowledge the grounding gap explicitly without it being
    # auto-handled by the "Start Therapy" button.
    setup_later_btn = gr.Button(
        "I'll set up NotebookLM later",
        variant="secondary",
        visible=False,
    )

    # --- End-of-wizard processing-style picker (PR 2, Fix 4) ---
    # Hidden until the 4 phases complete. The 3 buttons set
    # state["processing_style"]["communication_preference"] to the
    # mapped old label, then call _finish_onboarding.
    picker_col, concrete_btn, analytical_btn, mixed_btn = processing_style_picker()

    # --- Helper functions ---
    def get_current_question(phase, idx):
        """Get the current question data."""
        questions = get_phase_questions(phase)
        if idx < len(questions):
            return questions[idx]
        return None

    def render_question(phase, idx, onboarding_state):
        """Render the current question and return UI updates."""
        q = get_current_question(phase, idx)
        if q is None:
            # No more questions in this phase
            return _advance_phase(phase, onboarding_state)

        q_type = q.get("type", "text")
        question_text = q.get("question", "")

        updates = {
            question_display: gr.update(value=question_text),
            status_msg: gr.update(value=""),
        }

        # Show appropriate input type
        if q_type == "info":
            updates[answer_input] = gr.update(visible=False)
            updates[answer_checkboxes] = gr.update(visible=False)
            updates[confirm_btn] = gr.update(visible=False)
            updates[skip_btn] = gr.update(visible=False)
        elif q_type == "multiselect":
            updates[answer_input] = gr.update(visible=False)
            updates[answer_checkboxes] = gr.update(
                visible=True, choices=q.get("choices", [])
            )
            updates[confirm_btn] = gr.update(visible=False)
            updates[skip_btn] = gr.update(visible=not q.get("required", False))
        elif q_type == "choice":
            updates[answer_input] = gr.update(
                visible=True,
                lines=1,
                placeholder="Type your choice (or part of it)...",
            )
            updates[answer_checkboxes] = gr.update(visible=False)
            updates[confirm_btn] = gr.update(visible=False)
            updates[skip_btn] = gr.update(visible=not q.get("required", False))
        elif q_type == "confirm":
            updates[answer_input] = gr.update(visible=False)
            updates[answer_checkboxes] = gr.update(visible=False)
            updates[confirm_btn] = gr.update(visible=True)
            updates[skip_btn] = gr.update(visible=False)
        elif q_type == "textarea":
            updates[answer_input] = gr.update(visible=True, lines=4, placeholder="")
            updates[answer_checkboxes] = gr.update(visible=False)
            updates[confirm_btn] = gr.update(visible=False)
            updates[skip_btn] = gr.update(visible=not q.get("required", False))
        else:  # text
            updates[answer_input] = gr.update(visible=True, lines=1, placeholder="")
            updates[answer_checkboxes] = gr.update(visible=False)
            updates[confirm_btn] = gr.update(visible=False)
            updates[skip_btn] = gr.update(visible=not q.get("required", False))

        return updates

    def _advance_phase(phase, onboarding_state):
        """Move to the next phase or show the processing-style picker."""
        next_phase = get_next_phase(phase)
        phase_idx = PHASES.index(phase) if phase in PHASES else 0

        if next_phase is None:
            # All 4 phases complete — show the processing-style picker
            # instead of finishing directly. The picker's click
            # handler will call _finish_onboarding.
            return _show_picker(onboarding_state)

        new_idx = PHASES.index(next_phase)
        updates = {
            progress_text: gr.update(
                value=f"Step {new_idx + 1} of {len(PHASES)}: {_phase_display_name(next_phase)}"
            ),
            current_phase: next_phase,
            question_idx: 0,
        }
        # Render first question of new phase
        render_updates = render_question(next_phase, 0, onboarding_state)
        updates.update(render_updates)
        return updates

    def _show_picker(onboarding_state):
        """Hide the wizard UI and reveal the processing-style picker.

        Called after the last phase (``notebooks``) completes. The
        picker's 3 buttons each have a click handler (wired below)
        that sets ``state["processing_style"]["communication_preference"]``
        and calls ``_finish_onboarding``.
        """
        return {
            progress_text: gr.update(value="One last thing..."),
            question_display: gr.update(visible=False),
            answer_input: gr.update(visible=False),
            answer_checkboxes: gr.update(visible=False),
            confirm_btn: gr.update(visible=False),
            skip_btn: gr.update(visible=False),
            next_btn: gr.update(visible=False),
            back_btn: gr.update(visible=False),
            picker_col: gr.update(visible=True),
            state: onboarding_state,
        }

    def on_picker_click(choice: str, onboarding_state):
        """Handle a picker button click: set the user's choice, finish.

        The picker buttons set ``state["processing_style"]["communication_preference"]``
        to one of the OLD labels so ``build_processing_style()`` can
        consume it unchanged. The mapping (per user decision):
        concrete → "Direct and straightforward", analytical →
        "Gentle and indirect", mixed → "It varies — read the room".
        """
        from stillpoint.onboarding import PICKER_TO_COMMUNICATION
        onboarding_state.setdefault("processing_style", {})
        onboarding_state["processing_style"]["communication_preference"] = (
            PICKER_TO_COMMUNICATION[choice]
        )
        return _finish_onboarding(onboarding_state)

    def _finish_onboarding(onboarding_state):
        """Generate all config and show completion.

        Renders a conditional message based on how many notebooks the
        user has configured:
        - 0 notebooks: 4-step NotebookLM checklist + Start Therapy +
          "I'll set up NotebookLM later" (PR 2, Fix 2)
        - >0 notebooks: "fully configured" message + Start Therapy
        """
        try:
            generate_all_config(onboarding_state)
            notebook_count = get_notebook_count()
            if notebook_count == 0:
                completion_text = (
                    "## Your therapist is ready! 🎉\n\n"
                    "Your therapist can chat now with **minimal built-in "
                    "grounding** (ACT basics, intrusive-thoughts vs intent). "
                    "For deeper clinical grounding, connect NotebookLM "
                    "(recommended, ~15 min setup).\n\n"
                    "### How to connect NotebookLM (4 steps)\n\n"
                    "1. **Create or sign in to a Google account** at "
                    "[notebooklm.google.com](https://notebooklm.google.com).\n"
                    "2. **Create a new notebook** — click the \"+ New "
                    "notebook\" button.\n"
                    "3. **Copy the notebook ID from the URL.** The URL "
                    "looks like `https://notebooklm.google.com/notebook/"
                    "<UUID>` — copy the UUID (the long string after "
                    "`/notebook/`).\n"
                    "4. **Paste the ID in Settings → Notebooks** — fill "
                    "in the Topic, paste the ID, and describe when to "
                    "query it."
                )
                show_setup_later = True
            else:
                completion_text = (
                    "## Your therapist is ready! 🎉\n\n"
                    f"Your therapist is fully configured "
                    f"({notebook_count} notebook{'s' if notebook_count != 1 else ''}). "
                    "Click **Start Therapy** below to begin your first "
                    "session."
                )
                show_setup_later = False
            return {
                progress_text: gr.update(value="✅ Setup Complete!"),
                question_display: gr.update(value=completion_text),
                answer_input: gr.update(visible=False),
                answer_checkboxes: gr.update(visible=False),
                confirm_btn: gr.update(visible=False),
                skip_btn: gr.update(visible=False),
                next_btn: gr.update(visible=False),
                back_btn: gr.update(visible=False),
                done_btn: gr.update(visible=True),
                setup_later_btn: gr.update(visible=show_setup_later),
                status_msg: gr.update(value=""),
            }
        except Exception as e:
            return {
                status_msg: gr.update(value=f"⚠️ Error generating config: {e}")
            }

    def _phase_display_name(phase):
        """Get a display-friendly name for a phase."""
        names = {
            "welcome": "Welcome",
            "character_design": "Design Your Therapist",
            "infrastructure": "Infrastructure Setup",
            "notebooks": "Knowledge Base Planning",
        }
        return names.get(phase, phase)

    # --- Event handlers ---
    def on_next(answer_text, checkbox_vals, phase, idx, onboarding_state):
        """Handle Next button click."""
        q = get_current_question(phase, idx)
        if q is None:
            return _advance_phase(phase, onboarding_state)

        q_type = q.get("type", "text")
        q_id = q.get("id", "")

        # Determine the answer value
        answer = answer_text
        if q_type == "multiselect":
            answer = checkbox_vals if checkbox_vals else []
        elif q_type == "confirm":
            answer = True
        elif q_type == "info":
            answer = "acknowledged"

        # Validate required questions
        if q.get("required") and not answer:
            return {
                status_msg: gr.update(value="⚠️ This question is required.")
            }

        # Process the answer
        onboarding_state = process_answer(phase, q_id, answer, onboarding_state)

        # Move to next question or phase
        next_idx = idx + 1
        questions = get_phase_questions(phase)

        if next_idx < len(questions):
            # Next question in same phase
            updates = {
                question_idx: next_idx,
                state: onboarding_state,
                answer_input: gr.update(value=""),
                answer_checkboxes: gr.update(value=[]),
            }
            render_updates = render_question(phase, next_idx, onboarding_state)
            updates.update(render_updates)
            return updates
        else:
            # Phase complete — check if can advance
            if is_phase_complete(phase, onboarding_state):
                updates = _advance_phase(phase, onboarding_state)
                updates[state] = onboarding_state
                updates[answer_input] = gr.update(value="")
                updates[answer_checkboxes] = gr.update(value=[])
                return updates
            else:
                return {
                    state: onboarding_state,
                    status_msg: gr.update(
                        value="⚠️ Please answer all required questions before proceeding."
                    ),
                }

    def on_skip(phase, idx, onboarding_state):
        """Handle Skip button click."""
        q = get_current_question(phase, idx)
        if q and not q.get("required"):
            onboarding_state = process_answer(
                phase, q.get("id", ""), "", onboarding_state
            )

        next_idx = idx + 1
        questions = get_phase_questions(phase)

        if next_idx < len(questions):
            updates = {
                question_idx: next_idx,
                state: onboarding_state,
                answer_input: gr.update(value=""),
            }
            render_updates = render_question(phase, next_idx, onboarding_state)
            updates.update(render_updates)
            return updates
        else:
            if is_phase_complete(phase, onboarding_state):
                updates = _advance_phase(phase, onboarding_state)
                updates[state] = onboarding_state
                return updates
            else:
                return {
                    state: onboarding_state,
                    status_msg: gr.update(
                        value="⚠️ Please answer all required questions."
                    ),
                }

    def on_back(phase, idx, onboarding_state):
        """Handle Back button click."""
        if idx > 0:
            prev_idx = idx - 1
            updates = {
                question_idx: prev_idx,
                status_msg: gr.update(value=""),
            }
            render_updates = render_question(phase, prev_idx, onboarding_state)
            updates.update(render_updates)
            return updates
        else:
            # Go to previous phase
            phase_idx = PHASES.index(phase) if phase in PHASES else 0
            if phase_idx > 0:
                prev_phase = PHASES[phase_idx - 1]
                prev_phase_questions = get_phase_questions(prev_phase)
                prev_idx = max(0, len(prev_phase_questions) - 1)
                updates = {
                    current_phase: prev_phase,
                    question_idx: prev_idx,
                    progress_text: gr.update(
                        value=f"Step {phase_idx} of {len(PHASES)}: {_phase_display_name(prev_phase)}"
                    ),
                    status_msg: gr.update(value=""),
                }
                render_updates = render_question(prev_phase, prev_idx, onboarding_state)
                updates.update(render_updates)
                return updates
            return {status_msg: gr.update(value="")}

    def on_confirm(phase, idx, onboarding_state):
        """Handle Confirm button click."""
        q = get_current_question(phase, idx)
        if q:
            onboarding_state = process_answer(
                phase, q.get("id", ""), True, onboarding_state
            )

        next_idx = idx + 1
        questions = get_phase_questions(phase)

        if next_idx < len(questions):
            updates = {
                question_idx: next_idx,
                state: onboarding_state,
            }
            render_updates = render_question(phase, next_idx, onboarding_state)
            updates.update(render_updates)
            return updates
        else:
            if is_phase_complete(phase, onboarding_state):
                updates = _advance_phase(phase, onboarding_state)
                updates[state] = onboarding_state
                return updates
            else:
                return {
                    state: onboarding_state,
                    status_msg: gr.update(value="⚠️ Please complete required items."),
                }

    # --- Wire up events ---
    next_btn.click(
        fn=on_next,
        inputs=[answer_input, answer_checkboxes, current_phase, question_idx, state],
        outputs=[
            question_display, answer_input, answer_checkboxes,
            confirm_btn, skip_btn, next_btn, back_btn,
            done_btn, progress_text, status_msg,
            current_phase, question_idx, state,
        ],
    )

    skip_btn.click(
        fn=on_skip,
        inputs=[current_phase, question_idx, state],
        outputs=[
            question_display, answer_input, answer_checkboxes,
            confirm_btn, skip_btn, next_btn, back_btn,
            done_btn, progress_text, status_msg,
            current_phase, question_idx, state,
        ],
    )

    back_btn.click(
        fn=on_back,
        inputs=[current_phase, question_idx, state],
        outputs=[
            question_display, answer_input, answer_checkboxes,
            confirm_btn, skip_btn, next_btn, back_btn,
            done_btn, progress_text, status_msg,
            current_phase, question_idx, state,
        ],
    )

    confirm_btn.click(
        fn=on_confirm,
        inputs=[current_phase, question_idx, state],
        outputs=[
            question_display, answer_input, answer_checkboxes,
            confirm_btn, skip_btn, next_btn, back_btn,
            done_btn, progress_text, status_msg,
            current_phase, question_idx, state,
        ],
    )

    # Picker button click handlers (PR 2, Fix 4). Each button sets
    # the communication_preference in state and advances to
    # _finish_onboarding. Outputs match _finish_onboarding's update
    # dict (all the wizard UI components + the post-onboarding
    # buttons + state).
    picker_outputs = [
        question_display, answer_input, answer_checkboxes,
        confirm_btn, skip_btn, next_btn, back_btn,
        done_btn, setup_later_btn, progress_text, status_msg,
        state,
    ]
    concrete_btn.click(
        fn=on_picker_click,
        inputs=[gr.State("concrete"), state],
        outputs=picker_outputs,
    )
    analytical_btn.click(
        fn=on_picker_click,
        inputs=[gr.State("analytical"), state],
        outputs=picker_outputs,
    )
    mixed_btn.click(
        fn=on_picker_click,
        inputs=[gr.State("mixed"), state],
        outputs=picker_outputs,
    )

    return done_btn, setup_later_btn