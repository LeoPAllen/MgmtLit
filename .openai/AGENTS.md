# OpenAI Agent Runbook

Use this file as the top-level policy prompt when running MgmtLit in OpenAI/Codex environments.

## Orchestration order
1. `literature-review-planner`
2. `domain-literature-researcher` (parallel by domain)
3. `synthesis-planner`
4. `synthesis-writer` (parallel by section)

Load agent prompts from `.openai/agents/`.
Honor file contracts from `agentic/conventions.md`.
