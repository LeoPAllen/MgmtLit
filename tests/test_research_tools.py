from pathlib import Path

from mgmtlit.models import Paper
from mgmtlit.research_tools import enrich_bibliography, search_portfolio


def test_enrich_bibliography_adds_abstract(tmp_path: Path):
    bib = tmp_path / "x.bib"
    bib.write_text(
        """@article{smith2020,
  author = {Smith, Jane},
  title = {A Paper},
  year = {2020},
  journal = {J},
}
""",
        encoding="utf-8",
    )

    def resolver(**_: object):
        return {"status": "ok", "abstract": "This is abstract text.", "source": "s2"}

    stats = enrich_bibliography(bib, resolver=resolver)
    text = bib.read_text(encoding="utf-8")
    assert stats["enriched"] == 1
    assert "abstract = {This is abstract text.}" in text
    assert "abstract_source = {s2}" in text


def test_enrich_bibliography_marks_incomplete(tmp_path: Path):
    bib = tmp_path / "x.bib"
    bib.write_text(
        """@article{smith2020,
  author = {Smith, Jane},
  title = {A Paper},
  year = {2020},
  journal = {J},
  keywords = {management, High},
}
""",
        encoding="utf-8",
    )

    def resolver(**_: object):
        return {"status": "not_found"}

    stats = enrich_bibliography(bib, resolver=resolver)
    text = bib.read_text(encoding="utf-8")
    assert stats["incomplete"] == 1
    assert "INCOMPLETE" in text
    assert "no-abstract" in text


def test_search_portfolio_integration_with_mocked_sources(monkeypatch):
    class StubSource:
        name = "stub"

        def __init__(self, *args, **kwargs):
            pass

        def search(self, query, **kwargs):
            return [
                Paper(
                    source="stub",
                    paper_id=f"id-{query}",
                    title="Digital transformation and productivity",
                    authors=["A B"],
                    year=2022,
                    venue="Management Science",
                    doi=None,
                    url=None,
                    abstract="X",
                    citation_count=50,
                    fields=["management"],
                )
            ]

    monkeypatch.setattr("mgmtlit.research_tools.OpenAlexSource", StubSource)
    monkeypatch.setattr("mgmtlit.research_tools.SemanticScholarSource", StubSource)
    monkeypatch.setattr("mgmtlit.research_tools.CrossrefSource", StubSource)
    monkeypatch.setattr("mgmtlit.research_tools.CoreSource", StubSource)
    monkeypatch.setattr("mgmtlit.research_tools.RePEcSource", StubSource)
    monkeypatch.setattr("mgmtlit.research_tools.SSRNSource", StubSource)
    monkeypatch.setattr("mgmtlit.research_tools.ArxivSource", StubSource)

    payload = search_portfolio("digital transformation", description="firm outcomes", limit=30)
    assert payload["status"] == "ok"
    assert payload["results"]
    assert "source_counts" in payload
