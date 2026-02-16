from mgmtlit.agents import DomainPlan, _domain_query, _looks_sane_paper, _sanitize_paper
from mgmtlit.models import Paper


def _paper(title: str, abstract: str = "a") -> Paper:
    return Paper(
        source="x",
        paper_id="1",
        title=title,
        authors=["A B"],
        year=2020,
        venue="V",
        doi=None,
        url=None,
        abstract=abstract,
        citation_count=0,
        fields=[],
    )


def test_domain_query_is_bounded_and_compact():
    domain = DomainPlan(
        index=1,
        name="Theoretical mechanisms and contingencies",
        focus="Very long focus text that should not dominate query building.",
        key_questions=[],
        search_terms=["platform", "attention", "diffusion", "community", "elaboration"],
    )
    query = _domain_query(
        "How do cultural elements design attributes become popular and then get elaborate in digital fields",
        domain,
    )
    assert len(query) <= 220
    assert "the " not in query


def test_sanitize_and_filter_rejects_catalog_dump_title():
    p = _paper(
        "Volume 2, Issue 4 Authors: X Download PDF View Description Creative Commons License "
        "Article: 1 DOI Link: http://x",
        abstract="ok",
    )
    p = _sanitize_paper(p)
    assert _looks_sane_paper(p) is False
