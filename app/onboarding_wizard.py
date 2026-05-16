"""Onboarding wizard for Stillpoint Gradio UI.

Multi-step wizard that guides users through the 6-phase onboarding process.
Returns a Gradio component that signals completion when clicked.
"""

import gradio as gr

from stillpoint.onboarding import (
    PHASES,
    get_phase_questions,
    get_next_phase,
    is_phase_complete,
    process_answer,
    recommend_notebooks,
    recommend_sources,
    generate_all_config,
)


def build_onboarding_view() -> gr.Button:
    """Build the onboarding wizard view.

    Returns:
        A hidden button that gets enabled when onboarding completes.
        The main app uses this button's click to switch to chat view.
    """
    # --- State ---
    state = gr.State(value={})
    current_phase = gr.State(value=PHASES[0])
    question_idx = gr.State(value=0)

    # --- Header ---
    gr.Markdown("# 🧘 Stillpoint Setup")
    progress_text = gr.Markdown(value="Step 1 of 6: Welcome")

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
        """Move to the next phase or finish onboarding."""
        next_phase = get_next_phase(phase)
        phase_idx = PHASES.index(phase) if phase in PHASES else 0

        if next_phase is None:
            # Onboarding complete — generate config
            return _finish_onboarding(onboarding_state)

        new_idx = PHASES.index(next_phase)
        updates = {
            progress_text: gr.update(
                value=f"Step {new_idx + 1} of 6: {_phase_display_name(next_phase)}"
            ),
            current_phase: next_phase,
            question_idx: 0,
        }
        # Render first question of new phase
        render_updates = render_question(next_phase, 0, onboarding_state)
        updates.update(render_updates)
        return updates

    def _finish_onboarding(onboarding_state):
        """Generate all config and show completion."""
        try:
            generate_all_config(onboarding_state)
            return {
                progress_text: gr.update(value="✅ Setup Complete!"),
                question_display: gr.update(
                    value=(
                        "## Your therapist is ready! 🎉\n\n"
                        "All configuration has been saved. Click **Start Therapy** below "
                        "to begin your first session."
                    )
                ),
                answer_input: gr.update(visible=False),
                answer_checkboxes: gr.update(visible=False),
                confirm_btn: gr.update(visible=False),
                skip_btn: gr.update(visible=False),
                next_btn: gr.update(visible=False),
                back_btn: gr.update(visible=False),
                done_btn: gr.update(visible=True),
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
            "sources": "Source Recommendations",
            "processing_style": "Processing Style",
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
                        value=f"Step {phase_idx} of 6: {_phase_display_name(prev_phase)}"
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

    return done_btn