# MgmtLit

`mgmtlit` is an AI-assisted literature review builder for scholars in management, organizations, and information systems. It is inspired by PhilLit's pipeline design, adapted for business school research domains.

## Informal notes from the developer:

- This tool is an almost purely vibe-coded work in progress.
- There are serious ethical and practical considerations related to its use.
- If you happen to use it, please use it responsibly and feel free to share feedback :) 

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

## Quickstart (minimal)

1. Set one LLM backend.
2. Run one review command.

```bash
cat > .env << 'EOF'
LLM_BACKEND=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
EOF

mgmtlit review \
  "How does algorithmic management affect worker autonomy and performance?" \
  --description "Focus on platform and hybrid organizations since 2015"
```

## Configuration

Create `.env` in project root.

### Required

- `LLM_BACKEND`
  - one of: `openai`, `gemini`, `claude_code`, `none`

### Required by selected backend

- if `LLM_BACKEND=openai`:
  - `OPENAI_API_KEY`
  - optional: `OPENAI_MODEL` (default `gpt-5-mini`)
- if `LLM_BACKEND=gemini`:
  - `GEMINI_API_KEY`
  - optional: `GEMINI_MODEL` (default `gemini-2.0-flash`)
- if `LLM_BACKEND=claude_code`:
  - Claude Code CLI installed and authenticated
  - optional: `CLAUDE_CODE_CMD` (default `claude`)
  - optional: `CLAUDE_MODEL` (default `sonnet`)

### Optional retrieval keys

- `OPENALEX_EMAIL` (recommended, improves OpenAlex compliance)
- `SEMANTIC_SCHOLAR_API_KEY` (recommended for S2 throughput)
- `CORE_API_KEY` (only needed for `search-core` and CORE portfolio coverage)

### Full example `.env`

```bash
LLM_BACKEND=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
CLAUDE_MODEL=sonnet
CLAUDE_CODE_CMD=claude
OPENALEX_EMAIL=you@university.edu
SEMANTIC_SCHOLAR_API_KEY=
CORE_API_KEY=
```

## Main Command: `review`

### Standard run

```bash
mgmtlit review \
  "How does algorithmic management affect worker autonomy and performance?" \
  --description "Focus on platforms, frontline work, and hybrid organizations since 2015" \
  --max-papers 80 \
  --backend openai \
  --fail-on-llm-fallback \
  --resume \
  --output-dir reviews
```

### Soft epistemic steering (optional)

Use these when you want to nudge results toward your scholarly context without hard-filtering:

- `--prefer-term` / `--avoid-term`
- `--prefer-venue` / `--avoid-venue`
- `--prefer-source` / `--avoid-source`
- `--soft-restriction-strength` in `[0.0, 3.0]`
  - `0.0`: off
  - `1.0`: default soft steering
  - `2.0+`: stronger steering

```bash
mgmtlit review \
  "Algorithmic management and worker outcomes" \
  --backend openai \
  --prefer-term "field experiment" \
  --prefer-venue "Management Science" \
  --avoid-venue "medical" \
  --avoid-source arxiv \
  --soft-restriction-strength 1.2 \
  --max-papers 80
```

Supported source names for soft steering:
- `openalex`
- `semantic_scholar`
- `crossref`
- `core`
- `arxiv`
- `ssrn`
- `repec`

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

## Agent Pack Scaffold (optional)

Generate provider-specific agent files and hooks:

```bash
mgmtlit scaffold-agents --root .
```

This generates:
- `.claude/agents/*.md` plus `.claude/docs/` and `.claude/settings.json`
- `.claude/hooks/` validators (`bib_validator.py`, `metadata_validator.py`, `metadata_cleaner.py`, `validate_bib_write.py`, `subagent_stop_bib.sh`)
- `.openai/agents/*.md` plus `.openai/AGENTS.md`
- `.gemini/agents/*.md` plus `.gemini/GEMINI.md`
- `agentic/ARCHITECTURE.md`, `agentic/conventions.md`, `agentic/manifest.json`

Use `--no-overwrite` to preserve existing files.

## Boolean Flags (Important)

This CLI uses Typer boolean toggles. Do not pass `true`/`false` values.

- use `--resume` or `--no-resume`
- use `--fail-on-llm-fallback` or `--no-fail-on-llm-fallback`
- use `--overwrite` or `--no-overwrite`

## Research Utilities (optional)

Use these for targeted retrieval or debugging source coverage:

```bash
mgmtlit search-openalex "algorithmic management" --from-year 2018 --out oa.json
mgmtlit search-s2 "algorithmic management" --out s2.json
mgmtlit search-crossref "algorithmic management" --out cr.json
mgmtlit search-core "algorithmic management" --out core.json
mgmtlit search-ssrn "algorithmic management" --out ssrn.json
mgmtlit search-repec "algorithmic management" --out repec.json
mgmtlit search-portfolio "algorithmic management and worker outcomes" \
  --description "management, org science, economics, IS, and OM coverage" --out portfolio.json
mgmtlit verify-paper --doi 10.1177/0001839220977791 --out verify.json
mgmtlit s2-citations DOI:10.1177/0001839220977791 --mode both --out cites.json
mgmtlit s2-recommend PAPER_ID_1 PAPER_ID_2 --out recs.json
mgmtlit enrich-bibliography reviews/topic/intermediate_files/literature-domain-1.bib
```

`--out` is optional for search commands. If omitted, JSON is printed to stdout.

Provider-native orchestration engines are selected automatically by `--backend`:
- `openai` -> OpenAI-native orchestrator
- `gemini` -> Gemini-native orchestrator
- `claude_code` -> Claude-native orchestrator
- `none` -> deterministic orchestrator

## Additional Run Examples

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
2. Re-run with tighter terms/date windows and optional soft steering.
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
