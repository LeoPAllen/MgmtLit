from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from mgmtlit.models import Paper


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
