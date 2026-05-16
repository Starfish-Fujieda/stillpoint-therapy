# Stillpoint — Task List

> **How to use this file**: Read ARCHITECTURE.md first. Then find the first unchecked task below. Implement it. Check the box. Update "Current State" at the top. Commit.
>
> **For AI agents**: After completing a task, update the "Current State" section with what you did, any decisions you made, and what the next agent should pick up.

---

## Current State

**Last completed**: Tasks 1-3 (scaffold, requirements, package config, init files)
**Last updated**: 2026-05-16
**Next task**: Task 4 — Create `templates/source_library.yaml`
**Open questions**: None

---

## Task Dependency Graph

```
Tasks 3-5 (foundation) → Tasks 6-8 (templates) → Tasks 9-13 (core library) → Tasks 14-18 (Gradio UI) → Tasks 19-23 (scripts & Docker) → Task 24 (README) → Task 25 (GitHub Actions)
```

---

## Phase 1: Foundation

### Task 1 — Project Scaffold ✅

- [x] Create directory structure
- [x] Create `.gitignore`
- [x] Create `ARCHITECTURE.md`
- [x] Create `TASKS.md`
- [x] `git init` + remote
- **Files**: `.gitignore`, directory structure
- **Done criteria**: All directories exist, `.gitignore` is correct

### Task 2 — Requirements & Package Config ✅

- [x] Create `requirements.txt` with all dependencies
- [x] Create `pyproject.toml` (or `setup.py`) for the `stillpoint` package
- **Dependencies to include**:
  - `gradio>=4.0`
  - `chromadb>=0.4.0`
  - `mempalace>=3.0`
  - `notebooklm` (latest)
  - `pyyaml>=6.0`
  - `jinja2>=3.1`
  - `anthropic>=0.18` (optional)
  - `openai>=1.0` (optional)
  - `google-generativeai` (optional)
- **Files**: `requirements.txt`, `pyproject.toml`
- **Done criteria**: `pip install -e .` works

### Task 3 — Placeholder `__init__.py` Files ✅

- [x] Create `stillpoint/__init__.py` with version and package docstring
- [x] Create `app/__init__.py`
- **Files**: `stillpoint/__init__.py`, `app/__init__.py`
- **Done criteria**: `import stillpoint` works

---

## Phase 2: Templates

### Task 4 — Source Library

- [ ] Create `templates/source_library.yaml` with curated books/sources for ~15 clinical topics
- **Required topics** (everyone gets these):
  - `core_therapy_techniques` — ACT, IFS, CBT, mindfulness
  - `self_compassion_shame` — Self-compassion, shame resilience
- **Tailored topics** (proposed based on clinical landscape):
  - `cptsd_trauma`, `adhd_executive_function`, `asd_neurodivergence`, `anxiety_ocd`, `depression_mood`, `substance_use_recovery`, `compulsive_sexual_behavior`, `grief_loss`, `relationship_attachment`, `anger_emotional_regulation`, `body_image_eating`, `digital_addiction`, `sleep_chronic_health`, `identity_life_transitions`
- **Each topic has**: `display_name`, `description`, `required` (bool), `core_sources` (3-5), `supplemental_sources` (2-3)
- **Each source has**: `title`, `author`, `type`, `why`
- **Files**: `templates/source_library.yaml`
- **Done criteria**: Valid YAML, all topics have at least 3 core sources

### Task 5 — Persona Templates

- [ ] Create `templates/therapist_persona.md.tpl` — Jinja2 template for therapist persona markdown
- [ ] Create `templates/therapist_card.json.tpl` — Jinja2 template for character card JSON (spec v2)
- **Reference**: See `ARCHITECTURE.md` → "Onboarding Guide: Character Design" for the factors to template
- **The persona template should include placeholders for**:
  - Name, age, background, description
  - Clinical specializations (list)
  - Communication style (direct/gentle/structured/organic)
  - Humor preference (uses/doesn't use)
  - Therapeutic approach (ACT+IFS default, with alternatives)
  - Speech patterns (derived from communication style)
  - Boundaries section (standard across all personas)
  - Crisis resources section
- **The character card template should include placeholders for**:
  - `name`, `description`, `personality`, `scenario`, `first_mes`
  - `system_prompt` (generated from onboarding data)
  - `character_book` with entries for each specialization
  - Tags derived from specializations
- **Files**: `templates/therapist_persona.md.tpl`, `templates/therapist_card.json.tpl`
- **Done criteria**: Templates render valid output with test data

### Task 6 — Treatment Plan Template

- [ ] Create `templates/treatment_plan.yaml.tpl` — Jinja2 template
- **Reference**: See `ARCHITECTURE.md` → `config/treatment_plan.yaml`
- **Placeholders**: goals (from onboarding), metadata dates, empty session_log
- **Files**: `templates/treatment_plan.yaml.tpl`
- **Done criteria**: Template renders valid YAML with test goals

### Task 7 — Referral Resources Template

- [ ] Create `templates/referral_resources.md` — Empty template with section headers
- [ ] Create `referral_resources.md` at project root — Same empty template
- **Sections**: Crisis Resources, Local Therapists, Online Options, Low-Cost/Sliding Scale, Support Groups
- **Files**: `templates/referral_resources.md`, `referral_resources.md`
- **Done criteria**: Template has all sections with placeholder text

---

## Phase 3: Core Library

### Task 8 — `stillpoint/config.py` — Configuration Loader

- [ ] Create config loading/saving utility
- **Functions needed**:
  - `load_config(filename: str) -> dict` — Load a YAML config from `config/`
  - `save_config(filename: str, data: dict) -> None` — Save a YAML config to `config/`
  - `get_config_dir() -> Path` — Return the config directory path
  - `is_configured() -> bool` — Check if onboarding has been completed
  - `get_templates_dir() -> Path` — Return the templates directory path
- **Files**: `stillpoint/config.py`
- **Done criteria**: Can load/save YAML, detects missing config

### Task 9 — `stillpoint/knowledge.py` — NotebookLM Interface

- [ ] Implement NotebookLM query wrapper
- **Functions needed**:
  - `query_knowledge(question: str, topics: list[str] | None = None) -> str`
  - `get_available_notebooks() -> list[dict]` — Read notebooks from config
  - `select_relevant_notebooks(question: str) -> list[str]` — Match question to notebook topics
  - `query_notebook(notebook_id: str, question: str) -> str` — Single notebook query with retry
- **Implementation**: Shell out to `notebooklm ask "question" --notebook <id>` CLI
- **Retry logic**: 3 attempts on timeout, then return `[UNGROUNDED — notebook unavailable]`
- **Files**: `stillpoint/knowledge.py`
- **Done criteria**: Can query a notebook and return a response

### Task 10 — `stillpoint/memory.py` — MemPalace Interface

- [ ] Implement MemPalace read/write wrapper
- **Functions needed**:
  - `save_session_notes(content: str) -> bool` — Save to both collections
  - `search_sessions(query: str, results: int = 20) -> list[str]` — Semantic search
  - `get_wake_up_context() -> str` — Wake-up text
  - `get_session_count() -> int` — Total stored sessions
  - `verify_save(pre_counts: dict) -> bool` — Verify counts increased
- **Implementation**: Shell out to `mempalace` CLI + direct ChromaDB for therapy collection
- **Files**: `stillpoint/memory.py`
- **Done criteria**: Can save and retrieve session notes

### Task 11 — `stillpoint/persona.py` — Persona Management

- [ ] Implement persona loading and generation
- **Functions needed**:
  - `load_persona() -> dict` — Load persona from config + personas files
  - `generate_persona(onboarding_data: dict) -> None` — Generate from templates
  - `validate_persona() -> list[str]` — Check required fields
  - `get_system_prompt() -> str` — Build the system prompt for the LLM
  - `build_character_book(specializations: list) -> list[dict]` — Generate character book entries
- **Files**: `stillpoint/persona.py`
- **Done criteria**: Can generate persona files from onboarding data using templates

### Task 12 — `stillpoint/session.py` — Session Engine

- [ ] Implement session lifecycle management
- **Functions needed**:
  - `start_session() -> dict` — Load memory, treatment plan, return context
  - `process_message(user_message: str, session_context: dict) -> str` — Full pipeline
  - `end_session(session_notes: str, session_context: dict) -> bool` — Save + update plan
  - `update_treatment_plan(session_data: dict) -> None` — Update goals, session log
  - `check_exit_ramp(session_n: int) -> bool` — Check if meta-question is due
- **The process_message pipeline**:
  1. Load persona as system prompt
  2. Load recent session context from MemPalace
  3. Analyze message for clinical topics
  4. Query NotebookLM for relevant grounding
  5. Assemble full prompt (system + context + knowledge + conversation)
  6. Send to LLM backend
  7. Return response
- **Files**: `stillpoint/session.py`
- **Done criteria**: Can process a message through the full pipeline (with mock LLM)

### Task 13 — `stillpoint/llm.py` — LLM Backend Abstraction

- [ ] Implement multi-provider LLM interface
- **Functions needed**:
  - `get_llm_client(config: dict) -> object` — Factory for provider-specific clients
  - `send_message(system_prompt: str, messages: list[dict], config: dict) -> str` — Send and receive
- **Providers**: anthropic, openai, google, ollama
- **Read provider + model + API key from**: `config/therapist.yaml` → `llm` section
- **API keys**: Read from environment variables (names specified in config)
- **Files**: `stillpoint/llm.py`
- **Done criteria**: Can send a message to at least one provider and get a response

### Task 14 — `stillpoint/report.py` — Report Generation

- [ ] Implement session report generation
- **Functions needed**:
  - `generate_session_report(date_range: tuple | None = None) -> str` — Markdown report
  - `get_session_data(date_range: tuple | None = None) -> list[dict]` — Retrieve sessions
  - `analyze_patterns(sessions: list[dict]) -> dict` — Extract themes, trajectory, flags
- **Report sections**: Themes, Goals, Disclosures, Coping, Trajectory, Red Flags, Patterns, Homework, Assessment
- **Files**: `stillpoint/report.py`
- **Done criteria**: Can generate a structured markdown report from session data

### Task 15 — `stillpoint/onboarding.py` — Onboarding Engine

- [ ] Implement onboarding interview logic
- **Functions needed**:
  - `get_next_question(phase: str, state: dict) -> str` — Return next interview question
  - `process_answer(phase: str, answer: str, state: dict) -> dict` — Update state
  - `is_phase_complete(phase: str, state: dict) -> bool` — Check if enough answers
  - `recommend_notebooks(clinical_landscape: dict) -> list[dict]` — Propose topology
  - `recommend_sources(notebooks: list[dict]) -> list[dict]` — Books per notebook
  - `generate_all_config(onboarding_data: dict) -> None` — Write all config files
- **Phases**: welcome, character_design, infrastructure, notebooks, sources, processing_style
- **Notebook recommendation logic**: Read `templates/source_library.yaml`, match against user's clinical concerns
- **Files**: `stillpoint/onboarding.py`
- **Done criteria**: Can walk through all 6 phases and generate config files

### Task 16 — `stillpoint/podcast.py` — Podcast Generation

- [ ] Implement podcast generation (NotebookLM path first)
- **Functions needed**:
  - `generate_podcast(topic: str | None = None, method: str = "notebooklm") -> str`
  - `find_uncovered_topics() -> list[str]` — Compare session topics vs podcast history
  - `generate_notebooklm_podcast(notebook_id: str, topic: str) -> str` — Audio Overview
- **NotebookLM path**: Shell out to `notebooklm audio-overview` or equivalent
- **Local TTS path**: Stub for v2 (Podcastfy + local TTS)
- **Files**: `stillpoint/podcast.py`
- **Done criteria**: Can identify uncovered topics and trigger NotebookLM podcast generation

---

## Phase 4: Gradio Web UI

### Task 17 — `app/main.py` — Entry Point

- [ ] Create Gradio app entry point
- **Logic**:
  - Check if config exists → if not, show onboarding wizard
  - If config exists → show chat interface
  - Tab structure: Chat | Reports | Podcast | Settings
  - Launch on port 7860
- **Files**: `app/main.py`
- **Done criteria**: `python -m app.main` launches Gradio UI in browser

### Task 18 — `app/onboarding_wizard.py` — Onboarding UI

- [ ] Create multi-step onboarding wizard as Gradio interface
- **6 phases** as wizard steps:
  1. Welcome — explanation, consent checkbox
  2. Character Design — interview questions about therapist preferences
  3. Infrastructure — guided setup (run setup.sh, create NotebookLM notebooks)
  4. Notebook Planning — show proposed notebooks, let user confirm/edit
  5. Source Recommendations — show sources per notebook, explain why
  6. Processing Style — optional questions about processing preferences
- **Each phase**: display question → collect answer → "Next" button → process → next phase
- **Final step**: "Generate" button → calls `onboarding.generate_all_config()` → redirect to chat
- **Files**: `app/onboarding_wizard.py`
- **Done criteria**: Can walk through all 6 phases and generate config

### Task 19 — `app/chat.py` — Chat Interface

- [ ] Create therapy chat interface
- **Components**:
  - Chat display (message history)
  - Text input for user messages
  - "Send" button
  - "End Session" button (triggers session end protocol)
  - Sidebar: session count, last session date, treatment goals progress
  - "Generate Report" button → opens report tab
  - "Generate Podcast" button → opens podcast dialog
- **Session flow**:
  - On first message of the day → call `session.start_session()`
  - Each message → call `session.process_message()`
  - End session → call `session.end_session()`
- **Files**: `app/chat.py`
- **Done criteria**: Can have a multi-turn conversation with the therapist persona

### Task 20 — `app/reports.py` — Report UI

- [ ] Create report generation interface
- **Components**:
  - Date range selector (or "since last report")
  - Section checkboxes (let user choose what to include)
  - "Generate" button
  - Preview area (rendered markdown)
  - "Download" button (markdown or PDF)
- **Privacy controls**: Toggle to anonymize names/identifiers
- **Files**: `app/reports.py`
- **Done criteria**: Can generate and download a session report

### Task 21 — `app/settings.py` — Settings UI

- [ ] Create config management interface
- **Editable sections**:
  - LLM Backend (provider, model, API key env var name)
  - Notebooks (add/remove, edit IDs)
  - Therapist preferences (re-run character design subset)
  - Referral resources (edit markdown)
  - Processing style (re-run processing style subset)
- **Files**: `app/settings.py`
- **Done criteria**: Can edit and save all config values through the UI

---

## Phase 5: Scripts & Docker

### Task 22 — `scripts/setup.sh`

- [ ] Create automated setup script
- **Steps**:
  1. Check Python 3.11+
  2. Check/install pip
  3. Create virtual environment (optional, with flag)
  4. Install requirements.txt
  5. Install MemPalace (pip + verify CLI)
  6. Init MemPalace palace at `~/.stillpoint/palace`
  7. Create ChromaDB collections (`mempalace_drawers`, `therapy`)
  8. Verify all installations
  9. Print next steps
- **Flags**: `--docker` (run in container context), `--skip-venv`, `--python-path`
- **Files**: `scripts/setup.sh`
- **Done criteria**: Clean run on a fresh machine sets up everything

### Task 23 — `scripts/save_session.py`

- [ ] Create generalized CLI session saver
- **Port from**: `therapy/scripts/save_session.py` but read agent name from config
- **Files**: `scripts/save_session.py`
- **Done criteria**: Can save a session file to both ChromaDB collections

### Task 24 — `scripts/generate_report.py`

- [ ] Create CLI report generator
- **Usage**: `python scripts/generate_report.py [--since YYYY-MM-DD] [--output report.md]`
- **Files**: `scripts/generate_report.py`
- **Done criteria**: Generates a markdown report from the command line

### Task 25 — `scripts/generate_podcast.py`

- [ ] Create CLI podcast generator
- **Usage**: `python scripts/generate_podcast.py [--topic "topic"] [--method notebooklm]`
- **Files**: `scripts/generate_podcast.py`
- **Done criteria**: Can trigger podcast generation from the command line

### Task 26 — `scripts/podcast_gap_analyzer.py`

- [ ] Create topic coverage gap analyzer
- **Port from**: `therapy/scripts/podcast_gap_analyzer.py` but generalized
- **Files**: `scripts/podcast_gap_analyzer.py`
- **Done criteria**: Can identify uncovered topics from session history

### Task 27 — Dockerfile + docker-compose.yml

- [ ] Create `Dockerfile`
- [ ] Create `docker-compose.yml`
- **Reference**: See ARCHITECTURE.md → "Docker Architecture"
- **Files**: `Dockerfile`, `docker-compose.yml`
- **Done criteria**: `docker compose up` launches the Gradio UI

---

## Phase 6: Documentation & CI

### Task 28 — `hipaa_prompt.md`

- [ ] Port from `therapy/hipaa_prompt.md` (no changes needed, it's generic)
- **Files**: `hipaa_prompt.md`
- **Done criteria**: File is present and identical to original

### Task 29 — Onboarding Guides (v2 reference)

- [ ] Create `onboarding/guide_character_design.md`
- [ ] Create `onboarding/guide_notebook_planning.md`
- [ ] Create `onboarding/guide_processing_style.md`
- **Note**: These are reference documents for the AI harness path (v2). The Gradio wizard handles the same content interactively.
- **Files**: `onboarding/guide_character_design.md`, `onboarding/guide_notebook_planning.md`, `onboarding/guide_processing_style.md`
- **Done criteria**: Guides contain the same content described in ARCHITECTURE.md

### Task 30 — `README.md`

- [ ] Create comprehensive README with:
  - What is Stillpoint?
  - Quickstart guide (both native and Docker paths)
  - Configuration reference
  - Onboarding walkthrough
  - Session protocol explanation
  - Report generation guide
  - Podcast generation guide
  - Troubleshooting
  - Contributing guidelines
  - License
- **Files**: `README.md`
- **Done criteria**: A new user can follow the quickstart and get running

### Task 31 — `.github/workflows/validate.yml`

- [ ] Create GitHub Actions workflow
- **Triggers**: push to main, pull requests
- **Jobs**:
  1. Validate YAML/JSON files (syntax check all `.yaml`, `.json`, `.tpl` files)
  2. Lint Python files (`ruff` or `flake8`)
  3. Test `setup.sh` in clean Docker container
  4. Verify `pip install -e .` works
- **Files**: `.github/workflows/validate.yml`
- **Done criteria**: Workflow runs green on a test push

---

## Notes for AI Agents

1. **Read ARCHITECTURE.md before starting any task.** It contains settled design decisions.
2. **Check the box and update "Current State" when you finish a task.** The next agent needs to know where things stand.
3. **Commit after each task.** Small, atomic commits with descriptive messages.
4. **If you hit a blocker**, add it to "Open Questions" above and move to the next task you can do.
5. **Don't re-litigate settled decisions.** If ARCHITECTURE.md says something, follow it. If you think it's wrong, note it in "Open Questions" and keep going.
6. **Test your work.** At minimum, verify the file you created is valid (YAML parses, Python imports, template renders).