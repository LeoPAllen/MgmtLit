---
name: management-research
description: Structured retrieval and verification utilities for management literature.
---

# Management Research Skill

Prefer structured API calls over free-form web search.

## Script Equivalents (via CLI)
- `mgmtlit search-openalex "query" --out results.json`
- `mgmtlit search-s2 "query" --out results.json`
- `mgmtlit search-crossref "query" --out results.json`
- `mgmtlit verify-paper --doi 10.xxxx/xxxx --out verify.json`
- `mgmtlit s2-citations PAPER_ID --mode both --out citations.json`
- `mgmtlit s2-recommend PAPER_ID_1 PAPER_ID_2 --out recommend.json`
- `mgmtlit enrich-bibliography reviews/project/intermediate_files/literature-domain-1.bib`

## Rules
- Never fabricate metadata.
- Save evidence JSON under `intermediate_files/json/`.
- Prefer DOI-backed metadata when available.
