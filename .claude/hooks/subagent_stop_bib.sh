#!/bin/bash
set -e

if [ -x "$CLAUDE_PROJECT_DIR/.venv/bin/python" ]; then
  PYTHON="$CLAUDE_PROJECT_DIR/.venv/bin/python"
elif [ -x "$CLAUDE_PROJECT_DIR/.venv/Scripts/python" ]; then
  PYTHON="$CLAUDE_PROJECT_DIR/.venv/Scripts/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

if [ -z "$PYTHON" ]; then
  echo '{"decision":"allow"}'
  exit 0
fi

ERRORS=""
NOTES=""
while IFS= read -r bib; do
  [ -z "$bib" ] && continue
  result="$("$PYTHON" "$CLAUDE_PROJECT_DIR/.claude/hooks/bib_validator.py" "$bib" 2>/dev/null || true)"
  if echo "$result" | grep -q '"valid": false'; then
    ERRORS="$ERRORS"$'\n'"$bib: $result"
  fi

  bib_dir="$(dirname "$bib")"
  json_dir="$bib_dir/intermediate_files/json"
  if [ -d "$json_dir" ]; then
    clean="$("$PYTHON" "$CLAUDE_PROJECT_DIR/.claude/hooks/metadata_cleaner.py" "$bib" "$json_dir" 2>/dev/null || true)"
    if echo "$clean" | grep -q '"cleaned": true'; then
      NOTES="$NOTES"$'\n'"$bib cleaned: $clean"
    fi
    meta="$("$PYTHON" "$CLAUDE_PROJECT_DIR/.claude/hooks/metadata_validator.py" "$bib" "$json_dir" 2>/dev/null || true)"
    if echo "$meta" | grep -q '"valid": false'; then
      NOTES="$NOTES"$'\n'"$bib metadata warnings: $meta"
    fi
  fi
done < <(find "$CLAUDE_PROJECT_DIR/reviews" -type f -name "*.bib" 2>/dev/null || true)

if [ -n "$ERRORS" ]; then
  printf "%s" "$ERRORS" | "$PYTHON" -c 'import json,sys; print(json.dumps({"decision":"block","reason":sys.stdin.read().strip()}))'
  exit 0
fi

if [ -n "$NOTES" ]; then
  echo "metadata cleaning summary:$NOTES" >&2
fi

echo '{"decision":"allow"}'
