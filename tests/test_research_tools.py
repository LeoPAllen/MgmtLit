from pathlib import Path

from mgmtlit.research_tools import enrich_bibliography


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
