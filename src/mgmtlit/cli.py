from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from mgmtlit.config import load_env
from mgmtlit.agent_pack import scaffold_agent_pack
from mgmtlit.pipeline import RunConfig, run_review
from mgmtlit.research_tools import (
    enrich_bibliography,
    s2_citations,
    s2_recommend,
    search_crossref,
    search_openalex,
    search_portfolio,
    search_semantic_scholar,
    verify_paper,
    write_json,
)
from mgmtlit.postprocess import (
    assemble_review,
    dedupe_bib,
    generate_bibliography_apa,
    normalize_headings_file,
)

app = typer.Typer(help="AI-assisted literature reviews for management, organizations, and IS")
console = Console()


@app.command()
def review(
    topic: str = typer.Argument(..., help="Primary research question/topic"),
    description: str = typer.Option("", help="Optional scope/constraints for the review"),
    output_dir: Path = typer.Option(Path("reviews"), help="Output directory"),
    max_papers: int = typer.Option(80, min=20, max=300, help="Maximum papers in final evidence set"),
    from_year: int | None = typer.Option(None, help="Lower publication year bound"),
    to_year: int | None = typer.Option(None, help="Upper publication year bound"),
    include_term: list[str] = typer.Option(None, help="Extra domain keywords (repeatable)"),
    backend: str | None = typer.Option(
        None,
        help="LLM backend override: openai | gemini | claude_code | none",
    ),
    gemini_model: str | None = typer.Option(None, help="Gemini model override"),
    claude_model: str | None = typer.Option(None, help="Claude Code model override"),
    claude_command: str | None = typer.Option(None, help="Claude Code executable (default: claude)"),
    resume: bool = typer.Option(True, help="Resume if final artifacts already exist"),
    fail_on_llm_fallback: bool = typer.Option(
        True,
        help="Fail fast if LLM planning+synthesis both fall back to deterministic mode",
    ),
) -> None:
    env = load_env()
    config = RunConfig(
        topic=topic,
        description=description,
        output_dir=output_dir,
        max_papers=max_papers,
        from_year=from_year,
        to_year=to_year,
        include_terms=include_term or [],
        openalex_email=env.openalex_email,
        semantic_scholar_api_key=env.semantic_scholar_api_key,
        llm_backend=backend or env.llm_backend,
        openai_api_key=env.openai_api_key,
        openai_model=env.openai_model,
        gemini_api_key=env.gemini_api_key,
        gemini_model=gemini_model or env.gemini_model,
        claude_model=claude_model or env.claude_model,
        claude_command=claude_command or env.claude_command,
        resume=resume,
        fail_on_llm_fallback=fail_on_llm_fallback,
    )

    out = run_review(config)
    console.print(f"[bold green]Done.[/bold green] Files written to: {out}")

@app.command("assemble")
def assemble_cmd(
    output: Path = typer.Argument(..., help="Assembled markdown output path"),
    sections: list[Path] = typer.Argument(..., help="Section markdown files"),
    title: str = typer.Option(..., "--title", help="Review title for YAML frontmatter"),
    review_date: str | None = typer.Option(None, "--date", help="Optional YYYY-MM-DD date"),
) -> None:
    stats = assemble_review(output, sections, title=title, review_date=review_date)
    console.print(f"[bold green]Assembled[/bold green] {len(stats['sections'])} sections -> {output}")
    if stats["warnings"]:
        for warning in stats["warnings"]:
            console.print(f"[yellow]{warning}[/yellow]")


@app.command("dedupe-bib")
def dedupe_bib_cmd(
    output: Path = typer.Argument(..., help="Output merged BibTeX path"),
    inputs: list[Path] = typer.Argument(..., help="Input BibTeX files"),
) -> None:
    duplicates = dedupe_bib(inputs, output)
    console.print(f"[bold green]Wrote[/bold green] {output}")
    console.print(f"Removed duplicates: {len(duplicates)}")


@app.command("normalize-headings")
def normalize_headings_cmd(
    file: Path = typer.Argument(..., help="Assembled markdown file (modified in-place)"),
) -> None:
    changes = normalize_headings_file(file)
    if not changes:
        console.print("No heading changes needed.")
        return
    console.print(f"[bold green]Normalized[/bold green] {len(changes)} headings in {file}")


@app.command("generate-bibliography")
def generate_bibliography_cmd(
    review_file: Path = typer.Argument(..., help="Review markdown file to update"),
    bib_file: Path = typer.Argument(..., help="BibTeX file containing references"),
) -> None:
    stats = generate_bibliography_apa(review_file, bib_file)
    console.print(
        f"[bold green]Updated[/bold green] references in {review_file} "
        f"(matched {stats['matched']}/{stats['total']} entries)"
    )


@app.command("scaffold-agents")
def scaffold_agents_cmd(
    root: Path = typer.Option(Path("."), help="Project root where provider folders are generated"),
    overwrite: bool = typer.Option(
        True, help="Overwrite existing agent-pack files if they already exist"
    ),
) -> None:
    written = scaffold_agent_pack(root.resolve(), overwrite=overwrite)
    console.print(f"[bold green]Agent pack ready[/bold green] ({len(written)} files updated)")
    for path in written:
        console.print(f"- {path}")


@app.command("search-openalex")
def search_openalex_cmd(
    query: str = typer.Argument(..., help="Search query"),
    out: Path | None = typer.Option(None, help="Optional JSON output path"),
    from_year: int | None = typer.Option(None),
    to_year: int | None = typer.Option(None),
    limit: int = typer.Option(25, min=1, max=200),
) -> None:
    env = load_env()
    payload = search_openalex(
        query, email=env.openalex_email, from_year=from_year, to_year=to_year, limit=limit
    )
    write_json(out, payload)


@app.command("search-s2")
def search_s2_cmd(
    query: str = typer.Argument(..., help="Search query"),
    out: Path | None = typer.Option(None, help="Optional JSON output path"),
    from_year: int | None = typer.Option(None),
    to_year: int | None = typer.Option(None),
    limit: int = typer.Option(25, min=1, max=100),
) -> None:
    env = load_env()
    payload = search_semantic_scholar(
        query,
        api_key=env.semantic_scholar_api_key,
        from_year=from_year,
        to_year=to_year,
        limit=limit,
    )
    write_json(out, payload)


@app.command("search-crossref")
def search_crossref_cmd(
    query: str = typer.Argument(..., help="Search query"),
    out: Path | None = typer.Option(None, help="Optional JSON output path"),
    from_year: int | None = typer.Option(None),
    to_year: int | None = typer.Option(None),
    limit: int = typer.Option(25, min=1, max=100),
) -> None:
    payload = search_crossref(query, from_year=from_year, to_year=to_year, limit=limit)
    write_json(out, payload)


@app.command("search-portfolio")
def search_portfolio_cmd(
    topic: str = typer.Argument(..., help="Main research topic"),
    description: str = typer.Option("", help="Optional scope/context"),
    out: Path | None = typer.Option(None, help="Optional JSON output path"),
    from_year: int | None = typer.Option(None),
    to_year: int | None = typer.Option(None),
    limit: int = typer.Option(80, min=20, max=300),
) -> None:
    env = load_env()
    payload = search_portfolio(
        topic,
        description=description,
        openalex_email=env.openalex_email,
        s2_api_key=env.semantic_scholar_api_key,
        from_year=from_year,
        to_year=to_year,
        limit=limit,
    )
    write_json(out, payload)


@app.command("verify-paper")
def verify_paper_cmd(
    out: Path | None = typer.Option(None, help="Optional JSON output path"),
    doi: str | None = typer.Option(None, help="DOI to verify"),
    title: str | None = typer.Option(None, help="Title query fallback"),
    author: str | None = typer.Option(None, help="Author query fallback"),
    year: int | None = typer.Option(None, help="Year query fallback"),
) -> None:
    payload = verify_paper(doi=doi, title=title, author=author, year=year)
    write_json(out, payload)


@app.command("s2-citations")
def s2_citations_cmd(
    paper_id: str = typer.Argument(..., help="Semantic Scholar paper id or DOI:..."),
    out: Path | None = typer.Option(None, help="Optional JSON output path"),
    mode: str = typer.Option("both", help="both | references | citations"),
    influential_only: bool = typer.Option(False, help="Only influential citation edges"),
    limit: int = typer.Option(50, min=1, max=500),
) -> None:
    env = load_env()
    payload = s2_citations(
        paper_id,
        api_key=env.semantic_scholar_api_key,
        mode=mode,
        influential_only=influential_only,
        limit=limit,
    )
    write_json(out, payload)


@app.command("s2-recommend")
def s2_recommend_cmd(
    positive_ids: list[str] = typer.Argument(..., help="Seed paper IDs"),
    out: Path | None = typer.Option(None, help="Optional JSON output path"),
    limit: int = typer.Option(20, min=1, max=200),
) -> None:
    env = load_env()
    payload = s2_recommend(positive_ids, api_key=env.semantic_scholar_api_key, limit=limit)
    write_json(out, payload)


@app.command("enrich-bibliography")
def enrich_bibliography_cmd(
    bib_file: Path = typer.Argument(..., help="BibTeX file to enrich in-place"),
) -> None:
    env = load_env()
    stats = enrich_bibliography(
        bib_file,
        openalex_email=env.openalex_email,
        s2_api_key=env.semantic_scholar_api_key,
    )
    console.print(
        f"[bold green]Enriched[/bold green] {bib_file} "
        f"(entries={stats['entries']}, abstracts={stats['enriched']}, incomplete={stats['incomplete']})"
    )


if __name__ == "__main__":
    app()
