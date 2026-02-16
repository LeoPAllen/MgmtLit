from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mgmtlit.models import Paper
from mgmtlit.sources.base import PaperSource


class CrossrefSource(PaperSource):
    name = "crossref"

    def __init__(self, timeout: float = 25.0) -> None:
        self.client = httpx.Client(timeout=timeout)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def _get(self, params: dict[str, str]) -> dict:
        resp = self.client.get("https://api.crossref.org/works", params=params)
        resp.raise_for_status()
        return resp.json()

    def search(
        self,
        query: str,
        *,
        from_year: int | None = None,
        to_year: int | None = None,
        max_results: int = 50,
    ) -> list[Paper]:
        filters: list[str] = []
        if from_year:
            filters.append(f"from-pub-date:{from_year}-01-01")
        if to_year:
            filters.append(f"until-pub-date:{to_year}-12-31")

        params = {
            "query": query,
            "rows": str(min(max_results, 100)),
            "sort": "is-referenced-by-count",
            "order": "desc",
        }
        if filters:
            params["filter"] = ",".join(filters)

        payload = self._get(params)
        out: list[Paper] = []
        for item in payload.get("message", {}).get("items", []):
            title = (item.get("title") or ["Untitled"])[0]
            author_names = []
            for author in item.get("author", []):
                given = author.get("given", "").strip()
                family = author.get("family", "").strip()
                name = (given + " " + family).strip()
                if name:
                    author_names.append(name)
            parts = item.get("published-print") or item.get("published-online") or {}
            date_parts = parts.get("date-parts", [[None]])
            year = date_parts[0][0] if date_parts and date_parts[0] else None
            out.append(
                Paper(
                    source=self.name,
                    paper_id=item.get("DOI", ""),
                    title=title,
                    authors=author_names,
                    year=year,
                    venue=(item.get("container-title") or [None])[0],
                    doi=item.get("DOI"),
                    url=(item.get("URL") or None),
                    abstract=item.get("abstract"),
                    citation_count=item.get("is-referenced-by-count"),
                    fields=[],
                )
            )
        return out
