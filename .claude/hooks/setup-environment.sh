#!/bin/bash
set -e

if [ -f "$CLAUDE_PROJECT_DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$CLAUDE_PROJECT_DIR/.venv/bin/activate"
  PYTHON="$CLAUDE_PROJECT_DIR/.venv/bin/python"
elif [ -f "$CLAUDE_PROJECT_DIR/.venv/Scripts/activate" ]; then
  # shellcheck disable=SC1091
  source "$CLAUDE_PROJECT_DIR/.venv/Scripts/activate"
  PYTHON="$CLAUDE_PROJECT_DIR/.venv/Scripts/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

if [ -n "$CLAUDE_ENV_FILE" ] && [ -n "$PYTHON" ]; then
  echo "export PYTHON=$PYTHON" >> "$CLAUDE_ENV_FILE"
fi

echo "MgmtLit hook environment ready"
