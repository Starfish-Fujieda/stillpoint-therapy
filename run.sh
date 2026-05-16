#!/usr/bin/env bash
# Launch Stillpoint. Run this after scripts/setup.sh.
exec "$(dirname "$0")/.venv/bin/python" -m app.main "$@"
