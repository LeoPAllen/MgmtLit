from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from mgmtlit.models import Paper, QueryPlan


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:80] or "review"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def dedupe_papers(papers: Iterable[Paper]) -> list[Paper]:
    winners: dict[str, Paper] = {}
    for paper in papers:
        key = paper.canonical_key()
        prev = winners.get(key)
        if prev is None:
            winners[key] = paper
            continue

        prev_score = (prev.citation_count or 0, len(prev.abstract or ""))
        now_score = (paper.citation_count or 0, len(paper.abstract or ""))
        if now_score > prev_score:
            winners[key] = paper
    return list(winners.values())


def render_evidence_table(papers: list[Paper], limit: int = 30) -> str:
    rows = [
        "| # | Year | Paper | Evidence Summary |",
        "|---|---:|---|---|",
    ]
    for idx, paper in enumerate(papers[:limit], 1):
        summary = (paper.abstract or "No abstract available.").replace("\n", " ").strip()
        summary = summary[:220] + ("..." if len(summary) > 220 else "")
        year = str(paper.year) if paper.year else "-"
        title = paper.title.replace("|", "\\|")
        rows.append(f"| {idx} | {year} | {title} | {summary} |")
    return "\n".join(rows) + "\n"


def _bibtex_key(paper: Paper, existing: dict[str, int]) -> str:
    surname = "anon"
    if paper.authors:
        parts = paper.authors[0].split()
        if parts:
            surname = re.sub(r"[^a-zA-Z0-9]", "", parts[-1].lower()) or "anon"
    year = str(paper.year) if paper.year else "nd"
    base = f"{surname}{year}"
    count = existing[base]
    existing[base] += 1
    if count == 0:
        return base
    return f"{base}{count + 1}"


def render_bibtex(papers: list[Paper]) -> str:
    keys: dict[str, int] = defaultdict(int)
    chunks: list[str] = []
    for paper in papers:
        key = _bibtex_key(paper, keys)
        author = " and ".join(paper.authors) if paper.authors else "Unknown"
        fields = {
            "title": paper.title,
            "author": author,
            "year": str(paper.year) if paper.year else "",
            "journal": paper.venue or "",
            "doi": paper.doi or "",
            "url": paper.url or "",
        }
        lines = [f"@article{{{key},"]
        for name, value in fields.items():
            if value:
                safe = value.replace("{", "").replace("}", "")
                lines.append(f"  {name} = {{{safe}}},")
        lines.append("}")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks) + ("\n" if chunks else "")


def render_task_progress(
    *,
    topic: str,
    phases: list[str],
    completed: list[str],
    current: str,
    note: str,
) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    checks = []
    completed_set = set(completed)
    for phase in phases:
        marker = "x" if phase in completed_set else " "
        checks.append(f"- [{marker}] {phase}")
    lines = [
        "# Literature Review Progress Tracker",
        "",
        f"**Research Topic**: {topic}",
        f"**Last Updated**: {now}",
        "",
        "## Progress Status",
        "",
        *checks,
        "",
        "## Current Task",
        "",
        current,
        "",
        "## Latest Note",
        "",
        note,
        "",
    ]
    return "\n".join(lines)


def render_lit_review_plan_md(plan: QueryPlan, domains: list[object]) -> str:
    lines = [
        f"# Literature Review Plan: {plan.topic}",
        "",
        "## Research Idea Summary",
        "",
        plan.description or plan.topic,
        "",
        "## Key Research Questions",
        "",
    ]
    for i, q in enumerate(plan.subquestions, start=1):
        lines.append(f"{i}. {q}")
    lines.extend(["", "## Literature Review Domains", ""])
    for domain in domains:
        index = getattr(domain, "index", "?")
        name = str(getattr(domain, "name", "Domain"))
        focus = str(getattr(domain, "focus", ""))
        key_questions = list(getattr(domain, "key_questions", []))
        search_terms = list(getattr(domain, "search_terms", []))
        lines.extend(
            [
                f"### Domain {index}: {name}",
                "",
                f"**Focus**: {focus}",
                "",
                "**Key Questions**:",
            ]
        )
        for q in key_questions:
            lines.append(f"- {q}")
        lines.extend(["", "**Search Terms**:"])
        for term in search_terms:
            lines.append(f"- {term}")
        lines.extend(["", "---", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_synthesis_outline_md(topic: str, outline: object) -> str:
    lines = [
        "# Literature Review Outline",
        "",
        f"**Research Project**: {topic}",
        f"**Date**: {getattr(outline, 'created_on', '')}",
        f"**Total Literature Base**: {getattr(outline, 'total_papers', 0)} papers",
        "",
        "---",
        "",
    ]
    sections = getattr(outline, "sections", [])
    for section in sections:
        lines.extend(
            [
                section.heading,
                "",
                f"**Purpose**: {section.purpose}",
                "",
                f"**Word Target**: {section.word_target}",
                "",
            ]
        )
        mapped = getattr(section, "domain_indices", [])
        if mapped:
            lines.append("**Domain Mapping**: " + ", ".join(str(i) for i in mapped))
            lines.append("")
        lines.extend(["---", ""])
    lines.extend(["## Notes for Synthesis Writer", "", str(getattr(outline, "notes_for_writers", "")), ""])
    return "\n".join(lines)


def with_yaml_frontmatter(content: str, *, title: str) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    front = "\n".join(["---", f"title: {title}", f"date: {today}", "---", ""])
    return front + content.strip() + "\n"


def render_references_markdown(papers: list[Paper]) -> str:
    lines = ["## References", ""]
    for paper in papers:
        author = "; ".join(paper.authors[:3]) if paper.authors else "Unknown"
        year = str(paper.year) if paper.year else "n.d."
        venue = f" {paper.venue}." if paper.venue else ""
        doi_or_url = f" https://doi.org/{paper.doi}" if paper.doi else (f" {paper.url}" if paper.url else "")
        lines.append(f"- {author} ({year}). {paper.title}.{venue}{doi_or_url}".strip())
    lines.append("")
    return "\n".join(lines)
