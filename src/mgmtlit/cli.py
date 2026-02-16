from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from mgmtlit.config import load_env
from mgmtlit.pipeline import RunConfig, run_review
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


if __name__ == "__main__":
    app()
