from pathlib import Path

from mgmtlit.postprocess import (
    assemble_review,
    dedupe_bib,
    generate_bibliography_apa,
    normalize_headings,
)


def test_assemble_review_natural_sort_and_frontmatter(tmp_path: Path):
    s2 = tmp_path / "synthesis-section-2.md"
    s10 = tmp_path / "synthesis-section-10.md"
    s2.write_text("## B\n\nBody B\n", encoding="utf-8")
    s10.write_text("## C\n\nBody C\n", encoding="utf-8")
    out = tmp_path / "final.md"
    assemble_review(out, [s10, s2], title="T", review_date="2026-02-16")
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---\ntitle: T\ndate: 2026-02-16\n---")
    assert text.find("## B") < text.find("## C")


def test_dedupe_bib_merges_by_doi(tmp_path: Path):
    a = tmp_path / "a.bib"
    b = tmp_path / "b.bib"
    out = tmp_path / "out.bib"
    a.write_text(
        "@article{key1,\n  title={A},\n  doi={10.1000/x},\n  keywords={x, Low},\n}\n",
        encoding="utf-8",
    )
    b.write_text(
        "@article{key2,\n  title={A2},\n  doi={https://doi.org/10.1000/x},\n  keywords={x, High},\n abstract={Long enough abstract text here.}\n}\n",
        encoding="utf-8",
    )
    duplicates = dedupe_bib([a, b], out)
    text = out.read_text(encoding="utf-8")
    assert len(duplicates) == 1
    assert text.count("@article{") == 1
    assert "10.1000/x" in text


def test_normalize_headings_applies_numbering():
    content = "\n".join(
        [
            "---",
            "title: X",
            "---",
            "",
            "## Introduction",
            "### 9.9 Legacy",
            "## Debates",
            "### Subsection 2.3 Prior Work",
            "## Conclusion",
        ]
    )
    normalized, changes = normalize_headings(content)
    assert "## Introduction" in normalized
    assert "## Section 1: Debates" in normalized
    assert "### 1.1 Prior Work" in normalized
    assert changes


def test_generate_bibliography_apa_appends_references(tmp_path: Path):
    review = tmp_path / "review.md"
    bib = tmp_path / "all.bib"
    review.write_text(
        "## Introduction\n\nAs argued by Smith (2020), this is important.\n",
        encoding="utf-8",
    )
    bib.write_text(
        "@article{smith2020,\n"
        "  author = {Smith, John and Doe, Jane},\n"
        "  year = {2020},\n"
        "  title = {A study on organizations},\n"
        "  journal = {Management Journal},\n"
        "  volume = {12},\n"
        "  number = {3},\n"
        "  pages = {10-20},\n"
        "  doi = {10.1000/xyz}\n"
        "}\n",
        encoding="utf-8",
    )
    stats = generate_bibliography_apa(review, bib)
    text = review.read_text(encoding="utf-8")
    assert stats["matched"] == 1
    assert "## References" in text
    assert "Smith, J., & Doe, J. (2020)." in text
    assert "https://doi.org/10.1000/xyz" in text


def test_generate_bibliography_apa_replaces_existing_section(tmp_path: Path):
    review = tmp_path / "review.md"
    bib = tmp_path / "all.bib"
    review.write_text(
        "Body text citing Lee (2021).\n\n## References\n\nold entry\n",
        encoding="utf-8",
    )
    bib.write_text(
        "@article{lee2021,\n"
        "  author = {Lee, Alex},\n"
        "  year = {2021},\n"
        "  title = {Digital work design},\n"
        "  journal = {Org Science}\n"
        "}\n",
        encoding="utf-8",
    )
    generate_bibliography_apa(review, bib)
    text = review.read_text(encoding="utf-8")
    assert "old entry" not in text
    assert "Lee, A. (2021)." in text
