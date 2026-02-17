from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mgmtlit.models import Paper
from mgmtlit.net import cached_get_json
from mgmtlit.sources.base import PaperSource


class OpenAlexSource(PaperSource):
    name = "openalex"

    def __init__(self, email: str | None = None, timeout: float = 25.0) -> None:
        self.email = email
        self.client = httpx.Client(timeout=timeout)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def _get(self, params: dict[str, str]) -> dict:
        headers = {}
        if self.email:
            headers["User-Agent"] = f"mgmtlit/0.1 ({self.email})"
        return cached_get_json(
            self.client,
            "https://api.openalex.org/works",
            params=params,
            headers=headers,
            ttl_seconds=6 * 60 * 60,
            min_interval_sec=0.25,
        )

    @staticmethod
    def _abstract_from_inverted(index: dict[str, list[int]] | None) -> str | None:
        if not index:
            return None
        pos_map: dict[int, str] = {}
        for token, poss in index.items():
            for pos in poss:
                pos_map[pos] = token
        if not pos_map:
            return None
        return " ".join(pos_map[k] for k in sorted(pos_map))

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
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")

        params = {
            "search": query,
            "per-page": str(min(max_results, 200)),
            "sort": "cited_by_count:desc",
        }
        if filters:
            params["filter"] = ",".join(filters)

        payload = self._get(params)
        out: list[Paper] = []
        for item in payload.get("results", []):
            out.append(
                Paper(
                    source=self.name,
                    paper_id=item.get("id", ""),
                    title=item.get("title") or "Untitled",
                    authors=[a.get("author", {}).get("display_name", "") for a in item.get("authorships", []) if a.get("author")],
                    year=item.get("publication_year"),
                    venue=(item.get("primary_location") or {}).get("source", {}).get("display_name"),
                    doi=(item.get("doi") or "").replace("https://doi.org/", "") or None,
                    url=item.get("primary_location", {}).get("landing_page_url"),
                    abstract=self._abstract_from_inverted(item.get("abstract_inverted_index")),
                    citation_count=item.get("cited_by_count"),
                    fields=[c.get("display_name", "") for c in item.get("concepts", [])[:5]],
                )
            )
        return out
