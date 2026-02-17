from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mgmtlit.models import Paper
from mgmtlit.net import cached_get_json
from mgmtlit.sources.base import PaperSource


class SemanticScholarSource(PaperSource):
    name = "semantic_scholar"

    def __init__(self, api_key: str | None = None, timeout: float = 25.0) -> None:
        self.api_key = api_key
        self.client = httpx.Client(timeout=timeout)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def _get(self, params: dict[str, str]) -> dict:
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return cached_get_json(
            self.client,
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params=params,
            headers=headers,
            ttl_seconds=2 * 60 * 60,
            min_interval_sec=0.35,
        )

    def search(
        self,
        query: str,
        *,
        from_year: int | None = None,
        to_year: int | None = None,
        max_results: int = 50,
    ) -> list[Paper]:
        fields = (
            "paperId,title,abstract,year,venue,url,citationCount,authors,externalIds,fieldsOfStudy"
        )
        params = {
            "query": query,
            "fields": fields,
            "limit": str(min(max_results, 100)),
            "sort": "citationCount:desc",
        }
        if from_year or to_year:
            low = str(from_year or 1900)
            high = str(to_year or 2100)
            params["year"] = f"{low}-{high}"

        payload = self._get(params)
        out: list[Paper] = []
        for item in payload.get("data", []):
            doi = (item.get("externalIds") or {}).get("DOI")
            out.append(
                Paper(
                    source=self.name,
                    paper_id=item.get("paperId", ""),
                    title=item.get("title") or "Untitled",
                    authors=[a.get("name", "") for a in item.get("authors", [])],
                    year=item.get("year"),
                    venue=item.get("venue"),
                    doi=doi,
                    url=item.get("url"),
                    abstract=item.get("abstract"),
                    citation_count=item.get("citationCount"),
                    fields=item.get("fieldsOfStudy") or [],
                )
            )
        return out
