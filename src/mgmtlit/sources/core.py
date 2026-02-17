from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mgmtlit.models import Paper
from mgmtlit.net import cached_get_json
from mgmtlit.sources.base import PaperSource


class CoreSource(PaperSource):
    name = "core"

    def __init__(self, api_key: str | None = None, timeout: float = 25.0) -> None:
        self.api_key = api_key
        self.client = httpx.Client(timeout=timeout)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(2))
    def _get(self, params: dict[str, str]) -> dict:
        if not self.api_key:
            raise RuntimeError("CORE_API_KEY not configured.")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        return cached_get_json(
            self.client,
            "https://api.core.ac.uk/v3/search/works",
            params=params,
            headers=headers,
            ttl_seconds=24 * 60 * 60,
            min_interval_sec=0.4,
        )

    def search(
        self,
        query: str,
        *,
        from_year: int | None = None,
        to_year: int | None = None,
        max_results: int = 50,
    ) -> list[Paper]:
        params = {"q": query, "limit": str(min(max_results, 100))}
        if from_year:
            params["fromPublishedDate"] = f"{from_year}-01-01"
        if to_year:
            params["toPublishedDate"] = f"{to_year}-12-31"
        payload = self._get(params)
        out: list[Paper] = []
        for item in payload.get("results", []):
            authors = [a.get("name", "").strip() for a in item.get("authors", []) if isinstance(a, dict)]
            out.append(
                Paper(
                    source=self.name,
                    paper_id=str(item.get("id", "")),
                    title=str(item.get("title") or "Untitled"),
                    authors=[a for a in authors if a],
                    year=item.get("yearPublished"),
                    venue=item.get("publisher") or item.get("journals"),
                    doi=item.get("doi"),
                    url=item.get("downloadUrl") or item.get("sourceFulltextUrls", [None])[0],
                    abstract=item.get("abstract"),
                    citation_count=item.get("citationCount"),
                    fields=[],
                )
            )
        return out
