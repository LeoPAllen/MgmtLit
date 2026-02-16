from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from mgmtlit.config import load_env
from mgmtlit.pipeline import RunConfig, run_review

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
        openai_api_key=env.openai_api_key,
        openai_model=env.openai_model,
    )

    out = run_review(config)
    console.print(f"[bold green]Done.[/bold green] Files written to: {out}")


if __name__ == "__main__":
    app()
