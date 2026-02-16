# MgmtLit

`mgmtlit` is an AI-assisted literature review builder for scholars in management, organizations, and information systems. It is inspired by PhilLit's pipeline design, adapted for business school research domains.

## What it does

Given a research question, `mgmtlit` can:

1. Decompose the question into search facets relevant to management/organizations/IS.
2. Retrieve candidate papers from OpenAlex, Crossref, and Semantic Scholar.
3. Deduplicate and score papers by relevance and citation impact.
4. Build an evidence table with metadata and abstracts.
5. Draft a structured literature review and export a BibTeX file.

Outputs are written to `reviews/<slug>/`:

- `plan.json`: generated sub-questions and search facets
- `papers.json`: ranked paper candidates with metadata
- `evidence_table.md`: compact evidence matrix
- `review.md`: generated literature review draft
- `references.bib`: BibTeX entries for included sources

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
OPENALEX_EMAIL=you@university.edu
SEMANTIC_SCHOLAR_API_KEY=optional_but_recommended
```

Notes:
- `OPENAI_API_KEY` is optional. Without it, the tool uses deterministic fallback prompts and template-based synthesis.
- `OPENALEX_EMAIL` is optional but recommended by OpenAlex for polite pool usage.

## Usage

```bash
mgmtlit review \
  "How does algorithmic management affect worker autonomy and performance?" \
  --description "Focus on platforms, frontline work, and hybrid organizations since 2015" \
  --max-papers 80 \
  --output-dir reviews
```

Optional filters:

```bash
mgmtlit review "IT ambidexterity and digital transformation" \
  --from-year 2010 \
  --to-year 2026 \
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
