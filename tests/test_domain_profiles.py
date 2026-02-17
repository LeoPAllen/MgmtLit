from mgmtlit.domain_profiles import coverage_anchor_terms, query_variants, venue_boost


def test_query_variants_include_topic_and_are_bounded():
    variants = query_variants(
        "algorithmic management",
        "worker autonomy",
        ["platform labor", "control", "operations"],
    )
    assert variants
    assert "algorithmic management" in variants[0]
    assert len(variants) <= 8


def test_coverage_anchor_terms_contains_cross_discipline_terms():
    anchors = coverage_anchor_terms("digital transformation", "organization change", ["it capability"])
    joined = " ".join(anchors)
    assert "economics" in joined
    assert "information systems" in joined
    assert "operations management" in joined


def test_venue_boost_detects_priority_journals():
    assert venue_boost("Organization Science") > 0
    assert venue_boost("MIS Quarterly") > 0
    assert venue_boost("Random Venue") == 0
