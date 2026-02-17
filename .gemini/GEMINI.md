# Gemini Agent Runbook

Use this file as the top-level workflow prompt for Gemini-based runs.

## Orchestration order
1. `literature-review-planner`
2. `domain-literature-researcher` in parallel
3. `synthesis-planner`
4. `synthesis-writer` in parallel

Agent prompts live in `.gemini/agents/`.
File contracts and formatting rules are defined in `agentic/conventions.md`.
