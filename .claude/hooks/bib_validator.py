#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LATEX_ESCAPE_PATTERN = re.compile(r"\\[\"'`^~][A-Za-z]|\\c\{[A-Za-z]\}|\\ss\b")

REQUIRED_FIELDS = {
    "article": {"author", "title", "year"},
    "book": {"title", "year"},
    "incollection": {"author", "title", "year"},
    "inproceedings": {"author", "title", "year"},
    "misc": {"title", "year"},
}


@dataclass(slots=True)
class BibEntry:
    entry_type: str
    key: str
    body: str


def split_entries(content: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    i = 0
    n = len(content)
    while i < n:
        at = content.find("@", i)
        if at == -1:
            break
        m = re.match(r"@([A-Za-z]+)\s*\{", content[at:])
        if not m:
            i = at + 1
            continue
        entry_type = m.group(1).lower()
        start = at + m.end()
        depth = 1
        j = start
        while j < n and depth > 0:
            ch = content[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1
        raw = content[start : j - 1]
        comma = raw.find(",")
        if comma == -1:
            i = j
            continue
        key = raw[:comma].strip()
        body = raw[comma + 1 :]
        if entry_type != "comment":
            entries.append(BibEntry(entry_type=entry_type, key=key, body=body))
        i = j
    return entries


def extract_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    field_pattern = re.compile(r"^\s*([A-Za-z][\w-]*)\s*=\s*(.+?),?\s*$")
    for line in body.splitlines():
        m = field_pattern.match(line)
        if not m:
            continue
        name = m.group(1).lower()
        value = m.group(2).strip().strip(",").strip()
        if value.startswith("{") and value.endswith("}"):
            value = value[1:-1].strip()
        elif value.startswith('"') and value.endswith('"'):
            value = value[1:-1].strip()
        fields[name] = value
    return fields


def check_duplicate_keys(entries: list[BibEntry]) -> list[str]:
    seen: set[str] = set()
    errors: list[str] = []
    for entry in entries:
        if entry.key in seen:
            errors.append(f"duplicate citation key: {entry.key}")
        seen.add(entry.key)
    return errors


def check_duplicate_fields(content: str) -> list[str]:
    errors: list[str] = []
    for entry in split_entries(content):
        seen: dict[str, int] = {}
        for idx, line in enumerate(entry.body.splitlines(), start=1):
            m = re.match(r"^\s*([A-Za-z][\w-]*)\s*=", line)
            if not m:
                continue
            name = m.group(1).lower()
            if name in seen:
                errors.append(
                    f"{entry.key}: duplicate field '{name}' (lines {seen[name]} and {idx})"
                )
            else:
                seen[name] = idx
    return errors


def check_required_fields(path: str) -> list[str]:
    content = Path(path).read_text(encoding="utf-8")
    errors: list[str] = []
    for entry in split_entries(content):
        required = REQUIRED_FIELDS.get(entry.entry_type)
        if not required:
            continue
        fields = extract_fields(entry.body)
        missing = sorted(required.difference(fields))
        if missing:
            errors.append(f"{entry.key}: missing required fields: {', '.join(missing)}")
    return errors


def check_latex_escapes(path: str, content: str) -> list[str]:
    if not LATEX_ESCAPE_PATTERN.search(content):
        return []
    return [f"{path}: contains LaTeX escape sequences; use UTF-8 characters directly"]


def check_bibtex_syntax(path: str) -> list[str]:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"{path}: invalid UTF-8: {exc}"]
    entries = split_entries(content)
    if not entries and "@" in content:
        return [f"{path}: failed to parse BibTeX entries"]
    return []


def validate_file(path: str) -> dict[str, object]:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return {"valid": False, "errors": [f"invalid UTF-8: {exc}"]}
    except FileNotFoundError:
        return {"valid": False, "errors": [f"file not found: {path}"]}

    entries = split_entries(content)
    errors: list[str] = []
    errors.extend(check_duplicate_keys(entries))
    errors.extend(check_duplicate_fields(content))
    errors.extend(check_latex_escapes(path, content))
    errors.extend(check_bibtex_syntax(path))
    errors.extend(check_required_fields(path))
    return {"valid": not errors, "errors": errors}


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"valid": False, "errors": ["usage: bib_validator.py <bib_file>"]}))
        return 2
    result = validate_file(sys.argv[1])
    print(json.dumps(result))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
