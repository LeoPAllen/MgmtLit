from __future__ import annotations

from dataclasses import dataclass

from mgmtlit.agents import (
    AgentState,
    DomainResearchAgent,
    PlannerAgent,
    SynthesisPlannerAgent,
    SynthesisWriterAgent,
)
from mgmtlit.llm import LLMBackend


@dataclass(slots=True)
class OrchestrationEngine:
    name: str
    provider: str

    def run_planner(self, state: AgentState, backend: LLMBackend) -> None:
        PlannerAgent().run(state, backend)

    def run_domain_research(self, state: AgentState, backend: LLMBackend) -> None:
        DomainResearchAgent().run(state, backend)

    def run_synthesis_planner(self, state: AgentState, backend: LLMBackend) -> None:
        SynthesisPlannerAgent().run(state, backend)

    def run_synthesis_writer(self, state: AgentState, backend: LLMBackend) -> None:
        SynthesisWriterAgent().run(state, backend)


class OpenAIOrchestrationEngine(OrchestrationEngine):
    def __init__(self) -> None:
        super().__init__(name="openai-native", provider="openai")


class GeminiOrchestrationEngine(OrchestrationEngine):
    def __init__(self) -> None:
        super().__init__(name="gemini-native", provider="gemini")


class ClaudeCodeOrchestrationEngine(OrchestrationEngine):
    def __init__(self) -> None:
        super().__init__(name="claude-native", provider="claude")


class NullOrchestrationEngine(OrchestrationEngine):
    def __init__(self) -> None:
        super().__init__(name="deterministic", provider="none")


def create_orchestration_engine(backend_name: str) -> OrchestrationEngine:
    normalized = backend_name.strip().lower()
    if normalized == "openai":
        return OpenAIOrchestrationEngine()
    if normalized == "gemini":
        return GeminiOrchestrationEngine()
    if normalized == "claude_code":
        return ClaudeCodeOrchestrationEngine()
    return NullOrchestrationEngine()
