from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AgentSpec:
    name: str
    description: str
    tools: tuple[str, ...]
    model: str
    prompt: str


AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec(
        name="literature-review-planner",
        description=(
            "Decomposes management research questions into domains, key questions, "
            "and evidence-oriented search strategies."
        ),
        tools=("Read", "Write"),
        model="reasoning",
        prompt="""# Literature Review Planner

You are a planning specialist. Build a concrete domain decomposition for management research.

## Inputs
- Topic and optional scope description
- Output path for `lit-review-plan.md`

## Output requirements
- 3-8 domains, each with:
  - focus
  - key questions
  - search terms
  - expected evidence type (theory, empirical, methods, critique)
- include critical/counter-position coverage, not only confirmatory sources
- include recency strategy (last 5 years + foundational works)

Stop after writing the plan file.
""",
    ),
    AgentSpec(
        name="domain-literature-researcher",
        description=(
            "Runs domain-scoped evidence retrieval and produces valid BibTeX with "
            "metadata-rich annotations."
        ),
        tools=("Read", "Write", "Bash", "Glob", "Grep"),
        model="balanced",
        prompt="""# Domain Literature Researcher

You are a retrieval and curation specialist working in isolated context for one domain.

## Inputs
- domain focus + key questions
- exact output path for `literature-domain-N.bib`
- working directory for JSON evidence snapshots

## Rules
- never fabricate papers, DOI, venue, or years
- if metadata is missing, omit that field instead of guessing
- every entry must include a substantive `note` with:
  - core argument
  - relevance to the project
  - position in the debate
- prioritize management, organizations, and IS evidence

## Deliverables
- valid BibTeX file at requested output path
- source JSON artifacts in `intermediate_files/json/` when available

Stop after writing your domain bibliography file.
""",
    ),
    AgentSpec(
        name="synthesis-planner",
        description=(
            "Designs a tight synthesis outline from domain BibTeX files with section "
            "targets and citation allocation."
        ),
        tools=("Read", "Write", "Glob", "Grep"),
        model="reasoning",
        prompt="""# Synthesis Planner

You architect the literature review narrative from domain bibliographies.

## Inputs
- plan file
- all `literature-domain-*.bib` files
- output path for `synthesis-outline.md`

## Output requirements
- 3-6 sections organized by insight/tension (not by source list)
- explicit word targets per section
- papers grouped by section with high-priority anchors
- identify unresolved contradictions and methods gaps

Target a focused review arc suitable for a publishable management paper draft.
Stop after writing the synthesis outline.
""",
    ),
    AgentSpec(
        name="synthesis-writer",
        description=(
            "Writes section-level synthesis drafts from outline and BibTeX data using "
            "analytical, citation-grounded prose."
        ),
        tools=("Read", "Write", "Glob", "Grep"),
        model="balanced",
        prompt="""# Synthesis Writer

You write one assigned review section at a time.

## Inputs
- exact section heading to write
- outline path
- relevant domain bib files
- exact output path `synthesis-section-N.md`

## Writing constraints
- use only sources present in provided BibTeX files
- do not perform new paper discovery in synthesis phase
- analytical, evidence-based prose; avoid generic claims
- connect each subsection to the focal research question

Stop after writing the assigned section file.
""",
    ),
)


ARCHITECTURE_MD = """# Agentic Architecture (Cross-Provider)

MgmtLit follows a PhilLit-style staged workflow with specialized roles and explicit artifacts.

## Workflow
1. planner -> `lit-review-plan.md`
2. domain researchers (parallel) -> `literature-domain-*.bib`
3. synthesis planner -> `synthesis-outline.md`
4. synthesis writers (parallel) -> `synthesis-section-*.md`
5. assembler -> `literature-review-final.md` + `literature-all.bib`

## Design pattern
- Multi-file-then-assemble
- Isolated worker contexts
- Explicit intermediate artifacts for resumability and auditability
- Deterministic file contracts between stages

## Provider parity strategy
Canonical prompts live in this repo and are rendered for:
- Claude Code: `.claude/agents/*.md`
- OpenAI/Codex-style workflows: `.openai/agents/*.md` + `.openai/AGENTS.md`
- Gemini workflows: `.gemini/agents/*.md` + `.gemini/GEMINI.md`
"""


CONVENTIONS_MD = """# Agent Conventions

## Bibliographic integrity
- Never invent references or metadata.
- Omit unknown fields instead of guessing.
- Keep UTF-8 encoding.

## Annotation quality
Every BibTeX entry should include a substantive `note`:
- core argument
- relevance to research question
- position/tension in debate

## File contracts
- planner: `intermediate_files/lit-review-plan.md`
- domain researcher: `intermediate_files/literature-domain-N.bib`
- synthesis planner: `intermediate_files/synthesis-outline.md`
- synthesis writer: `intermediate_files/synthesis-section-N.md`
"""


OPENAI_RUNBOOK = """# OpenAI Agent Runbook

Use this file as the top-level policy prompt when running MgmtLit in OpenAI/Codex environments.

## Orchestration order
1. `literature-review-planner`
2. `domain-literature-researcher` (parallel by domain)
3. `synthesis-planner`
4. `synthesis-writer` (parallel by section)

Load agent prompts from `.openai/agents/`.
Honor file contracts from `agentic/conventions.md`.
"""


GEMINI_RUNBOOK = """# Gemini Agent Runbook

Use this file as the top-level workflow prompt for Gemini-based runs.

## Orchestration order
1. `literature-review-planner`
2. `domain-literature-researcher` in parallel
3. `synthesis-planner`
4. `synthesis-writer` in parallel

Agent prompts live in `.gemini/agents/`.
File contracts and formatting rules are defined in `agentic/conventions.md`.
"""

CLAUDE_SKILL_LIT_REVIEW = """---
name: literature-review
description: Orchestrates the full literature review workflow using specialized agents.
---

# Literature Review Skill

Use this as the top-level orchestrator in main context.

## Workflow
1. Run `literature-review-planner` and write `intermediate_files/lit-review-plan.md`
2. Run `domain-literature-researcher` in parallel for all domains to produce `literature-domain-*.bib`
3. Run `synthesis-planner` and write `intermediate_files/synthesis-outline.md`
4. Run `synthesis-writer` in parallel by section to produce `synthesis-section-*.md`
5. Assemble final outputs with `mgmtlit assemble` and `mgmtlit dedupe-bib`

Track progress in `intermediate_files/task-progress.md`.
"""

CLAUDE_SKILL_MGMT_RESEARCH = """---
name: management-research
description: Structured retrieval and verification utilities for management literature.
---

# Management Research Skill

Prefer structured API calls over free-form web search.

## Script Equivalents (via CLI)
- `mgmtlit search-openalex "query" --out results.json`
- `mgmtlit search-s2 "query" --out results.json`
- `mgmtlit search-crossref "query" --out results.json`
- `mgmtlit verify-paper --doi 10.xxxx/xxxx --out verify.json`
- `mgmtlit s2-citations PAPER_ID --mode both --out citations.json`
- `mgmtlit s2-recommend PAPER_ID_1 PAPER_ID_2 --out recommend.json`
- `mgmtlit enrich-bibliography reviews/project/intermediate_files/literature-domain-1.bib`

## Rules
- Never fabricate metadata.
- Save evidence JSON under `intermediate_files/json/`.
- Prefer DOI-backed metadata when available.
"""

HOOK_SETUP_ENV_SH = """#!/bin/bash
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
"""

HOOK_BIB_VALIDATOR_PY = """#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LATEX_ESCAPE_PATTERN = re.compile(r"\\\\[\\\"'`^~][A-Za-z]|\\\\c\\{[A-Za-z]\\}|\\\\ss\\b")

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
        m = re.match(r"@([A-Za-z]+)\\s*\\{", content[at:])
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
    field_pattern = re.compile(r"^\\s*([A-Za-z][\\w-]*)\\s*=\\s*(.+?),?\\s*$")
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
            m = re.match(r"^\\s*([A-Za-z][\\w-]*)\\s*=", line)
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
"""

HOOK_METADATA_VALIDATOR_PY = """#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

from bib_validator import extract_fields, split_entries

VALIDATED_FIELDS = {"journal", "booktitle", "volume", "number", "pages", "publisher", "year", "doi"}


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def normalize_doi(value: str) -> str:
    doi = normalize_text(value)
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "doi.org/"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi


def normalize_pages(value: str) -> str:
    return re.sub(r"\\s*[-–—]+\\s*", "-", value.strip())


def load_json_index(json_dir: Path) -> dict[str, set[str]]:
    index = {
        "journal": set(),
        "booktitle": set(),
        "volume": set(),
        "number": set(),
        "pages": set(),
        "publisher": set(),
        "year": set(),
        "doi": set(),
    }

    def ingest_dict(obj: dict[str, Any]) -> None:
        for key in ("journal", "booktitle", "container_title", "venue"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                index["journal"].add(normalize_text(val))
        source = obj.get("source")
        if isinstance(source, dict):
            source_name = source.get("name")
            if isinstance(source_name, str) and source_name.strip():
                index["journal"].add(normalize_text(source_name))
        volume = obj.get("volume")
        if volume is not None:
            index["volume"].add(str(volume).strip())
        issue = obj.get("issue", obj.get("number"))
        if issue is not None:
            index["number"].add(str(issue).strip())
        pages = obj.get("pages", obj.get("page"))
        if isinstance(pages, str) and pages.strip():
            index["pages"].add(normalize_pages(pages))
        publisher = obj.get("publisher")
        if isinstance(publisher, str) and publisher.strip():
            index["publisher"].add(normalize_text(publisher))
        year = obj.get("year", obj.get("publication_year"))
        if year is not None:
            index["year"].add(str(year).strip())
        doi = obj.get("doi")
        if isinstance(doi, str) and doi.strip():
            index["doi"].add(normalize_doi(doi))

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            ingest_dict(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for file in sorted(json_dir.glob("*.json")):
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            continue
        walk(payload)
    index["booktitle"] = set(index["journal"])
    return index


def validate_bib_file(bib_file: Path, json_dir: Path) -> dict[str, object]:
    try:
        content = bib_file.read_text(encoding="utf-8")
    except Exception as exc:
        return {"valid": False, "errors": [f"cannot read {bib_file}: {exc}"]}

    index = load_json_index(json_dir)
    errors: list[str] = []
    for entry in split_entries(content):
        fields = extract_fields(entry.body)
        for field, raw_value in fields.items():
            if field not in VALIDATED_FIELDS:
                continue
            if not raw_value:
                continue
            value = raw_value.strip()
            match field:
                case "journal" | "booktitle":
                    ok = normalize_text(value) in index["journal"]
                case "volume":
                    ok = value in index["volume"]
                case "number":
                    ok = value in index["number"]
                case "pages":
                    ok = normalize_pages(value) in index["pages"]
                case "publisher":
                    ok = normalize_text(value) in index["publisher"]
                case "year":
                    ok = value in index["year"]
                case "doi":
                    ok = normalize_doi(value) in index["doi"]
                case _:
                    ok = True
            if not ok:
                errors.append(f"{entry.key}: field '{field}' not found in JSON evidence")
    return {"valid": not errors, "errors": errors}


def main() -> int:
    if len(sys.argv) != 3:
        print(
            json.dumps(
                {"valid": False, "errors": ["usage: metadata_validator.py <bib_file> <json_dir>"]}
            )
        )
        return 2
    result = validate_bib_file(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
"""

HOOK_METADATA_CLEANER_PY = """#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from bib_validator import extract_fields, split_entries
from metadata_validator import (
    VALIDATED_FIELDS,
    load_json_index,
    normalize_doi,
    normalize_pages,
    normalize_text,
)


def _is_verified(field: str, value: str, index: dict[str, set[str]]) -> bool:
    if field in {"journal", "booktitle"}:
        return normalize_text(value) in index["journal"]
    if field == "volume":
        return value in index["volume"]
    if field == "number":
        return value in index["number"]
    if field == "pages":
        return normalize_pages(value) in index["pages"]
    if field == "publisher":
        return normalize_text(value) in index["publisher"]
    if field == "year":
        return value in index["year"]
    if field == "doi":
        return normalize_doi(value) in index["doi"]
    return True


def _render_field(name: str, value: str) -> str:
    return f"  {name} = {{{value}}},"


def clean_bib_file(bib_file: Path, json_dir: Path) -> dict[str, Any]:
    content = bib_file.read_text(encoding="utf-8")
    index = load_json_index(json_dir)

    cleaned_entries: list[str] = []
    removed_by_key: dict[str, list[str]] = {}
    output: list[str] = []
    for entry in split_entries(content):
        fields = extract_fields(entry.body)
        kept: dict[str, str] = {}
        removed: list[str] = []
        for name, value in fields.items():
            value = value.strip()
            if name not in VALIDATED_FIELDS:
                kept[name] = value
                continue
            if _is_verified(name, value, index):
                kept[name] = value
            else:
                removed.append(name)

        entry_type = entry.entry_type
        if entry_type in {"article", "incollection", "inproceedings", "book"}:
            required = {
                "article": ["journal"],
                "incollection": ["booktitle"],
                "inproceedings": ["booktitle"],
                "book": ["publisher"],
            }[entry_type]
            if any(req not in kept for req in required):
                entry_type = "misc"
                kept.pop("journal", None)
                kept.pop("booktitle", None)
                kept.pop("publisher", None)
                if "howpublished" not in kept and "url" not in kept:
                    kept["howpublished"] = "Metadata-cleaned source"
                if "type_downgrade" not in removed:
                    removed.append("type_downgrade")

        if removed:
            keywords = kept.get("keywords", "")
            if "METADATA_CLEANED" not in keywords:
                kept["keywords"] = (keywords + ", METADATA_CLEANED").strip(", ").strip()
            cleaned_entries.append(entry.key)
            removed_by_key[entry.key] = removed

        preferred_order = [
            "author",
            "title",
            "journal",
            "booktitle",
            "publisher",
            "year",
            "volume",
            "number",
            "pages",
            "doi",
            "url",
            "howpublished",
            "abstract",
            "keywords",
            "note",
        ]
        ordered = [k for k in preferred_order if k in kept] + [k for k in kept if k not in preferred_order]
        output.append(f"@{entry_type}{{{entry.key},")
        output.extend(_render_field(name, kept[name]) for name in ordered)
        output.append("}")
        output.append("")

    if cleaned_entries:
        bib_file.write_text("\\n".join(output).strip() + "\\n", encoding="utf-8")
    return {
        "cleaned": bool(cleaned_entries),
        "entries_cleaned": len(cleaned_entries),
        "total_fields_removed": sum(len(v) for v in removed_by_key.values()),
        "cleaned_entries": removed_by_key,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            json.dumps(
                {"cleaned": False, "error": "usage: metadata_cleaner.py <bib_file> <json_dir>"}
            )
        )
        return 2
    try:
        result = clean_bib_file(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as exc:
        print(json.dumps({"cleaned": False, "error": str(exc)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""

HOOK_VALIDATE_BIB_WRITE_PY = """#!/usr/bin/env python3
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
                        "denyReason": "BibTeX validation failed:\\n- " + "\\n- ".join(errors),
                    }
                }
            )
        )
        return 0

    print(json.dumps({"hookSpecificOutput": {}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""

HOOK_SUBAGENT_STOP_SH = """#!/bin/bash
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
    ERRORS="$ERRORS"$'\\n'"$bib: $result"
  fi

  bib_dir="$(dirname "$bib")"
  json_dir="$bib_dir/intermediate_files/json"
  if [ -d "$json_dir" ]; then
    clean="$("$PYTHON" "$CLAUDE_PROJECT_DIR/.claude/hooks/metadata_cleaner.py" "$bib" "$json_dir" 2>/dev/null || true)"
    if echo "$clean" | grep -q '"cleaned": true'; then
      NOTES="$NOTES"$'\\n'"$bib cleaned: $clean"
    fi
    meta="$("$PYTHON" "$CLAUDE_PROJECT_DIR/.claude/hooks/metadata_validator.py" "$bib" "$json_dir" 2>/dev/null || true)"
    if echo "$meta" | grep -q '"valid": false'; then
      NOTES="$NOTES"$'\\n'"$bib metadata warnings: $meta"
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
"""


def _claude_agent_doc(spec: AgentSpec) -> str:
    tools = ", ".join(spec.tools)
    return (
        "---\n"
        f"name: {spec.name}\n"
        f"description: {spec.description}\n"
        f"tools: {tools}\n"
        f"model: {spec.model}\n"
        "permissionMode: default\n"
        "---\n\n"
        f"{spec.prompt.strip()}\n"
    )


def _portable_agent_doc(spec: AgentSpec, provider: str) -> str:
    tools = ", ".join(spec.tools)
    return (
        f"# Agent: {spec.name}\n\n"
        f"Provider: {provider}\n\n"
        f"Description: {spec.description}\n\n"
        f"Suggested tools: {tools}\n\n"
        f"{spec.prompt.strip()}\n"
    )


def _claude_settings() -> dict[str, object]:
    return {
        "permissions": {
            "defaultMode": "default",
            "deny": ["Bash(sudo *)", "Bash(dd *)", "Bash(mkfs *)"],
            "allow": [
                "Read",
                "Write(reviews/**)",
                "Edit(reviews/**)",
                "Glob",
                "Grep",
                "WebSearch",
                "WebFetch",
                "Bash(ls *)",
                "Bash(cat *)",
                "Bash(python *)",
                "Bash(python3 *)",
                "Bash(pytest *)",
                "Bash(find *)",
                "Bash(mkdir *)",
                "Skill(literature-review)",
                "Skill(management-research)",
            ],
            "ask": ["Bash(rm *)", "Bash(rmdir *)"],
        },
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/setup-environment.sh",
                        }
                    ]
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "\"$CLAUDE_PROJECT_DIR\"/.venv/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/validate_bib_write.py 2>/dev/null || python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/validate_bib_write.py 2>/dev/null || echo '{\"hookSpecificOutput\": {}}'",
                        }
                    ],
                }
            ],
            "SubagentStop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/subagent_stop_bib.sh",
                        }
                    ]
                }
            ],
        },
    }


def scaffold_agent_pack(root: Path, overwrite: bool = True) -> list[Path]:
    written: list[Path] = []
    root = root.resolve()

    targets = [
        root / "agentic" / "ARCHITECTURE.md",
        root / "agentic" / "conventions.md",
        root / ".openai" / "AGENTS.md",
        root / ".gemini" / "GEMINI.md",
        root / ".claude" / "docs" / "ARCHITECTURE.md",
        root / ".claude" / "docs" / "conventions.md",
        root / ".claude" / "skills" / "literature-review" / "SKILL.md",
        root / ".claude" / "skills" / "management-research" / "SKILL.md",
        root / ".claude" / "settings.json",
        root / ".claude" / "hooks" / "setup-environment.sh",
        root / ".claude" / "hooks" / "bib_validator.py",
        root / ".claude" / "hooks" / "metadata_validator.py",
        root / ".claude" / "hooks" / "metadata_cleaner.py",
        root / ".claude" / "hooks" / "validate_bib_write.py",
        root / ".claude" / "hooks" / "subagent_stop_bib.sh",
        root / "agentic" / "manifest.json",
    ]
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)

    _write_file(root / "agentic" / "ARCHITECTURE.md", ARCHITECTURE_MD, overwrite, written)
    _write_file(root / "agentic" / "conventions.md", CONVENTIONS_MD, overwrite, written)
    _write_file(root / ".openai" / "AGENTS.md", OPENAI_RUNBOOK, overwrite, written)
    _write_file(root / ".gemini" / "GEMINI.md", GEMINI_RUNBOOK, overwrite, written)
    _write_file(root / ".claude" / "docs" / "ARCHITECTURE.md", ARCHITECTURE_MD, overwrite, written)
    _write_file(root / ".claude" / "docs" / "conventions.md", CONVENTIONS_MD, overwrite, written)
    _write_file(
        root / ".claude" / "skills" / "literature-review" / "SKILL.md",
        CLAUDE_SKILL_LIT_REVIEW,
        overwrite,
        written,
    )
    _write_file(
        root / ".claude" / "skills" / "management-research" / "SKILL.md",
        CLAUDE_SKILL_MGMT_RESEARCH,
        overwrite,
        written,
    )
    _write_file(root / ".claude" / "hooks" / "setup-environment.sh", HOOK_SETUP_ENV_SH, overwrite, written)
    _write_file(root / ".claude" / "hooks" / "bib_validator.py", HOOK_BIB_VALIDATOR_PY, overwrite, written)
    _write_file(
        root / ".claude" / "hooks" / "metadata_validator.py", HOOK_METADATA_VALIDATOR_PY, overwrite, written
    )
    _write_file(
        root / ".claude" / "hooks" / "metadata_cleaner.py", HOOK_METADATA_CLEANER_PY, overwrite, written
    )
    _write_file(
        root / ".claude" / "hooks" / "validate_bib_write.py", HOOK_VALIDATE_BIB_WRITE_PY, overwrite, written
    )
    _write_file(root / ".claude" / "hooks" / "subagent_stop_bib.sh", HOOK_SUBAGENT_STOP_SH, overwrite, written)
    _write_json(root / ".claude" / "settings.json", _claude_settings(), overwrite, written)
    _write_json(
        root / "agentic" / "manifest.json",
        {
            "version": 1,
            "agents": [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "tools": list(spec.tools),
                    "model": spec.model,
                }
                for spec in AGENT_SPECS
            ],
        },
        overwrite,
        written,
    )

    for spec in AGENT_SPECS:
        _write_file(
            root / ".claude" / "agents" / f"{spec.name}.md",
            _claude_agent_doc(spec),
            overwrite,
            written,
        )
        _write_file(
            root / ".openai" / "agents" / f"{spec.name}.md",
            _portable_agent_doc(spec, "openai"),
            overwrite,
            written,
        )
        _write_file(
            root / ".gemini" / "agents" / f"{spec.name}.md",
            _portable_agent_doc(spec, "gemini"),
            overwrite,
            written,
        )
    return written


def _write_file(path: Path, content: str, overwrite: bool, written: list[Path]) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    if path.suffix == ".sh":
        path.chmod(0o755)
    written.append(path)


def _write_json(path: Path, payload: object, overwrite: bool, written: list[Path]) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    written.append(path)
