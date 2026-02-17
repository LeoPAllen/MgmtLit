from mgmtlit.orchestration import (
    ClaudeCodeOrchestrationEngine,
    GeminiOrchestrationEngine,
    NullOrchestrationEngine,
    OpenAIOrchestrationEngine,
    create_orchestration_engine,
)


def test_create_orchestration_engine_provider_mapping():
    assert isinstance(create_orchestration_engine("openai"), OpenAIOrchestrationEngine)
    assert isinstance(create_orchestration_engine("gemini"), GeminiOrchestrationEngine)
    assert isinstance(create_orchestration_engine("claude_code"), ClaudeCodeOrchestrationEngine)
    assert isinstance(create_orchestration_engine("none"), NullOrchestrationEngine)
