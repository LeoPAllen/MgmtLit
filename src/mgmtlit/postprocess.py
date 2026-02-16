from __future__ import annotations

import re
import unicodedata
from datetime import date
from pathlib import Path


def natural_sort_key(path: Path) -> tuple[str | int, ...]:
    parts = re.split(r"(\d+)", path.name)
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)


def strip_section_frontmatter(content: str) -> str:
    if not content.startswith("---\n"):
        return content
    match = re.search(r"\n---\n|\n---$", content[4:])
    if not match:
        return content
    end_pos = 4 + match.end()
    return content[end_pos:].lstrip("\n")


def assemble_review(
    output_file: Path,
    section_files: list[Path],
    *,
    title: str,
    review_date: str | None = None,
) -> dict[str, object]:
    if not section_files:
        raise ValueError("No section files provided")
    review_date = review_date or date.today().isoformat()

    parts: list[str] = [
        "---",
        f"title: {title}",
        f"date: {review_date}",
        "---",
        "",
    ]
    stats: dict[str, object] = {"sections": [], "warnings": [], "total_bytes": 0}
    for path in sorted(section_files, key=natural_sort_key):
        if not path.exists():
            raise FileNotFoundError(f"Section file not found: {path}")
        content = strip_section_frontmatter(path.read_text(encoding="utf-8")).strip()
        if not content:
            cast_list(stats["warnings"]).append(f"Empty section: {path.name}")
            continue
        cast_list(stats["sections"]).append(path.name)
        stats["total_bytes"] = int(stats["total_bytes"]) + len(content.encode("utf-8"))
        parts.append(content)
        parts.append("")

    while parts and not parts[-1].strip():
        parts.pop()
    output_file.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return stats


def dedupe_bib(input_files: list[Path], output_file: Path) -> list[str]:
    seen: dict[str, str] = {}
    by_doi: dict[str, str] = {}
    comments: list[str] = []
    duplicates: list[str] = []

    for bib_file in input_files:
        content = bib_file.read_text(encoding="utf-8")
        entries = re.split(r"\n(?=@)", content)
        for entry in entries:
            text = entry.strip()
            if not text:
                continue
            if text.lower().startswith("@comment"):
                comments.append(text)
                continue
            m = re.match(r"@(\w+)\{([^,]+),", text, re.IGNORECASE)
            if not m:
                continue
            key = m.group(2).strip()
            doi = _extract_doi(text)

            if key in seen:
                duplicates.append(key)
                seen[key] = _merge_entry(seen[key], text)
                continue

            if doi and doi in by_doi:
                winner_key = by_doi[doi]
                duplicates.append(key)
                seen[winner_key] = _merge_entry(seen[winner_key], text)
                continue

            seen[key] = text
            if doi:
                by_doi[doi] = key

    chunks = [c.rstrip() for c in comments]
    chunks.extend(v.rstrip() for v in seen.values())
    output_file.write_text("\n\n".join(chunks).strip() + ("\n" if chunks else ""), encoding="utf-8")
    return duplicates


INTRO_PATTERNS = {"introduction", "preamble", "overview", "background"}
CONCLUSION_PATTERNS = {"conclusion", "summary", "closing remarks", "final remarks", "concluding remarks"}
EXCLUDED_HEADINGS = {"references", "bibliography"}

RE_SECTION_PREFIX = re.compile(r"^(?:Section\s+\d{1,2}\s*:\s*)(.*)", re.IGNORECASE)
RE_SUBSECTION_PREFIX = re.compile(r"^(?:Subsection\s+)?\d{1,2}\.\d{1,2}\s*:?\s*(.*)", re.IGNORECASE)


def normalize_headings(content: str) -> tuple[str, list[str]]:
    lines = content.split("\n")
    changes: list[str] = []
    frontmatter_end = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                frontmatter_end = i + 1
                break

    section_lines: list[int] = []
    for i, line in enumerate(lines):
        if i < frontmatter_end:
            continue
        if line.startswith("## ") and not line.startswith("### "):
            section_lines.append(i)

    if not section_lines:
        return content, changes

    body_count = 0
    replacements: dict[int, str] = {}
    for pos, i in enumerate(section_lines):
        raw = lines[i]
        title = _normalize_em_dash(_strip_section_prefix(raw[3:].strip()))
        kind = "body"
        lower = title.lower().strip()
        if lower in EXCLUDED_HEADINGS:
            kind = "excluded"
        elif pos == 0 and lower in INTRO_PATTERNS:
            kind = "intro"
        elif pos == len(section_lines) - 1 and lower in CONCLUSION_PATTERNS:
            kind = "conclusion"

        if kind == "excluded":
            continue
        if kind == "body":
            body_count += 1
            new = f"## Section {body_count}: {title}"
        else:
            new = f"## {title}"
        if new != raw:
            replacements[i] = new
            changes.append(f"L{i + 1}: '{raw}' -> '{new}'")

        section_end = section_lines[pos + 1] if pos + 1 < len(section_lines) else len(lines)
        sub_count = 0
        for j in range(i + 1, section_end):
            if not lines[j].startswith("### "):
                continue
            sub_raw = lines[j]
            sub_title = _normalize_em_dash(_strip_subsection_prefix(sub_raw[4:].strip()))
            if kind == "body":
                sub_count += 1
                sub_new = f"### {body_count}.{sub_count} {sub_title}"
            else:
                sub_new = f"### {sub_title}"
            if sub_new != sub_raw:
                replacements[j] = sub_new
                changes.append(f"L{j + 1}: '{sub_raw}' -> '{sub_new}'")

    for idx, value in replacements.items():
        lines[idx] = value
    return "\n".join(lines), changes


def normalize_headings_file(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    new_content, changes = normalize_headings(content)
    if changes:
        path.write_text(new_content, encoding="utf-8")
    return changes


def _extract_doi(entry: str) -> str | None:
    m = re.search(r"doi\s*=\s*\{([^}]+)\}", entry, re.IGNORECASE)
    if not m:
        return None
    doi = m.group(1).strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
            break
    return doi


def _has_abstract(entry: str) -> bool:
    m = re.search(r"abstract\s*=\s*\{([^}]*)\}", entry, re.IGNORECASE | re.DOTALL)
    return bool(m and len(m.group(1).strip()) > 10)


def _importance(entry: str) -> int:
    m = re.search(r"keywords\s*=\s*\{([^}]*)\}", entry, re.IGNORECASE)
    if not m:
        return 1
    value = m.group(1)
    if "High" in value:
        return 3
    if "Medium" in value:
        return 2
    return 1


def _merge_entry(existing: str, incoming: str) -> str:
    ex_abs = _has_abstract(existing)
    in_abs = _has_abstract(incoming)
    if ex_abs != in_abs:
        return incoming if in_abs else existing
    ex_imp = _importance(existing)
    in_imp = _importance(incoming)
    if in_imp > ex_imp:
        return incoming
    return existing


def _strip_section_prefix(title: str) -> str:
    m = RE_SECTION_PREFIX.match(title)
    return m.group(1).strip() if m else title


def _strip_subsection_prefix(title: str) -> str:
    m = RE_SUBSECTION_PREFIX.match(title)
    return m.group(1).strip() if m else title


def _normalize_em_dash(text: str) -> str:
    return re.sub(r"\s*\u2014\s*", ": ", text)


def cast_list(value: object) -> list[str]:
    if isinstance(value, list):
        return value
    return []


def generate_bibliography_apa(review_file: Path, bib_file: Path) -> dict[str, int]:
    review_text = review_file.read_text(encoding="utf-8")
    entries = _parse_bib_entries(bib_file.read_text(encoding="utf-8"))
    cited = _find_cited_entries(review_text, entries)
    references = _render_references_apa(cited)
    updated = _apply_references_section(review_text, references)
    review_file.write_text(updated, encoding="utf-8")
    return {"matched": len(cited), "total": len(entries)}


def _parse_bib_entries(content: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for chunk in re.split(r"\n(?=@)", content):
        text = chunk.strip()
        if not text or text.lower().startswith("@comment"):
            continue
        m = re.match(r"@(\w+)\{([^,]+),", text, re.IGNORECASE)
        if not m:
            continue
        entry_type = m.group(1).lower()
        key = m.group(2).strip()
        fields: dict[str, str] = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", text, re.DOTALL):
            fields[fm.group(1).lower()] = fm.group(2).strip()
        out.append({"type": entry_type, "key": key, "fields": fields})
    return out


def _normalize_text(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _find_cited_entries(review_text: str, entries: list[dict[str, object]]) -> list[dict[str, object]]:
    text = _normalize_text(review_text)
    matched: list[dict[str, object]] = []
    seen_doi: set[str] = set()
    for entry in entries:
        fields = entry["fields"]
        if not isinstance(fields, dict):
            continue
        author_field = str(fields.get("author", "")).strip()
        year = str(fields.get("year", "")).strip()
        if not author_field or not year:
            continue
        surname = _first_author_surname(author_field)
        if not surname:
            continue
        norm_surname = _normalize_text(surname)
        pattern = re.compile(r"\b" + re.escape(norm_surname) + r"\b", re.IGNORECASE)
        hit = False
        for m in pattern.finditer(text):
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            window = text[start:end]
            if year in window:
                hit = True
                break
        if not hit:
            continue

        doi = str(fields.get("doi", "")).strip().lower()
        if doi:
            doi = _normalize_doi_value(doi)
            if doi in seen_doi:
                continue
            seen_doi.add(doi)
        matched.append(entry)
    matched.sort(key=lambda e: (_first_author_surname(str(cast_dict(e["fields"]).get("author", ""))).lower(), str(cast_dict(e["fields"]).get("year", ""))))
    return matched


def _render_references_apa(entries: list[dict[str, object]]) -> str:
    lines = ["## References", ""]
    for entry in entries:
        fields = cast_dict(entry["fields"])
        author_text = _format_authors_apa(str(fields.get("author", "")))
        year = str(fields.get("year", "")).strip() or "n.d."
        title = _clean_ws(str(fields.get("title", "")).rstrip("."))
        journal = _clean_ws(str(fields.get("journal", "") or fields.get("booktitle", "") or fields.get("publisher", "")))
        volume = _clean_ws(str(fields.get("volume", "")))
        number = _clean_ws(str(fields.get("number", "") or fields.get("issue", "")))
        pages = _clean_ws(str(fields.get("pages", "")))
        doi = _normalize_doi_or_url(str(fields.get("doi", "")).strip(), str(fields.get("url", "")).strip())

        parts = [f"{author_text} ({year}). {title}."]
        if journal:
            journal_part = journal
            if volume:
                journal_part += f", {volume}"
            if number:
                journal_part += f"({number})"
            if pages:
                journal_part += f", {pages}"
            journal_part += "."
            parts.append(journal_part)
        if doi:
            parts.append(doi)
        lines.append(" ".join(p for p in parts if p).strip())
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def _apply_references_section(review_text: str, references_section: str) -> str:
    m = re.search(r"^## References\s*$", review_text, re.MULTILINE)
    if m:
        return review_text[: m.start()].rstrip() + "\n\n" + references_section + "\n"
    return review_text.rstrip() + "\n\n" + references_section + "\n"


def _format_authors_apa(author_field: str) -> str:
    authors = [a.strip() for a in author_field.split(" and ") if a.strip()]
    formatted = [_format_single_author_apa(a) for a in authors]
    if not formatted:
        return "Unknown"
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def _format_single_author_apa(author: str) -> str:
    if "," in author:
        last, rest = [p.strip() for p in author.split(",", 1)]
        first_parts = rest.split()
    else:
        parts = author.split()
        if not parts:
            return "Unknown"
        last = parts[-1]
        first_parts = parts[:-1]
    initials = " ".join(f"{p[0]}." for p in first_parts if p and p[0].isalpha())
    if initials:
        return f"{last}, {initials}"
    return last


def _first_author_surname(author_field: str) -> str:
    first = author_field.split(" and ")[0].strip()
    if "," in first:
        return first.split(",", 1)[0].strip()
    parts = first.split()
    return parts[-1] if parts else ""


def _normalize_doi_value(doi: str) -> str:
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"):
        if doi.startswith(prefix):
            return doi[len(prefix) :]
    return doi


def _normalize_doi_or_url(doi: str, url: str) -> str:
    doi = doi.strip()
    url = url.strip()
    if doi:
        return "https://doi.org/" + _normalize_doi_value(doi)
    return url


def _clean_ws(s: str) -> str:
    return " ".join(s.split())


def cast_dict(value: object) -> dict[str, str]:
    if isinstance(value, dict):
        out: dict[str, str] = {}
        for k, v in value.items():
            if isinstance(k, str):
                out[k] = str(v)
        return out
    return {}
