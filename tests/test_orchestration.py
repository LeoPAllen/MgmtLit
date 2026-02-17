from mgmtlit.orchestration import (
    ClaudeCodeOrchestrationEngine,
    GeminiOrchestrationEngine,
    NullOrchestrationEngine,
    OpenAIOrchestrationEngine,
    create_orchestration_engine,
)
from mgmtlit.agents import AgentState, RunInputs
from mgmtlit.llm import LLMBackend


def test_create_orchestration_engine_provider_mapping():
    assert isinstance(create_orchestration_engine("openai"), OpenAIOrchestrationEngine)
    assert isinstance(create_orchestration_engine("gemini"), GeminiOrchestrationEngine)
    assert isinstance(create_orchestration_engine("claude_code"), ClaudeCodeOrchestrationEngine)
    assert isinstance(create_orchestration_engine("none"), NullOrchestrationEngine)


class _Backend(LLMBackend):
    name = "test"

    def __init__(self):
        self.agents = []

    def ask_text(self, payload):
        raise RuntimeError("unused")

    def ask_agent_text(self, agent_name, payload):
        self.agents.append(agent_name)
        if agent_name == "literature-review-planner":
            return (
                '{"facets":["f1"],"subquestions":["q1"],"keywords":["k1"],'
                '"domains":[{"name":"d1","focus":"x","key_questions":["q"],"search_terms":["t"]}]}'
            )
        return '{"sections":[{"heading":"## Introduction","purpose":"x","word_target":300,"domain_indices":[1]}],"notes_for_writers":"n"}'


def test_orchestration_engine_invokes_agent_named_prompts():
    engine = OpenAIOrchestrationEngine()
    backend = _Backend()
    state = AgentState(
        inputs=RunInputs(
            topic="t",
            description="d",
            max_papers=20,
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
    )
    engine.run_planner(state, backend)
    state.papers = []
    engine.run_synthesis_planner(state, backend)
    assert "literature-review-planner" in backend.agents
    assert "synthesis-planner" in backend.agents
