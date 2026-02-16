from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mgmtlit.agents import (
    AgentState,
    DomainResearchAgent,
    PlannerAgent,
    RunInputs,
    SynthesisPlannerAgent,
    SynthesisWriterAgent,
)
from mgmtlit.llm import create_backend
from mgmtlit.utils import (
    dump_json,
    ensure_dir,
    render_bibtex,
    render_evidence_table,
    render_lit_review_plan_md,
    render_references_markdown,
    render_synthesis_outline_md,
    render_task_progress,
    slugify,
    with_yaml_frontmatter,
)


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
    llm_backend: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    claude_command: str = "claude"
    claude_model: str = "sonnet"
    resume: bool = True


PHASES = [
    "Phase 1: Verify environment and determine execution mode",
    "Phase 2: Structure literature review domains",
    "Phase 3: Research domains in parallel",
    "Phase 4: Outline synthesis review across domains",
    "Phase 5: Write review sections in parallel",
    "Phase 6: Assemble final review files and bibliography",
]


def run_review(config: RunConfig) -> Path:
    slug = slugify(config.topic)
    review_dir = config.output_dir / slug
    intermediate_dir = review_dir / "intermediate_files"
    json_dir = intermediate_dir / "json"
    ensure_dir(review_dir)
    ensure_dir(intermediate_dir)
    ensure_dir(json_dir)

    backend = create_backend(
        config.llm_backend,
        openai_api_key=config.openai_api_key,
        openai_model=config.openai_model,
        claude_command=config.claude_command,
        claude_model=config.claude_model,
        gemini_api_key=config.gemini_api_key,
        gemini_model=config.gemini_model,
    )
    state = AgentState(
        inputs=RunInputs(
            topic=config.topic,
            description=config.description,
            max_papers=config.max_papers,
            from_year=config.from_year,
            to_year=config.to_year,
            include_terms=config.include_terms or [],
            openalex_email=config.openalex_email,
            semantic_scholar_api_key=config.semantic_scholar_api_key,
        )
    )

    completed: list[str] = []
    current = PHASES[0]
    _write_progress(intermediate_dir / "task-progress.md", config.topic, completed, current, "Initializing review run.")

    final_review_path = review_dir / "literature-review-final.md"
    final_bib_path = review_dir / "literature-all.bib"
    if config.resume and final_review_path.exists() and final_bib_path.exists():
        completed = PHASES.copy()
        _write_progress(
            intermediate_dir / "task-progress.md",
            config.topic,
            completed,
            "Workflow already complete.",
            "Detected existing final artifacts and returned without overwriting.",
        )
        return review_dir

    completed.append(PHASES[0])
    current = PHASES[1]
    _write_progress(intermediate_dir / "task-progress.md", config.topic, completed, current, "Environment checks passed.")

    PlannerAgent().run(state, backend)
    if state.plan is None:
        raise RuntimeError("Pipeline failed: planner did not produce a query plan.")
    dump_json(review_dir / "plan.json", state.plan.as_dict())
    dump_json(intermediate_dir / "domains.json", [d.as_dict() for d in state.domains])
    (intermediate_dir / "lit-review-plan.md").write_text(
        render_lit_review_plan_md(state.plan, state.domains), encoding="utf-8"
    )
    completed.append(PHASES[1])
    current = PHASES[2]
    _write_progress(intermediate_dir / "task-progress.md", config.topic, completed, current, "Domain plan generated.")

    DomainResearchAgent().run(state, backend)
    for domain in state.domains:
        papers = state.domain_papers.get(domain.index, [])
        bib_name = f"literature-domain-{domain.index}.bib"
        (intermediate_dir / bib_name).write_text(render_bibtex(papers), encoding="utf-8")
        dump_json(
            json_dir / f"domain-{domain.index}-papers.json",
            [p.as_dict() for p in papers],
        )
    dump_json(review_dir / "papers.json", [p.as_dict() for p in state.papers])
    (review_dir / "evidence_table.md").write_text(render_evidence_table(state.papers), encoding="utf-8")
    completed.append(PHASES[2])
    current = PHASES[3]
    _write_progress(intermediate_dir / "task-progress.md", config.topic, completed, current, "Domain research complete.")

    SynthesisPlannerAgent().run(state, backend)
    if state.outline is None:
        raise RuntimeError("Pipeline failed: synthesis planner did not produce an outline.")
    dump_json(intermediate_dir / "synthesis-outline.json", state.outline.as_dict())
    (intermediate_dir / "synthesis-outline.md").write_text(
        render_synthesis_outline_md(config.topic, state.outline), encoding="utf-8"
    )
    completed.append(PHASES[3])
    current = PHASES[4]
    _write_progress(intermediate_dir / "task-progress.md", config.topic, completed, current, "Synthesis outline complete.")

    SynthesisWriterAgent().run(state, backend)
    for section in state.outline.sections:
        text = state.section_text.get(section.index, "").strip()
        if not text:
            continue
        (intermediate_dir / f"synthesis-section-{section.index}.md").write_text(text + "\n", encoding="utf-8")
    completed.append(PHASES[4])
    current = PHASES[5]
    _write_progress(intermediate_dir / "task-progress.md", config.topic, completed, current, "Section drafting complete.")

    review_body = state.review.strip()
    references_section = render_references_markdown(state.papers)
    full_review = review_body + "\n\n" + references_section + "\n"
    final_review = with_yaml_frontmatter(full_review, title=f"Literature Review: {config.topic}")
    final_review_path.write_text(final_review, encoding="utf-8")
    final_bib_path.write_text(render_bibtex(state.papers), encoding="utf-8")
    (review_dir / "references.bib").write_text(render_bibtex(state.papers), encoding="utf-8")
    (review_dir / "review.md").write_text(state.review, encoding="utf-8")
    dump_json(review_dir / "agent_trace.json", [e.as_dict() for e in state.events])

    completed.append(PHASES[5])
    _write_progress(
        intermediate_dir / "task-progress.md",
        config.topic,
        completed,
        "Complete",
        "Final review and bibliography assembled.",
    )
    return review_dir


def _write_progress(path: Path, topic: str, completed: list[str], current: str, note: str) -> None:
    path.write_text(
        render_task_progress(topic=topic, phases=PHASES, completed=completed, current=current, note=note),
        encoding="utf-8",
    )
