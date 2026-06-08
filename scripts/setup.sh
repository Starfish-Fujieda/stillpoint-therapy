#!/usr/bin/env bash
#
# Stillpoint — automated setup
#
# Gets a fresh machine from zero to "ready to run", then leaves the user with
# exactly one manual step: authenticating the NotebookLM CLI.
#
# Steps:
#   0. Pre-flight checks (working dir, Python 3.11+, disk, internet, write perms, existing install)
#   1. Create the project virtualenv (.venv) and install dependencies
#   2. Bootstrap pipx if missing
#   3. Install the notebooklm-py CLI (with browser automation support)
#   4. Install the Chromium browser Playwright needs
#   5. Check NotebookLM auth status and prompt for `notebooklm login` if needed
#
# Flags:
#   --verbose    Show full command output (debug mode)
#   --quiet      Suppress progress output (use for CI)
#   --dry-run    Run pre-flight and print the install plan, don't execute installs
#   --help       Show this help
#
# Safe to re-run: every step is idempotent.

set -euo pipefail

# ---- output helpers ---------------------------------------------------------
if [[ -t 1 ]]; then
  BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
  BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi
# step/ok respect --quiet; warn/die always print to stderr.
step() { [[ ${QUIET:-0} -eq 1 ]] || { echo; echo "${BOLD}==> $*${RESET}"; }; }
ok()   { [[ ${QUIET:-0} -eq 1 ]] || echo "${GREEN}    ✓ $*${RESET}"; }
warn() { echo "${YELLOW}    ! $*${RESET}" >&2; }
die()  { echo "${RED}    ✗ $*${RESET}" >&2; exit 1; }

# ---- flag parsing -----------------------------------------------------------
VERBOSE=0
QUIET=0
DRY_RUN=0
for arg in "$@"; do
  case $arg in
    --verbose) VERBOSE=1 ;;
    --quiet)   QUIET=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --help|-h)
      cat <<'EOF'
Stillpoint — automated setup

Gets a fresh machine from zero to "ready to run", then leaves the user with
exactly one manual step: authenticating the NotebookLM CLI.

Steps:
  0. Pre-flight checks (working dir, Python 3.11+, disk, internet, write perms, existing install)
  1. Create the project virtualenv (.venv) and install dependencies
  2. Bootstrap pipx if missing
  3. Install the notebooklm-py CLI (with browser automation support)
  4. Install the Chromium browser Playwright needs
  5. Check NotebookLM auth status and prompt for `notebooklm login` if needed

Flags:
  --verbose    Show full command output (debug mode)
  --quiet      Suppress progress output (use for CI)
  --dry-run    Run pre-flight and print the install plan, don't execute installs
  --help       Show this help

Safe to re-run: every step is idempotent.
EOF
      exit 0
      ;;
    *) die "Unknown flag: $arg. Use --verbose, --quiet, --dry-run, or --help." ;;
  esac
done

# ---- locate project root ----------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "${BOLD}Stillpoint setup${RESET}  —  $PROJECT_ROOT"
[[ $DRY_RUN -eq 1 ]] && echo "${YELLOW}(DRY RUN — no installs will execute)${RESET}"
[[ $QUIET -eq 1 ]] || echo

# ---- 0. Pre-flight checks ---------------------------------------------------
step "Pre-flight checks"

# Working directory: must be a Stillpoint checkout
if [[ ! -f "$PROJECT_ROOT/pyproject.toml" || ! -d "$PROJECT_ROOT/stillpoint" ]]; then
  die "Not a Stillpoint project root (missing pyproject.toml or stillpoint/). Run this from a Stillpoint checkout."
fi
ok "Project root verified"

# Python 3.11+ detection (with a clear install path in the error)
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)' 2>/dev/null; then
      PYTHON="$candidate"; break
    fi
  fi
done
if [[ -z "$PYTHON" ]]; then
  die "Python 3.11+ not found. Install from https://www.python.org/downloads/ or via your package manager (e.g. 'brew install python@3.12' on macOS)."
fi
ok "Using $("$PYTHON" --version 2>&1) ($(command -v "$PYTHON"))"

# Disk space check (~500MB needed for venv + pipx + Playwright)
NEEDED_MB=500
if command -v df >/dev/null 2>&1; then
  AVAILABLE_KB=$(df -Pk "$PROJECT_ROOT" | tail -1 | awk '{print $4}')
  AVAILABLE_MB=$((AVAILABLE_KB / 1024))
  if [[ $AVAILABLE_MB -lt $NEEDED_MB ]]; then
    die "Insufficient disk space: ${AVAILABLE_MB}MB available, ${NEEDED_MB}MB needed. Free up space and re-run."
  fi
  ok "Disk space: ${AVAILABLE_MB}MB available (${NEEDED_MB}MB needed)"
else
  warn "Could not check disk space (df not available)"
fi

# Internet connectivity check (required to download packages)
if ! curl -sSI --max-time 5 https://pypi.org >/dev/null 2>&1; then
  die "No internet connectivity to https://pypi.org. Setup needs to download Python packages. Check your network and re-run."
fi
ok "Internet connectivity verified (pypi.org reachable)"

# Write permissions on the project directory
if [[ ! -w "$PROJECT_ROOT" ]]; then
  die "No write permission on $PROJECT_ROOT. Run with appropriate permissions."
fi
ok "Write permission verified"

# Existing install check (re-runs are safe; flag so the user knows)
EXISTING=0
[[ -d "$PROJECT_ROOT/.venv" ]] && EXISTING=1
if command -v pipx >/dev/null 2>&1 && pipx list 2>/dev/null | grep -q 'notebooklm-py'; then
  EXISTING=1
fi
if [[ $EXISTING -eq 1 ]]; then
  warn "Existing Stillpoint install detected — re-running will be safe and may upgrade components"
else
  ok "No existing install detected"
fi

# ---- 1. Project virtualenv --------------------------------------------------
step "Creating project virtualenv (.venv)"
if [[ ! -d .venv ]]; then
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  ${BOLD}[DRY-RUN]${RESET} $PYTHON -m venv .venv"
  else
    "$PYTHON" -m venv .venv
    ok "Created .venv"
  fi
else
  ok ".venv already exists"
fi
VENV_PY=".venv/bin/python"

# Exit early in dry-run after printing the install plan
if [[ $DRY_RUN -eq 1 ]]; then
  step "Install plan (DRY RUN — nothing below this line will execute)"
  cat <<EOF
  ${BOLD}→${RESET} Upgrade pip in .venv
      $VENV_PY -m pip install --upgrade pip
  ${BOLD}→${RESET} Install project requirements (requirements.txt minus notebooklm)
      $VENV_PY -m pip install -r <filtered requirements>
  ${BOLD}→${RESET} Install project in editable mode
      $VENV_PY -m pip install -e . --no-deps
  ${BOLD}→${RESET} Bootstrap pipx (Apple Silicon → Intel Homebrew → PATH lookup → install)
  ${BOLD}→${RESET} Install notebooklm-py via pipx (with [browser] extra)
  ${BOLD}→${RESET} Install Chromium browser for Playwright (no-op on macOS, needs sudo on Linux)
  ${BOLD}→${RESET} Check NotebookLM auth status (one-time manual step: \`notebooklm login\`)
EOF
  echo
  echo "${BOLD}Dry run complete. Re-run without --dry-run to actually install.${RESET}"
  exit 0
fi

# ---- 1b. Install dependencies ------------------------------------------------
step "Installing dependencies (this can take a few minutes)..."
"$VENV_PY" -m pip install --upgrade pip
ok "pip upgraded"
# notebooklm is an external CLI installed via pipx below — not a pip dependency.
grep -vE '^[[:space:]]*#|^[[:space:]]*$|notebooklm' requirements.txt \
  | "$VENV_PY" -m pip install -r /dev/stdin
ok "Project requirements installed"
"$VENV_PY" -m pip install -e . --no-deps
ok "Stillpoint installed in editable mode"

# ---- 2. pipx ----------------------------------------------------------------
step "Checking pipx (for the NotebookLM CLI)"
PIPX=""
# Apple Silicon Homebrew (most common on M1/M2/M3/M4 Macs — /opt/homebrew is the default prefix)
if [[ -x "/opt/homebrew/bin/pipx" ]]; then
  PIPX="/opt/homebrew/bin/pipx"
  ok "Found pipx at $PIPX (Apple Silicon Homebrew)"
# Intel Homebrew / Linux x86_64 Homebrew prefix
elif [[ -x "/usr/local/bin/pipx" ]]; then
  PIPX="/usr/local/bin/pipx"
  ok "Found pipx at $PIPX (Intel Homebrew)"
# PATH lookup (catches Linux distro installs, pyenv, etc.)
elif command -v pipx >/dev/null 2>&1; then
  PIPX="pipx"
  ok "Found pipx on PATH: $(command -v pipx)"
else
  warn "pipx not found in common locations — installing it"
  "$PYTHON" -m pip install --user --quiet pipx
  "$PYTHON" -m pipx ensurepath >/dev/null 2>&1 || true
  # ensurepath updates shell rc files, not this session — add it manually here.
  export PATH="$HOME/.local/bin:$PATH"
  if command -v pipx >/dev/null 2>&1; then
    PIPX="pipx"
    ok "pipx installed"
  else
    die "pipx install failed. Install pipx manually: https://pypa.github.io/pipx/installation/"
  fi
fi
# Final fallback: invoke via `python -m pipx`
if ! command -v "$PIPX" >/dev/null 2>&1; then
  PIPX="$PYTHON -m pipx"
fi

# ---- 3. notebooklm-py CLI ---------------------------------------------------
step "Installing the NotebookLM CLI (notebooklm-py)"
if $PIPX list 2>/dev/null | grep -q 'notebooklm-py'; then
  $PIPX upgrade notebooklm-py >/dev/null 2>&1 || true
  ok "notebooklm-py already installed (upgraded if newer was available)"
else
  # [browser] extra pulls in Playwright, required for `notebooklm login`.
  $PIPX install "notebooklm-py[browser]"
  ok "notebooklm-py installed"
fi

# ---- 4. Playwright browser --------------------------------------------------
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

# ---- 5. NotebookLM authentication -------------------------------------------
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
echo "    ${BOLD}What was installed:${RESET}"
echo "      • Python project dependencies (in .venv/)"
echo "      • notebooklm-py CLI (via pipx)"
echo "      • Chromium browser (for NotebookLM auth)"
echo
echo "    ${BOLD}Next steps:${RESET}"
echo
if [[ ! -f "$NLM_STORAGE" ]]; then
  echo "      1. Authenticate NotebookLM:    ${BOLD}notebooklm login${RESET}"
  echo "      2. Activate the environment:   ${BOLD}source .venv/bin/activate${RESET}"
  echo "      3. Launch the app:             ${BOLD}python -m app.main${RESET}"
else
  echo "      1. Activate the environment:   ${BOLD}source .venv/bin/activate${RESET}"
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
