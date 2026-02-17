# Agentic Architecture (Cross-Provider)

MgmtLit follows a PhilLit-style staged workflow with specialized roles and explicit artifacts.

## Workflow
1. planner -> `lit-review-plan.md`
2. domain researchers (parallel) -> `literature-domain-*.bib`
3. synthesis planner -> `synthesis-outline.md`
4. synthesis writers (parallel) -> `synthesis-section-*.md`
5. assembler -> `literature-review-final.md` + `literature-all.bib`

## Design pattern
- Multi-file-then-assemble
- Isolated worker contexts
- Explicit intermediate artifacts for resumability and auditability
- Deterministic file contracts between stages

## Provider parity strategy
Canonical prompts live in this repo and are rendered for:
- Claude Code: `.claude/agents/*.md`
- OpenAI/Codex-style workflows: `.openai/agents/*.md` + `.openai/AGENTS.md`
- Gemini workflows: `.gemini/agents/*.md` + `.gemini/GEMINI.md`
