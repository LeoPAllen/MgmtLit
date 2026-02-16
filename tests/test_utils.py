from mgmtlit.models import Paper
from mgmtlit.utils import dedupe_papers, render_bibtex, slugify


def _paper(title: str, doi: str | None, cites: int, abstract: str = "x") -> Paper:
    return Paper(
        source="x",
        paper_id=title,
        title=title,
        authors=["Ada Lovelace"],
        year=2020,
        venue="Journal",
        doi=doi,
        url=None,
        abstract=abstract,
        citation_count=cites,
    )


def test_slugify():
    assert slugify("AI & Organizations: A Review!") == "ai-organizations-a-review"


def test_dedupe_prefers_more_cited():
    a = _paper("Test Paper", "10.1000/xyz", 10, "short")
    b = _paper("Test Paper", "10.1000/xyz", 50, "longer abstract")
    out = dedupe_papers([a, b])
    assert len(out) == 1
    assert out[0].citation_count == 50


def test_bibtex():
    papers = [_paper("Title", "10.1/abc", 5)]
    bib = render_bibtex(papers)
    assert "@article" in bib
    assert "doi = {10.1/abc}" in bib
