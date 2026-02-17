from __future__ import annotations

import json
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import httpx

from mgmtlit.domain_profiles import coverage_anchor_terms, query_variants, venue_boost
from mgmtlit.models import Paper
from mgmtlit.sources import (
    CoreSource,
    CrossrefSource,
    OpenAlexSource,
    RePEcSource,
    SSRNSource,
    SemanticScholarSource,
)
from mgmtlit.sources.arxiv import ArxivSource
from mgmtlit.utils import dedupe_papers


def paper_to_dict(paper: Paper) -> dict[str, Any]:
    return paper.as_dict()


def search_openalex(
    query: str,
    *,
    email: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    source = OpenAlexSource(email=email)
    papers = source.search(query, from_year=from_year, to_year=to_year, max_results=limit)
    return {"status": "ok", "source": "openalex", "query": query, "results": [paper_to_dict(p) for p in papers]}


def search_semantic_scholar(
    query: str,
    *,
    api_key: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    source = SemanticScholarSource(api_key=api_key)
    papers = source.search(query, from_year=from_year, to_year=to_year, max_results=limit)
    return {
        "status": "ok",
        "source": "semantic_scholar",
        "query": query,
        "results": [paper_to_dict(p) for p in papers],
    }


def search_crossref(
    query: str,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    source = CrossrefSource()
    papers = source.search(query, from_year=from_year, to_year=to_year, max_results=limit)
    return {"status": "ok", "source": "crossref", "query": query, "results": [paper_to_dict(p) for p in papers]}


def search_core(
    query: str,
    *,
    api_key: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    source = CoreSource(api_key=api_key)
    papers = source.search(query, from_year=from_year, to_year=to_year, max_results=limit)
    return {"status": "ok", "source": "core", "query": query, "results": [paper_to_dict(p) for p in papers]}


def search_ssrn(
    query: str,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    source = SSRNSource()
    papers = source.search(query, from_year=from_year, to_year=to_year, max_results=limit)
    return {"status": "ok", "source": "ssrn", "query": query, "results": [paper_to_dict(p) for p in papers]}


def search_repec(
    query: str,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    source = RePEcSource()
    papers = source.search(query, from_year=from_year, to_year=to_year, max_results=limit)
    return {"status": "ok", "source": "repec", "query": query, "results": [paper_to_dict(p) for p in papers]}


def search_portfolio(
    topic: str,
    *,
    description: str = "",
    openalex_email: str | None = None,
    s2_api_key: str | None = None,
    core_api_key: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    anchors = coverage_anchor_terms(topic, description, [])
    variants = query_variants(topic, "cross-disciplinary management research", anchors[:8])[:6]
    sources = [
        OpenAlexSource(email=openalex_email),
        SemanticScholarSource(api_key=s2_api_key),
        CrossrefSource(),
        CoreSource(api_key=core_api_key),
        RePEcSource(),
        SSRNSource(),
        ArxivSource(),
    ]
    all_papers: list[Paper] = []
    source_counts: dict[str, int] = {}
    for source in sources:
        count = 0
        for query in variants:
            try:
                papers = source.search(
                    query,
                    from_year=from_year,
                    to_year=to_year,
                    max_results=max(8, limit // 3),
                )
            except Exception:
                papers = []
            count += len(papers)
            all_papers.extend(papers)
        source_counts[source.name] = count
    merged = dedupe_papers(all_papers)
    for paper in merged:
        cite = min((paper.citation_count or 0) / 200.0, 2.0)
        recency = 0.3 if paper.year and paper.year >= 2019 else 0.0
        paper.relevance_score = cite + recency + venue_boost(paper.venue)
    merged.sort(key=lambda p: p.relevance_score, reverse=True)
    merged = merged[:limit]
    return {
        "status": "ok",
        "topic": topic,
        "description": description,
        "query_variants": variants,
        "source_counts": source_counts,
        "results": [paper_to_dict(p) for p in merged],
    }


def s2_citations(
    paper_id: str,
    *,
    api_key: str | None = None,
    mode: str = "both",
    influential_only: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    headers = {"x-api-key": api_key} if api_key else {}
    client = httpx.Client(timeout=30.0)
    fields = "paperId,title,year,venue,citationCount,authors,externalIds,url"
    out: dict[str, Any] = {"status": "ok", "paper_id": paper_id, "mode": mode, "results": {}}

    def get(endpoint: str) -> list[dict[str, Any]]:
        params: dict[str, str] = {"fields": fields, "limit": str(limit)}
        if influential_only:
            params["isInfluential"] = "true"
        resp = client.get(endpoint, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data", [])
        papers: list[dict[str, Any]] = []
        for row in data:
            # references endpoint uses row["citedPaper"], citations endpoint uses row["citingPaper"]
            paper = row.get("citedPaper") or row.get("citingPaper") or row
            papers.append(paper)
        return papers

    base = f"https://api.semanticscholar.org/graph/v1/paper/{quote(paper_id, safe='')}"
    try:
        if mode in {"both", "references"}:
            out["results"]["references"] = get(f"{base}/references")
        if mode in {"both", "citations"}:
            out["results"]["citations"] = get(f"{base}/citations")
    except Exception as exc:
        return {"status": "error", "paper_id": paper_id, "error": str(exc)}
    return out


def s2_recommend(
    positive_ids: list[str],
    *,
    api_key: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    headers = {"x-api-key": api_key} if api_key else {}
    client = httpx.Client(timeout=30.0)
    endpoint = "https://api.semanticscholar.org/recommendations/v1/papers"
    payload = {"positivePaperIds": positive_ids}
    params = {"limit": str(limit), "fields": "paperId,title,abstract,year,venue,citationCount,authors,externalIds,url"}
    try:
        resp = client.post(endpoint, json=payload, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("recommendedPapers", [])
        return {"status": "ok", "positive_ids": positive_ids, "results": data}
    except Exception as exc:
        return {"status": "error", "positive_ids": positive_ids, "error": str(exc)}


def verify_paper(
    *,
    doi: str | None = None,
    title: str | None = None,
    author: str | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    client = httpx.Client(timeout=30.0)
    try:
        if doi:
            endpoint = f"https://api.crossref.org/works/{quote(doi, safe='')}"
            resp = client.get(endpoint)
            resp.raise_for_status()
            item = resp.json().get("message", {})
            return {"status": "ok", "results": [_crossref_item_to_record(item)]}

        q = " ".join(x for x in [title or "", author or "", str(year or "")] if x).strip()
        if not q:
            return {"status": "error", "error": "provide doi or title/author/year query"}
        params = {"query.bibliographic": q, "rows": "5"}
        resp = client.get("https://api.crossref.org/works", params=params)
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        return {"status": "ok", "results": [_crossref_item_to_record(item) for item in items]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def resolve_abstract(
    *,
    doi: str | None = None,
    title: str | None = None,
    openalex_email: str | None = None,
    s2_api_key: str | None = None,
) -> dict[str, Any]:
    # 1) Semantic Scholar by DOI
    if doi:
        try:
            client = httpx.Client(timeout=30.0)
            headers = {"x-api-key": s2_api_key} if s2_api_key else {}
            resp = client.get(
                f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote(doi, safe='')}",
                params={"fields": "paperId,title,abstract"},
                headers=headers,
            )
            if resp.status_code < 400:
                data = resp.json()
                abs_text = (data.get("abstract") or "").strip()
                if abs_text:
                    return {"status": "ok", "abstract": abs_text, "source": "s2"}
        except Exception:
            pass

    # 2) OpenAlex search
    if title or doi:
        try:
            query = title or doi or ""
            results = search_openalex(query, email=openalex_email, limit=5)
            for item in results.get("results", []):
                abs_text = (item.get("abstract") or "").strip()
                if abs_text:
                    return {"status": "ok", "abstract": abs_text, "source": "openalex"}
        except Exception:
            pass

    # 3) Semantic Scholar query by title
    if title:
        try:
            results = search_semantic_scholar(title, api_key=s2_api_key, limit=5)
            for item in results.get("results", []):
                abs_text = (item.get("abstract") or "").strip()
                if abs_text:
                    return {"status": "ok", "abstract": abs_text, "source": "s2"}
        except Exception:
            pass

    return {"status": "not_found"}


@dataclass(slots=True)
class BibEntry:
    entry_type: str
    key: str
    fields: dict[str, str]


def enrich_bibliography(
    bib_path: Path,
    *,
    openalex_email: str | None = None,
    s2_api_key: str | None = None,
    resolver: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    text = bib_path.read_text(encoding="utf-8")
    entries = _parse_bib_entries(text)
    resolve = resolver or resolve_abstract
    enriched = 0
    incomplete = 0
    for entry in entries:
        abstract = entry.fields.get("abstract", "").strip()
        if abstract:
            continue
        result = resolve(
            doi=entry.fields.get("doi"),
            title=entry.fields.get("title"),
            openalex_email=openalex_email,
            s2_api_key=s2_api_key,
        )
        if result.get("status") == "ok":
            entry.fields["abstract"] = str(result.get("abstract", "")).strip()
            entry.fields["abstract_source"] = str(result.get("source", "unknown"))
            enriched += 1
        else:
            _append_keywords(entry.fields, ["INCOMPLETE", "no-abstract"])
            incomplete += 1
    bib_path.write_text(_render_bib_entries(entries), encoding="utf-8")
    return {"status": "ok", "enriched": enriched, "incomplete": incomplete, "entries": len(entries)}


def _append_keywords(fields: dict[str, str], values: list[str]) -> None:
    current = [v.strip() for v in fields.get("keywords", "").split(",") if v.strip()]
    for value in values:
        if value not in current:
            current.append(value)
    if current:
        fields["keywords"] = ", ".join(current)


def _parse_bib_entries(text: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    for chunk in re.split(r"\n(?=@)", text):
        block = chunk.strip()
        if not block or block.lower().startswith("@comment"):
            continue
        m = re.match(r"@(\w+)\{([^,]+),", block, re.IGNORECASE)
        if not m:
            continue
        entry_type = m.group(1).lower()
        key = m.group(2).strip()
        fields: dict[str, str] = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", block, re.DOTALL):
            fields[fm.group(1).lower()] = fm.group(2).strip()
        entries.append(BibEntry(entry_type=entry_type, key=key, fields=fields))
    return entries


def _render_bib_entries(entries: list[BibEntry]) -> str:
    chunks: list[str] = []
    for entry in entries:
        lines = [f"@{entry.entry_type}{{{entry.key},"]
        for key, value in entry.fields.items():
            if value:
                safe = value.replace("{", "").replace("}", "")
                lines.append(f"  {key} = {{{safe}}},")
        lines.append("}")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks).strip() + ("\n" if chunks else "")


def _crossref_item_to_record(item: dict[str, Any]) -> dict[str, Any]:
    published = item.get("published-print") or item.get("published-online") or {}
    parts = published.get("date-parts", [[None]])
    year = parts[0][0] if parts and parts[0] else None
    typ = str(item.get("type") or "")
    bib_type = _crossref_to_bibtex_type(typ)
    return {
        "doi": item.get("DOI"),
        "title": ((item.get("title") or [""])[0] if isinstance(item.get("title"), list) else item.get("title")),
        "year": year,
        "container_title": ((item.get("container-title") or [""])[0] if isinstance(item.get("container-title"), list) else item.get("container-title")),
        "volume": item.get("volume"),
        "issue": item.get("issue"),
        "page": item.get("page"),
        "publisher": item.get("publisher"),
        "type": typ,
        "suggested_bibtex_type": bib_type,
        "url": item.get("URL"),
    }


def _crossref_to_bibtex_type(crossref_type: str) -> str:
    mapping = {
        "journal-article": "article",
        "book-chapter": "incollection",
        "proceedings-article": "inproceedings",
        "book": "book",
        "edited-book": "book",
        "dissertation": "phdthesis",
    }
    return mapping.get(crossref_type, "misc")


def write_json(path: Path | None, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, indent=2, ensure_ascii=True)
    if path is None:
        print(serialized)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")
