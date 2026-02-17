# MgmtLit

`mgmtlit` is an AI-assisted literature review builder for scholars in management, organizations, and information systems. It is inspired by PhilLit's pipeline design, adapted for business school research domains.

## What it does

Given a research question, `mgmtlit` now runs a PhilLit-style 6-phase workflow:

1. Verify run state and initialize progress tracking.
2. Decompose the topic into domains (`literature-review-planner`).
3. Research each domain and produce per-domain BibTeX (`domain-literature-researcher`).
4. Build a synthesis outline (`synthesis-planner`).
5. Draft section files (`synthesis-writer`).
6. Assemble final review and bibliography artifacts.

Outputs are written to `reviews/<slug>/`:

- `literature-review-final.md`: assembled review with YAML frontmatter and references
- `literature-all.bib`: aggregated bibliography
- `review.md`: assembled section draft without frontmatter
- `plan.json`: generated sub-questions and search facets
- `papers.json`: ranked paper candidates with metadata
- `agent_trace.json`: per-agent status + fallback information
- `evidence_table.md`: compact evidence matrix
- `references.bib`: BibTeX entries for included sources
- `intermediate_files/task-progress.md`: resumable phase tracker
- `intermediate_files/lit-review-plan.md`: domain decomposition
- `intermediate_files/literature-domain-*.bib`: per-domain bibliographies
- `intermediate_files/synthesis-outline.md`: section blueprint
- `intermediate_files/synthesis-section-*.md`: drafted sections
- `intermediate_files/json/*.json`: per-domain evidence snapshots

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure

Create `.env`:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
LLM_BACKEND=openai
CLAUDE_MODEL=sonnet
CLAUDE_CODE_CMD=claude
OPENALEX_EMAIL=you@university.edu
SEMANTIC_SCHOLAR_API_KEY=optional_but_recommended
```

Notes:
- `LLM_BACKEND` can be `openai`, `gemini`, `claude_code`, or `none`.
- `OPENAI_API_KEY` is only required when `LLM_BACKEND=openai`.
- `GEMINI_API_KEY` is only required when `LLM_BACKEND=gemini`.
- For `LLM_BACKEND=claude_code`, install/configure the Claude Code CLI and optionally override `CLAUDE_CODE_CMD`.
- `OPENALEX_EMAIL` is optional but recommended by OpenAlex for polite pool usage.
- Default behavior is fail-fast if both planner and synthesis fall back from LLM (`--fail-on-llm-fallback true`), to avoid silently producing low-quality output.

## Usage

```bash
mgmtlit review \
  "How does algorithmic management affect worker autonomy and performance?" \
  --description "Focus on platforms, frontline work, and hybrid organizations since 2015" \
  --max-papers 80 \
  --backend openai \
  --fail-on-llm-fallback true \
  --resume true \
  --output-dir reviews
```

PhilLit-style postprocessing commands:

```bash
mgmtlit assemble reviews/topic/literature-review-final.md \
  reviews/topic/intermediate_files/synthesis-section-*.md \
  --title "Literature Review: Topic"

mgmtlit dedupe-bib reviews/topic/literature-all.bib \
  reviews/topic/intermediate_files/literature-domain-1.bib \
  reviews/topic/intermediate_files/literature-domain-2.bib

mgmtlit normalize-headings reviews/topic/literature-review-final.md

mgmtlit generate-bibliography \
  reviews/topic/literature-review-final.md \
  reviews/topic/literature-all.bib
```

`generate-bibliography` appends or replaces `## References` in **APA style** based on in-text citations.

Cross-provider agent-pack scaffold (PhilLit-style role decomposition):

```bash
mgmtlit scaffold-agents --root .
```

This generates:
- `.claude/agents/*.md` plus `.claude/docs/` and `.claude/settings.json`
- `.claude/hooks/` validators (`bib_validator.py`, `metadata_validator.py`, `metadata_cleaner.py`, `validate_bib_write.py`, `subagent_stop_bib.sh`)
- `.openai/agents/*.md` plus `.openai/AGENTS.md`
- `.gemini/agents/*.md` plus `.gemini/GEMINI.md`
- `agentic/ARCHITECTURE.md`, `agentic/conventions.md`, `agentic/manifest.json`

Use `--overwrite false` to preserve existing files.

Structured research utilities (PhilLit-style script equivalents):

```bash
mgmtlit search-openalex "algorithmic management" --from-year 2018 --out oa.json
mgmtlit search-s2 "algorithmic management" --out s2.json
mgmtlit search-crossref "algorithmic management" --out cr.json
mgmtlit search-portfolio "algorithmic management and worker outcomes" \
  --description "management, org science, economics, IS, and OM coverage" --out portfolio.json
mgmtlit verify-paper --doi 10.1177/0001839220977791 --out verify.json
mgmtlit s2-citations DOI:10.1177/0001839220977791 --mode both --out cites.json
mgmtlit s2-recommend PAPER_ID_1 PAPER_ID_2 --out recs.json
mgmtlit enrich-bibliography reviews/topic/intermediate_files/literature-domain-1.bib
```

Provider-native orchestration engines are selected automatically by `--backend`:
- `openai` -> OpenAI-native orchestrator
- `gemini` -> Gemini-native orchestrator
- `claude_code` -> Claude-native orchestrator
- `none` -> deterministic orchestrator

Optional filters:

```bash
mgmtlit review "IT ambidexterity and digital transformation" \
  --from-year 2010 \
  --to-year 2026 \
  --backend gemini \
  --gemini-model gemini-2.0-flash \
  --include-term "dynamic capabilities" \
  --include-term "organizational learning"

mgmtlit review "IT ambidexterity and digital transformation" \
  --from-year 2010 \
  --to-year 2026 \
  --backend claude_code \
  --claude-model sonnet \
  --include-term "dynamic capabilities" \
  --include-term "organizational learning"
```

## Domain coverage

Default domain lexicon includes:

- Management strategy, innovation, entrepreneurship
- Organization theory, institutional theory, routines, culture
- Information systems, digital transformation, platform ecosystems, AI governance
- Operations and supply chains
- OB/HR, labor process, leadership, teams
- Corporate governance, CSR, sustainability

You can add custom include terms via `--include-term`.

## Suggested workflow for scholars

1. Run once with broad settings and inspect `papers.json`.
2. Re-run with tighter include terms and date windows.
3. Manually verify key papers before submission-quality writing.
4. Use `review.md` as a first draft, not a final manuscript.

## Why this is "similar" to PhilLit

PhilLit's architecture emphasizes decomposition, retrieval, evidence tracking, and synthesis. `mgmtlit` preserves that end-to-end shape but reorients topic lexicons, search heuristics, and section templates toward management scholarship.

## Development

```bash
pip install -e .[dev]
pytest
ruff check .
```
