# Stillpoint — Claude Code Configuration

Stillpoint is an AI-assisted self-therapy framework: a Python CLI/Gradio app
with a customizable therapist persona, clinical knowledge grounding, and
persistent session memory.

## Rules

- Do what has been asked; nothing more, nothing less
- NEVER create files unless necessary — prefer editing existing files
- NEVER create documentation files unless explicitly requested
- Keep working files and tests out of the repo root — use `app/`, `stillpoint/`,
  `tests/`, `scripts/`, `config/`
- ALWAYS read a file before editing it
- NEVER commit secrets, credentials, or `.env` files
- Validate input at system boundaries

## Project Layout

- `app/` — CLI / Gradio entry points: `main`, `chat`, `onboarding_wizard`,
  `reports`, `settings`
- `stillpoint/` — core package: `config`, `knowledge`, `llm`, `memory`,
  `onboarding`, `persona`, `podcast`, `report`, `session`
- `scripts/` — setup and generation utilities (`setup.sh`, `generate_*.py`,
  `save_session.py`)
- `tests/` — pytest suite
- `config/`, `personas/`, `templates/` — user-generated and template content
- `ARCHITECTURE.md`, `TASKS.md` — design decisions marked "settled" require
  Rich's sign-off before changing

## Build & Run

```bash
scripts/setup.sh                 # one-time setup (creates .venv, installs deps)
pip install -e ".[dev]"          # editable install with dev tooling
./run.sh                         # launch the app (python -m app.main)
```

- Python 3.11+. Entry point: `app.main:main` (also the `stillpoint` script).
- LLM providers are optional extras: `anthropic`, `openai`, `google`.
- `notebooklm-py` is an external CLI installed via `pipx`, not a pip dependency.

## Test & Lint

```bash
pytest                           # test suite (testpaths = tests/)
ruff check .                     # lint (line-length 100, py311)
```

- CI: `.github/workflows/validate.yml` runs syntax (`py_compile`) and import
  checks on push/PR to `main`.
- ALWAYS run `pytest` after code changes.
