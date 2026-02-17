---
name: literature-review
description: Orchestrates the full literature review workflow using specialized agents.
---

# Literature Review Skill

Use this as the top-level orchestrator in main context.

## Workflow
1. Run `literature-review-planner` and write `intermediate_files/lit-review-plan.md`
2. Run `domain-literature-researcher` in parallel for all domains to produce `literature-domain-*.bib`
3. Run `synthesis-planner` and write `intermediate_files/synthesis-outline.md`
4. Run `synthesis-writer` in parallel by section to produce `synthesis-section-*.md`
5. Assemble final outputs with `mgmtlit assemble` and `mgmtlit dedupe-bib`

Track progress in `intermediate_files/task-progress.md`.
