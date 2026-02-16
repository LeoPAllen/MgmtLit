from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any

from mgmtlit.llm import LLMBackend
from mgmtlit.models import Paper, QueryPlan
from mgmtlit.utils import dedupe_papers

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
class DomainPlan:
    index: int
    name: str
    focus: str
    key_questions: list[str]
    search_terms: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "focus": self.focus,
            "key_questions": self.key_questions,
            "search_terms": self.search_terms,
        }


@dataclass(slots=True)
class SynthesisSection:
    index: int
    heading: str
    purpose: str
    word_target: int
    domain_indices: list[int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "heading": self.heading,
            "purpose": self.purpose,
            "word_target": self.word_target,
            "domain_indices": self.domain_indices,
        }


@dataclass(slots=True)
class SynthesisOutline:
    created_on: str
    total_papers: int
    sections: list[SynthesisSection]
    notes_for_writers: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "created_on": self.created_on,
            "total_papers": self.total_papers,
            "sections": [s.as_dict() for s in self.sections],
            "notes_for_writers": self.notes_for_writers,
        }


@dataclass(slots=True)
class RunInputs:
    topic: str
    description: str
    max_papers: int
    from_year: int | None
    to_year: int | None
    include_terms: list[str]
    openalex_email: str | None
    semantic_scholar_api_key: str | None


@dataclass(slots=True)
class AgentEvent:
    agent: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


@dataclass(slots=True)
class AgentState:
    inputs: RunInputs
    plan: QueryPlan | None = None
    domains: list[DomainPlan] = field(default_factory=list)
    domain_queries: dict[int, str] = field(default_factory=dict)
    domain_papers: dict[int, list[Paper]] = field(default_factory=dict)
    papers: list[Paper] = field(default_factory=list)
    outline: SynthesisOutline | None = None
    section_text: dict[int, str] = field(default_factory=dict)
    review: str = ""
    events: list[AgentEvent] = field(default_factory=list)

    def log(self, event: AgentEvent) -> None:
        self.events.append(event)


class PlannerAgent:
    name = "literature-review-planner"

    def run(self, state: AgentState, backend: LLMBackend) -> None:
        seed_terms = DEFAULT_BUSINESS_TERMS + state.inputs.include_terms
        fallback_plan = _fallback_query_plan(state.inputs.topic, state.inputs.description, seed_terms)
        fallback_domains = _fallback_domains(fallback_plan)
        try:
            response = backend.ask_json(
                {
                    "task": "Create a management literature review plan with explicit domains.",
                    "topic": state.inputs.topic,
                    "description": state.inputs.description,
                    "seed_terms": seed_terms,
                    "requirements": {
                        "facets": "5-8 thematic facets",
                        "subquestions": "5-8 specific research subquestions",
                        "keywords": "20-30 search keywords/bigrams",
                        "domains": "3-8 literature-review domains, each with focus, key questions, and search terms",
                    },
                    "output_json_schema": {
                        "facets": ["..."],
                        "subquestions": ["..."],
                        "keywords": ["..."],
                        "domains": [
                            {
                                "name": "...",
                                "focus": "...",
                                "key_questions": ["..."],
                                "search_terms": ["..."],
                            }
                        ],
                    },
                }
            )
            plan = QueryPlan(
                topic=state.inputs.topic,
                description=state.inputs.description,
                facets=_as_string_list(response.get("facets")) or fallback_plan.facets,
                subquestions=_as_string_list(response.get("subquestions")) or fallback_plan.subquestions,
                keywords=_as_string_list(response.get("keywords")) or fallback_plan.keywords,
            )
            parsed_domains = _parse_domains(response.get("domains"))
            state.plan = plan
            state.domains = parsed_domains or fallback_domains
            state.log(
                AgentEvent(
                    agent=self.name,
                    status="ok",
                    message="Generated plan and domains with LLM backend.",
                    details={"backend": backend.name, "domains": len(state.domains)},
                )
            )
        except Exception as exc:
            state.plan = fallback_plan
            state.domains = fallback_domains
            state.log(
                AgentEvent(
                    agent=self.name,
                    status="fallback",
                    message="Used deterministic planner/domain fallback.",
                    details={"reason": str(exc), "domains": len(state.domains)},
                )
            )


class DomainResearchAgent:
    name = "domain-literature-researcher"

    def run(self, state: AgentState, backend: LLMBackend) -> None:
        del backend
        if state.plan is None or not state.domains:
            raise RuntimeError("Planner must run before domain research.")
        from mgmtlit.sources import CrossrefSource, OpenAlexSource, SemanticScholarSource

        sources = [
            OpenAlexSource(email=state.inputs.openalex_email),
            CrossrefSource(),
            SemanticScholarSource(api_key=state.inputs.semantic_scholar_api_key),
        ]
        per_domain_budget = max(15, state.inputs.max_papers // max(len(state.domains), 1))
        all_raw: list[Paper] = []
        retrieval_log: dict[str, dict[str, int]] = {}

        for domain in state.domains:
            query = _domain_query(state.inputs.topic, domain)
            state.domain_queries[domain.index] = query
            domain_raw: list[Paper] = []
            source_counts: dict[str, int] = {}
            for source in sources:
                try:
                    papers = source.search(
                        query,
                        from_year=state.inputs.from_year,
                        to_year=state.inputs.to_year,
                        max_results=per_domain_budget,
                    )
                    cleaned = [_sanitize_paper(p) for p in papers]
                    cleaned = [p for p in cleaned if _looks_sane_paper(p)]
                    domain_raw.extend(cleaned)
                    source_counts[source.name] = len(papers)
                except Exception:
                    source_counts[source.name] = 0

            deduped = dedupe_papers(domain_raw)
            for paper in deduped:
                paper.relevance_score = _score_paper(paper, state.plan, domain)
            deduped.sort(key=lambda p: p.relevance_score, reverse=True)
            trimmed = deduped[:per_domain_budget]
            state.domain_papers[domain.index] = trimmed
            all_raw.extend(trimmed)
            retrieval_log[f"domain_{domain.index}"] = source_counts

        merged = dedupe_papers(all_raw)
        for paper in merged:
            paper.relevance_score = _score_paper(paper, state.plan, None)
        merged.sort(key=lambda p: p.relevance_score, reverse=True)
        state.papers = merged[: state.inputs.max_papers]
        state.log(
            AgentEvent(
                agent=self.name,
                status="ok",
                message="Completed domain-level retrieval and ranking.",
                details={"domains": len(state.domains), "final_count": len(state.papers), "retrieval": retrieval_log},
            )
        )


class SynthesisPlannerAgent:
    name = "synthesis-planner"

    def run(self, state: AgentState, backend: LLMBackend) -> None:
        if state.plan is None or not state.domains:
            raise RuntimeError("Plan and domains required for synthesis planning.")
        fallback = _fallback_outline(state)
        try:
            domain_summaries = [
                {
                    "index": d.index,
                    "name": d.name,
                    "focus": d.focus,
                    "paper_count": len(state.domain_papers.get(d.index, [])),
                }
                for d in state.domains
            ]
            response = backend.ask_json(
                {
                    "task": "Create a synthesis outline for a management literature review.",
                    "topic": state.plan.topic,
                    "description": state.plan.description,
                    "facets": state.plan.facets,
                    "subquestions": state.plan.subquestions,
                    "domains": domain_summaries,
                    "target_review_words": "3000-4000",
                    "requirements": {
                        "sections": "3-6 sections including Introduction and Conclusion",
                        "each_section": "heading, purpose, word_target, mapped domain indices",
                        "notes_for_writers": "instructions for argument flow and citation strategy",
                    },
                    "output_json_schema": {
                        "sections": [
                            {
                                "heading": "## Introduction",
                                "purpose": "...",
                                "word_target": 450,
                                "domain_indices": [1, 2],
                            }
                        ],
                        "notes_for_writers": "...",
                    },
                }
            )
            sections = _parse_sections(response.get("sections"), len(state.domains))
            notes = str(response.get("notes_for_writers") or "").strip()
            if not sections:
                state.outline = fallback
            else:
                state.outline = SynthesisOutline(
                    created_on=date.today().isoformat(),
                    total_papers=len(state.papers),
                    sections=sections,
                    notes_for_writers=notes or fallback.notes_for_writers,
                )
            state.log(
                AgentEvent(
                    agent=self.name,
                    status="ok",
                    message="Created synthesis outline.",
                    details={"sections": len(state.outline.sections), "backend": backend.name},
                )
            )
        except Exception as exc:
            state.outline = fallback
            state.log(
                AgentEvent(
                    agent=self.name,
                    status="fallback",
                    message="Used deterministic synthesis outline fallback.",
                    details={"reason": str(exc), "sections": len(state.outline.sections)},
                )
            )


class SynthesisWriterAgent:
    name = "synthesis-writer"

    def run(self, state: AgentState, backend: LLMBackend) -> None:
        if state.plan is None or state.outline is None:
            raise RuntimeError("Synthesis outline required before writing sections.")

        for section in state.outline.sections:
            selected = _section_papers(state, section)
            fallback_text = _fallback_section_text(section, selected, state.plan)
            try:
                evidence = [
                    {
                        "title": p.title,
                        "authors": p.authors[:4],
                        "year": p.year,
                        "venue": p.venue,
                        "doi": p.doi,
                        "abstract": (p.abstract or "")[:1200],
                        "relevance_score": round(p.relevance_score, 3),
                    }
                    for p in selected[:30]
                ]
                text = backend.ask_text(
                    {
                        "task": "Write one section of an academic literature review.",
                        "topic": state.plan.topic,
                        "description": state.plan.description,
                        "section_heading": section.heading,
                        "section_purpose": section.purpose,
                        "target_words": section.word_target,
                        "instructions": [
                            "Use Chicago-style in-text citations (Author, Year).",
                            "Ground claims only in provided evidence.",
                            "Avoid evaluative superlatives unless explicit evidence supports them.",
                            "Return markdown with the exact section heading on the first line.",
                        ],
                        "evidence": evidence,
                    }
                ).strip()
                if not text.startswith(section.heading):
                    text = f"{section.heading}\n\n{text}"
                state.section_text[section.index] = text.rstrip() + "\n"
            except Exception:
                state.section_text[section.index] = fallback_text

        ordered = [state.section_text[s.index].rstrip() for s in state.outline.sections if s.index in state.section_text]
        state.review = "\n\n".join(ordered).strip() + "\n"
        state.log(
            AgentEvent(
                agent=self.name,
                status="ok",
                message="Wrote section files and assembled draft review.",
                details={"sections": len(state.section_text)},
            )
        )


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _parse_domains(value: Any) -> list[DomainPlan]:
    if not isinstance(value, list):
        return []
    out: list[DomainPlan] = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        focus = str(item.get("focus") or "").strip() or f"Literature domain for {name}"
        key_questions = _as_string_list(item.get("key_questions"))[:4]
        terms = _as_string_list(item.get("search_terms"))[:10]
        out.append(
            DomainPlan(
                index=idx,
                name=name,
                focus=focus,
                key_questions=key_questions,
                search_terms=terms,
            )
        )
    return out[:8]


def _parse_sections(value: Any, num_domains: int) -> list[SynthesisSection]:
    if not isinstance(value, list):
        return []
    out: list[SynthesisSection] = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        heading = str(item.get("heading") or "").strip() or f"## Section {idx}"
        if not heading.startswith("## "):
            heading = f"## {heading.lstrip('#').strip()}"
        purpose = str(item.get("purpose") or "").strip() or "Synthesize key debates and implications."
        try:
            word_target = int(item.get("word_target", 600))
        except Exception:
            word_target = 600
        domain_indices = item.get("domain_indices")
        if isinstance(domain_indices, list):
            mapped = [int(x) for x in domain_indices if isinstance(x, int) and 1 <= x <= num_domains]
        else:
            mapped = []
        out.append(
            SynthesisSection(
                index=idx,
                heading=heading,
                purpose=purpose,
                word_target=max(250, min(word_target, 1800)),
                domain_indices=mapped,
            )
        )
    return out[:8]


def _domain_query(topic: str, domain: DomainPlan) -> str:
    chunks = [topic, domain.name] + domain.search_terms[:8]
    text = " ".join(c for c in chunks if c)
    tokens = re.findall(r"[a-zA-Z0-9\-]+", text.lower())
    stop = {"the", "and", "for", "with", "from", "into", "that", "this", "then", "how"}
    kept: list[str] = []
    for tok in tokens:
        if len(tok) < 3 or tok in stop:
            continue
        if tok not in kept:
            kept.append(tok)
    query = " ".join(kept[:22]).strip()
    return query[:220]


def _score_paper(paper: Paper, plan: QueryPlan, domain: DomainPlan | None) -> float:
    text = f"{paper.title} {(paper.abstract or '')} {' '.join(paper.fields)}".lower()
    keyword_hits = sum(1 for kw in plan.keywords if kw.lower() in text)
    facet_hits = sum(1 for f in plan.facets if any(t in text for t in f.lower().split()))
    domain_hits = 0
    if domain:
        domain_tokens = (domain.name + " " + domain.focus + " " + " ".join(domain.search_terms)).lower().split()
        domain_hits = sum(1 for tok in domain_tokens[:25] if tok and tok in text)
    cite_score = min((paper.citation_count or 0) / 200.0, 2.0)
    recency_boost = 0.4 if (paper.year and paper.year >= 2018) else 0.0
    return keyword_hits * 0.9 + facet_hits * 0.35 + domain_hits * 0.15 + cite_score + recency_boost


def _fallback_query_plan(topic: str, description: str, seed_terms: list[str]) -> QueryPlan:
    facets = [
        "Core construct definitions",
        "Theoretical mechanisms and contingencies",
        "Outcomes and performance effects",
        "Boundary conditions and contexts",
        "Methods and measurement patterns",
        "Managerial and policy implications",
    ]
    subquestions = [
        f"How is '{topic}' conceptualized across management and IS research?",
        "What dominant theoretical lenses explain observed relationships?",
        "What outcomes are most consistently associated with the focal construct?",
        "Which contexts and boundary conditions moderate effects?",
        "What methodological limitations and identification challenges persist?",
        "What unresolved debates suggest opportunities for future studies?",
    ]
    keywords = list(dict.fromkeys((seed_terms + topic.lower().split())[:35]))
    return QueryPlan(
        topic=topic,
        description=description,
        facets=facets,
        subquestions=subquestions,
        keywords=keywords,
    )


def _fallback_domains(plan: QueryPlan) -> list[DomainPlan]:
    domains: list[DomainPlan] = []
    for idx, facet in enumerate(plan.facets[:6], start=1):
        domains.append(
            DomainPlan(
                index=idx,
                name=facet,
                focus=f"Management literature centered on {facet.lower()} for topic '{plan.topic}'.",
                key_questions=[
                    f"What does research report about {facet.lower()}?",
                    f"How does {facet.lower()} shape findings on {plan.topic}?",
                ],
                search_terms=plan.keywords[(idx - 1) * 4 : idx * 4] or plan.keywords[:4],
            )
        )
    return domains


def _fallback_outline(state: AgentState) -> SynthesisOutline:
    sections: list[SynthesisSection] = [
        SynthesisSection(
            index=1,
            heading="## Introduction",
            purpose="Frame the topic, scope, and research motivation.",
            word_target=450,
            domain_indices=[],
        )
    ]
    next_idx = 2
    for domain in state.domains[:4]:
        sections.append(
            SynthesisSection(
                index=next_idx,
                heading=f"## Section {next_idx - 1}: {domain.name}",
                purpose=domain.focus,
                word_target=700,
                domain_indices=[domain.index],
            )
        )
        next_idx += 1
    sections.append(
        SynthesisSection(
            index=next_idx,
            heading="## Conclusion",
            purpose="Summarize key tensions, gaps, and future research priorities.",
            word_target=450,
            domain_indices=[],
        )
    )
    return SynthesisOutline(
        created_on=date.today().isoformat(),
        total_papers=len(state.papers),
        sections=sections,
        notes_for_writers=(
            "Use high-relevance papers first, surface competing explanations, and make boundary "
            "conditions explicit in every body section."
        ),
    )


def _section_papers(state: AgentState, section: SynthesisSection) -> list[Paper]:
    if section.domain_indices:
        collected: list[Paper] = []
        for idx in section.domain_indices:
            collected.extend(state.domain_papers.get(idx, []))
        deduped = dedupe_papers(collected)
        deduped.sort(key=lambda p: p.relevance_score, reverse=True)
        return deduped[:20]
    return state.papers[:20]


def _fallback_section_text(section: SynthesisSection, papers: list[Paper], plan: QueryPlan) -> str:
    lines = [section.heading, "", section.purpose, ""]
    if not papers:
        lines.append(
            "Available evidence is sparse in the retrieved corpus, indicating a need for broader "
            "search expansion or tighter conceptual boundaries."
        )
        return "\n".join(lines).rstrip() + "\n"

    for paper in papers[:8]:
        author = paper.authors[0].split()[-1] if paper.authors else "Unknown"
        year = paper.year or "n.d."
        title = paper.title.replace("\n", " ").strip()
        title = title[:180] + ("..." if len(title) > 180 else "")
        snippet = (paper.abstract or "No abstract available.").replace("\n", " ").strip()[:220]
        lines.append(f"- ({author}, {year}) {title}: {snippet}")
    lines.extend(
        [
            "",
            (
                "Taken together, these studies indicate unresolved tensions around mechanisms, "
                "measurement choices, and boundary conditions that are central to the review topic."
            ),
            (
                f"This section therefore positions {plan.topic} as an active, cumulative research "
                "program rather than a settled evidence base."
            ),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _sanitize_paper(paper: Paper) -> Paper:
    title = _clean_text(paper.title, limit=240)
    abstract = _clean_text(paper.abstract or "", limit=2500) or None
    authors = [_clean_text(a, limit=80) for a in paper.authors if _clean_text(a, limit=80)]
    fields = [_clean_text(f, limit=60) for f in paper.fields if _clean_text(f, limit=60)]
    paper.title = title or "Untitled"
    paper.abstract = abstract
    paper.authors = authors
    paper.fields = fields[:8]
    return paper


def _looks_sane_paper(paper: Paper) -> bool:
    title = (paper.title or "").lower()
    if len(title) < 8:
        return False
    if len(title) > 260:
        return False
    bad_markers = ["download pdf", "view description", "creative commons license", "article:", "volume", "issue"]
    marker_hits = sum(1 for m in bad_markers if m in title)
    if marker_hits >= 3:
        return False
    if title.count("http") > 1:
        return False
    return True


def _clean_text(value: str, *, limit: int) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text
