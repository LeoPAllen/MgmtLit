from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from mgmtlit.llm import LLMClient
from mgmtlit.models import Paper, QueryPlan
from mgmtlit.sources import CrossrefSource, OpenAlexSource, SemanticScholarSource
from mgmtlit.utils import dedupe_papers, dump_json, ensure_dir, render_bibtex, render_evidence_table, slugify

console = Console()

DEFAULT_BUSINESS_TERMS = [
    "management",
    "organization theory",
    "information systems",
    "digital transformation",
    "platform ecosystem",
    "innovation",
    "strategy",
    "dynamic capabilities",
    "institutional theory",
    "routines",
    "organizational learning",
    "governance",
    "leadership",
    "labor process",
    "algorithmic management",
]


@dataclass(slots=True)
class RunConfig:
    topic: str
    description: str
    output_dir: Path
    max_papers: int = 80
    from_year: int | None = None
    to_year: int | None = None
    include_terms: list[str] | None = None
    openalex_email: str | None = None
    semantic_scholar_api_key: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"


def build_query_plan(config: RunConfig) -> QueryPlan:
    seed_terms = DEFAULT_BUSINESS_TERMS + (config.include_terms or [])
    if config.openai_api_key:
        try:
            llm = LLMClient(api_key=config.openai_api_key, model=config.openai_model)
            return llm.plan_query(config.topic, config.description, seed_terms)
        except Exception as exc:
            console.print(f"[yellow]LLM planning failed, using fallback planner:[/yellow] {exc}")

    facets = [
        "Core construct definitions",
        "Theoretical mechanisms and contingencies",
        "Outcomes and performance effects",
        "Boundary conditions and contexts",
        "Methods and measurement patterns",
        "Managerial and policy implications",
    ]
    subquestions = [
        f"How is '{config.topic}' conceptualized across management and IS research?",
        "What dominant theoretical lenses explain observed relationships?",
        "What outcomes are most consistently associated with the focal construct?",
        "Which contexts and boundary conditions moderate effects?",
        "What methodological limitations and identification challenges persist?",
        "What unresolved debates suggest opportunities for future studies?",
    ]
    keywords = list(dict.fromkeys((seed_terms + config.topic.lower().split())[:35]))
    return QueryPlan(
        topic=config.topic,
        description=config.description,
        facets=facets,
        subquestions=subquestions,
        keywords=keywords,
    )


def _score_paper(paper: Paper, plan: QueryPlan) -> float:
    text = f"{paper.title} {(paper.abstract or '')} {' '.join(paper.fields)}".lower()
    keyword_hits = sum(1 for kw in plan.keywords if kw.lower() in text)
    facet_hits = sum(1 for f in plan.facets if any(t in text for t in f.lower().split()))
    cite_score = min((paper.citation_count or 0) / 200.0, 2.0)
    recency_boost = 0.4 if (paper.year and paper.year >= 2018) else 0.0
    return keyword_hits * 0.9 + facet_hits * 0.35 + cite_score + recency_boost


def retrieve_papers(config: RunConfig, plan: QueryPlan) -> list[Paper]:
    per_source = max(20, config.max_papers // 2)
    queries = [config.topic] + plan.keywords[:8]
    query = " ".join(dict.fromkeys(queries))

    sources = [
        OpenAlexSource(email=config.openalex_email),
        CrossrefSource(),
        SemanticScholarSource(api_key=config.semantic_scholar_api_key),
    ]

    raw: list[Paper] = []
    for source in sources:
        try:
            papers = source.search(
                query,
                from_year=config.from_year,
                to_year=config.to_year,
                max_results=per_source,
            )
            raw.extend(papers)
            console.print(f"[green]{source.name}[/green]: retrieved {len(papers)} papers")
        except Exception as exc:
            console.print(f"[yellow]{source.name} failed:[/yellow] {exc}")

    deduped = dedupe_papers(raw)
    for paper in deduped:
        paper.relevance_score = _score_paper(paper, plan)
    deduped.sort(key=lambda p: p.relevance_score, reverse=True)
    return deduped[: config.max_papers]


def _fallback_review(plan: QueryPlan, papers: list[Paper]) -> str:
    top = papers[:25]
    intro = (
        f"# Literature Review: {plan.topic}\n\n"
        f"## Introduction\n"
        f"Scope: {plan.description or plan.topic}. This draft synthesizes {len(top)} high-ranking papers "
        "from management, organizations, and information systems databases.\n"
    )

    sections = [intro]
    for facet in plan.facets[:6]:
        sections.append(f"\n## {facet}\n")
        related = [p for p in top if facet.split()[0].lower() in (p.abstract or "").lower()]
        chosen = related[:4] if related else top[:4]
        if not chosen:
            sections.append("Evidence is currently sparse for this facet.\n")
            continue
        for paper in chosen:
            author = paper.authors[0].split()[-1] if paper.authors else "Unknown"
            year = paper.year or "n.d."
            claim = (paper.abstract or "No abstract available.").replace("\n", " ")[:220]
            sections.append(f"- ({author}, {year}) {paper.title}: {claim}\n")

    sections.append("\n## Gaps and Future Research Agenda\n")
    sections.append(
        "Current evidence indicates conceptual fragmentation, uneven measurement quality, and limited causal identification in many studies. "
        "Future work should combine stronger theory-to-measure alignment with multi-method designs and cross-context replication.\n"
    )
    sections.append("\n## Conclusion\n")
    sections.append(
        "The reviewed literature suggests substantive progress but persistent disagreement about mechanisms and boundary conditions. "
        "A cumulative management science agenda should prioritize transparent designs, construct validity, and explicit competing explanations.\n"
    )

    sections.append("\n## Reference Mapping\n")
    for paper in top:
        sections.append(f"- {paper.title} ({paper.year or 'n.d.'})")
    return "\n".join(sections).strip() + "\n"


def compose_review(config: RunConfig, plan: QueryPlan, papers: list[Paper]) -> str:
    if config.openai_api_key:
        try:
            llm = LLMClient(api_key=config.openai_api_key, model=config.openai_model)
            return llm.compose_review(plan, papers)
        except Exception as exc:
            console.print(f"[yellow]LLM drafting failed, using fallback writer:[/yellow] {exc}")
    return _fallback_review(plan, papers)


def run_review(config: RunConfig) -> Path:
    slug = slugify(config.topic)
    out_dir = config.output_dir / slug
    ensure_dir(out_dir)

    console.print(f"[bold]Building review for:[/bold] {config.topic}")
    plan = build_query_plan(config)
    papers = retrieve_papers(config, plan)
    review = compose_review(config, plan, papers)

    dump_json(out_dir / "plan.json", plan.as_dict())
    dump_json(out_dir / "papers.json", [p.as_dict() for p in papers])
    (out_dir / "evidence_table.md").write_text(render_evidence_table(papers), encoding="utf-8")
    (out_dir / "review.md").write_text(review, encoding="utf-8")
    (out_dir / "references.bib").write_text(render_bibtex(papers), encoding="utf-8")

    return out_dir
