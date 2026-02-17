#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

HOOKS_DIR = Path(__file__).parent
sys.path.insert(0, str(HOOKS_DIR))

from bib_validator import (  # noqa: E402
    check_bibtex_syntax,
    check_duplicate_fields,
    check_latex_escapes,
    check_required_fields,
)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"hookSpecificOutput": {}}))
        return 0

    if payload.get("tool_name") != "Write":
        print(json.dumps({"hookSpecificOutput": {}}))
        return 0

    tool_input = payload.get("tool_input", {})
    file_path = str(tool_input.get("file_path", ""))
    content = str(tool_input.get("content", ""))
    if not file_path.endswith(".bib") or not content:
        print(json.dumps({"hookSpecificOutput": {}}))
        return 0

    errors = []
    errors.extend(check_duplicate_fields(content))
    errors.extend(check_latex_escapes(file_path, content))

    with tempfile.NamedTemporaryFile(mode="w", suffix=".bib", encoding="utf-8", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        errors.extend(check_bibtex_syntax(str(tmp_path)))
        errors.extend(check_required_fields(str(tmp_path)))
    finally:
        tmp_path.unlink(missing_ok=True)

    if errors:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "permissionDecision": "deny",
                        "denyReason": "BibTeX validation failed:\n- " + "\n- ".join(errors),
                    }
                }
            )
        )
        return 0

    print(json.dumps({"hookSpecificOutput": {}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
