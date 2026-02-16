from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class QueryPlan:
    topic: str
    description: str
    facets: list[str]
    subquestions: list[str]
    keywords: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "description": self.description,
            "facets": self.facets,
            "subquestions": self.subquestions,
            "keywords": self.keywords,
        }


@dataclass(slots=True)
class Paper:
    source: str
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    venue: str | None
    doi: str | None
    url: str | None
    abstract: str | None
    citation_count: int | None
    fields: list[str] = field(default_factory=list)
    relevance_score: float = 0.0

    def canonical_key(self) -> str:
        if self.doi:
            return self.doi.lower().strip()
        return " ".join(self.title.lower().split())

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "url": self.url,
            "abstract": self.abstract,
            "citation_count": self.citation_count,
            "fields": self.fields,
            "relevance_score": round(self.relevance_score, 3),
        }
