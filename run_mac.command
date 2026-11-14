#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10 or later is required. Install Python from https://www.python.org/downloads/"
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "Python 3.10 or later is required."
  exit 1
fi

# Create a project-local environment only when one does not already exist.
# Never reuse a virtual environment from a different project directory.
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi
PYTHON_BIN="$(pwd)/.venv/bin/python"

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "The existing .venv uses an unsupported Python version. Remove this project's .venv and rerun."
  exit 1
fi

"$PYTHON_BIN" -m pip install --disable-pip-version-check -r requirements.txt
"$PYTHON_BIN" -m pip check
exec "$PYTHON_BIN" -m streamlit run app.py
