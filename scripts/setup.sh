#!/usr/bin/env bash
#
# Stillpoint — automated setup
#
# Gets a fresh machine from zero to "ready to run", then leaves the user with
# exactly one manual step: authenticating the NotebookLM CLI.
#
# What this does:
#   1. Verify Python 3.11+
#   2. Create the project virtualenv (.venv) and install dependencies
#   3. Bootstrap pipx if missing
#   4. Install the notebooklm-py CLI (with browser automation support)
#   5. Install the Chromium browser Playwright needs
#   6. Check NotebookLM auth status and prompt for `notebooklm login` if needed
#
# Safe to re-run: every step is idempotent.

set -euo pipefail

# ---- output helpers ---------------------------------------------------------
if [[ -t 1 ]]; then
  BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
  BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi
step() { echo; echo "${BOLD}==> $*${RESET}"; }
ok()   { echo "${GREEN}    ✓ $*${RESET}"; }
warn() { echo "${YELLOW}    ! $*${RESET}"; }
die()  { echo "${RED}    ✗ $*${RESET}" >&2; exit 1; }

# ---- locate project root ----------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "${BOLD}Stillpoint setup${RESET}  —  $PROJECT_ROOT"

# ---- 1. Python --------------------------------------------------------------
step "Checking Python"
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)' 2>/dev/null; then
      PYTHON="$candidate"; break
    fi
  fi
done
[[ -n "$PYTHON" ]] || die "Python 3.11+ not found. Install it and re-run this script."
ok "Using $("$PYTHON" --version 2>&1) ($(command -v "$PYTHON"))"

# ---- 2. Project virtualenv --------------------------------------------------
step "Creating project virtualenv (.venv)"
if [[ ! -d .venv ]]; then
  "$PYTHON" -m venv .venv
  ok "Created .venv"
else
  ok ".venv already exists"
fi
VENV_PY=".venv/bin/python"

echo "    Installing dependencies (this can take a few minutes)..."
"$VENV_PY" -m pip install --quiet --upgrade pip
# notebooklm is an external CLI installed via pipx below — not a pip dependency.
grep -vE '^[[:space:]]*#|^[[:space:]]*$|notebooklm' requirements.txt \
  | "$VENV_PY" -m pip install --quiet -r /dev/stdin
"$VENV_PY" -m pip install --quiet -e . --no-deps
ok "Dependencies installed into .venv"

# ---- 3. pipx ----------------------------------------------------------------
step "Checking pipx (for the NotebookLM CLI)"
if ! command -v pipx >/dev/null 2>&1; then
  warn "pipx not found — installing it"
  "$PYTHON" -m pip install --user --quiet pipx
  "$PYTHON" -m pipx ensurepath >/dev/null 2>&1 || true
  # ensurepath updates shell rc files, not this session — add it manually here.
  export PATH="$HOME/.local/bin:$PATH"
  ok "pipx installed"
else
  ok "pipx already installed"
fi
PIPX="pipx"
command -v pipx >/dev/null 2>&1 || PIPX="$PYTHON -m pipx"

# ---- 4. notebooklm-py CLI ---------------------------------------------------
step "Installing the NotebookLM CLI (notebooklm-py)"
if $PIPX list 2>/dev/null | grep -q 'notebooklm-py'; then
  $PIPX upgrade notebooklm-py >/dev/null 2>&1 || true
  ok "notebooklm-py already installed (upgraded if newer was available)"
else
  # [browser] extra pulls in Playwright, required for `notebooklm login`.
  $PIPX install "notebooklm-py[browser]"
  ok "notebooklm-py installed"
fi

# ---- 5. Playwright browser --------------------------------------------------
step "Installing the Chromium browser for NotebookLM automation"
PIPX_VENVS="$( { $PIPX environment --value PIPX_LOCAL_VENVS 2>/dev/null; } || true )"
[[ -n "$PIPX_VENVS" ]] || PIPX_VENVS="$HOME/.local/pipx/venvs"
PLAYWRIGHT_BIN="$PIPX_VENVS/notebooklm-py/bin/playwright"
if [[ -x "$PLAYWRIGHT_BIN" ]]; then
  # --with-deps also installs the OS libraries Chromium needs to launch.
  # No-op on macOS; on Linux it uses the system package manager (needs root/sudo).
  "$PLAYWRIGHT_BIN" install --with-deps chromium
  ok "Chromium installed"
else
  warn "Could not locate Playwright in the notebooklm-py venv."
  warn "Run this manually:  $PIPX runpip notebooklm-py exec playwright install --with-deps chromium"
fi

# ---- 6. NotebookLM authentication -------------------------------------------
step "Checking NotebookLM authentication"
NLM_STORAGE="${HOME}/.notebooklm/storage_state.json"
if [[ -f "$NLM_STORAGE" ]]; then
  ok "NotebookLM session found ($NLM_STORAGE)"
  echo "    If grounding later fails with an auth error, re-run:  notebooklm login"
else
  warn "Not authenticated yet — this is the one manual step."
  echo
  echo "    NotebookLM grounding is a core Stillpoint feature. To enable it,"
  echo "    authenticate the CLI with your Google account:"
  echo
  echo "        ${BOLD}notebooklm login${RESET}"
  echo
  echo "    This opens a browser for a one-time Google sign-in."
fi

# ---- done -------------------------------------------------------------------
step "Setup complete"
echo
echo "    Next steps:"
echo
echo "      1. Activate the environment:   ${BOLD}source .venv/bin/activate${RESET}"
if [[ ! -f "$NLM_STORAGE" ]]; then
  echo "      2. Authenticate NotebookLM:    ${BOLD}notebooklm login${RESET}"
  echo "      3. Launch the app:             ${BOLD}python -m app.main${RESET}"
else
  echo "      2. Launch the app:             ${BOLD}python -m app.main${RESET}"
fi
echo
if ! command -v notebooklm >/dev/null 2>&1; then
  warn "'notebooklm' is not on your PATH in this shell."
  warn "Open a new terminal, or run:  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo
echo "${BOLD}Setup complete.${RESET}"
echo
echo "To launch Stillpoint:"
echo "    ${GREEN}bash run.sh${RESET}"
echo
