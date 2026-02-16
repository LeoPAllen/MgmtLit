from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from mgmtlit.models import Paper, QueryPlan


SYSTEM_PROMPT = (
    "You are a careful literature review assistant for management, organizations, "
    "and information systems. Never invent citations. Ground all claims in supplied abstracts."
)


class LLMClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def plan_query(self, topic: str, description: str, seed_terms: list[str]) -> QueryPlan:
        prompt = {
            "task": "Create literature review query plan",
            "topic": topic,
            "description": description,
            "seed_terms": seed_terms,
            "requirements": {
                "facets": "5-8 thematic facets",
                "subquestions": "5-8 specific research subquestions",
                "keywords": "20-30 search keywords/bigrams",
            },
            "output_json_schema": {
                "facets": ["..."],
                "subquestions": ["..."],
                "keywords": ["..."],
            },
        }
        content = self._ask_json(prompt)
        return QueryPlan(
            topic=topic,
            description=description,
            facets=content.get("facets", []),
            subquestions=content.get("subquestions", []),
            keywords=content.get("keywords", []),
        )

    def compose_review(
        self,
        plan: QueryPlan,
        papers: list[Paper],
        *,
        max_citations: int = 40,
    ) -> str:
        selected = papers[:max_citations]
        evidence = [
            {
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "venue": p.venue,
                "doi": p.doi,
                "url": p.url,
                "abstract": (p.abstract or "")[:1500],
                "citation_count": p.citation_count,
            }
            for p in selected
        ]

        prompt = {
            "task": "Write a structured scholarly literature review draft",
            "topic": plan.topic,
            "description": plan.description,
            "facets": plan.facets,
            "subquestions": plan.subquestions,
            "instructions": [
                "Use only supplied sources.",
                "If evidence is thin, say so explicitly.",
                "Use inline citations like (Author, Year).",
                "Include sections: Introduction, Theoretical Lenses, Empirical Findings, Methods Patterns, Gaps and Tensions, Future Research Agenda, Conclusion.",
                "Add a final section 'Reference Mapping' with bullet points mapping each major claim to source titles.",
            ],
            "evidence": evidence,
        }
        return self._ask_text(prompt)

    def _ask_text(self, payload: dict[str, Any]) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
            ],
        )
        return response.output_text.strip()

    def _ask_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = self._ask_text(payload)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Allow for fenced JSON responses.
            text = text.strip().strip("`")
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise
