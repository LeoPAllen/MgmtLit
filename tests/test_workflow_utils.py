from mgmtlit.models import QueryPlan
from mgmtlit.utils import (
    render_lit_review_plan_md,
    render_references_markdown,
    render_task_progress,
    with_yaml_frontmatter,
)


class _Domain:
    def __init__(self, index: int, name: str):
        self.index = index
        self.name = name
        self.focus = f"Focus for {name}"
        self.key_questions = ["Q1", "Q2"]
        self.search_terms = ["t1", "t2"]


def test_render_task_progress_marks_completed():
    text = render_task_progress(
        topic="X",
        phases=["A", "B"],
        completed=["A"],
        current="B",
        note="n",
    )
    assert "- [x] A" in text
    assert "- [ ] B" in text


def test_render_lit_review_plan_contains_domains():
    plan = QueryPlan(topic="Topic", description="Desc", facets=[], subquestions=["Q"], keywords=["k"])
    text = render_lit_review_plan_md(plan, [_Domain(1, "D1")])
    assert "### Domain 1: D1" in text
    assert "**Search Terms**:" in text


def test_with_yaml_frontmatter_prefixes_document():
    out = with_yaml_frontmatter("Body", title="My Title")
    assert out.startswith("---\ntitle: My Title")
    assert "Body" in out


def test_render_references_markdown_has_heading():
    out = render_references_markdown([])
    assert out.startswith("## References")
