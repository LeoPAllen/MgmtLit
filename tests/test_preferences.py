from mgmtlit.agents import RunInputs, _preference_adjustment
from mgmtlit.models import Paper


def _inputs() -> RunInputs:
    return RunInputs(
        topic="algorithmic management",
        description="",
        max_papers=80,
        from_year=None,
        to_year=None,
        include_terms=[],
        openalex_email=None,
        semantic_scholar_api_key=None,
        core_api_key=None,
        prefer_terms=[],
        avoid_terms=[],
        prefer_venues=[],
        avoid_venues=[],
        prefer_sources=[],
        avoid_sources=[],
        soft_restriction_strength=1.0,
    )


def _paper() -> Paper:
    return Paper(
        source="semantic_scholar",
        paper_id="1",
        title="Algorithmic management and worker autonomy",
        authors=["A B"],
        year=2022,
        venue="Management Science",
        doi=None,
        url=None,
        abstract="Paper studies productivity and control in platform work.",
        citation_count=10,
        fields=["management", "platform"],
    )


def test_preference_adjustment_rewards_preferred_signals():
    inputs = _inputs()
    inputs.prefer_terms = ["worker autonomy"]
    inputs.prefer_venues = ["management science"]
    inputs.prefer_sources = ["semantic_scholar"]
    score = _preference_adjustment(_paper(), inputs)
    assert score > 0


def test_preference_adjustment_penalizes_avoided_signals():
    inputs = _inputs()
    inputs.avoid_terms = ["platform work"]
    inputs.avoid_venues = ["management science"]
    inputs.avoid_sources = ["semantic_scholar"]
    score = _preference_adjustment(_paper(), inputs)
    assert score < 0
