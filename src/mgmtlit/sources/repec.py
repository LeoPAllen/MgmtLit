from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mgmtlit.models import Paper
from mgmtlit.net import cached_get_json
from mgmtlit.sources.base import PaperSource


class RePEcSource(PaperSource):
    name = "repec"

    def __init__(self, timeout: float = 25.0) -> None:
        self.client = httpx.Client(timeout=timeout)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def _get(self, params: dict[str, str]) -> dict:
        return cached_get_json(
            self.client,
            "https://api.crossref.org/works",
            params=params,
            headers=None,
            ttl_seconds=24 * 60 * 60,
            min_interval_sec=0.2,
        )

    def search(
        self,
        query: str,
        *,
        from_year: int | None = None,
        to_year: int | None = None,
        max_results: int = 50,
    ) -> list[Paper]:
        filters = ["type:posted-content"]
        if from_year:
            filters.append(f"from-pub-date:{from_year}-01-01")
        if to_year:
            filters.append(f"until-pub-date:{to_year}-12-31")
        params = {
            "query.bibliographic": f"RePEc {query}",
            "rows": str(min(max_results, 100)),
            "filter": ",".join(filters),
            "sort": "is-referenced-by-count",
            "order": "desc",
        }
        payload = self._get(params)
        out: list[Paper] = []
        for item in payload.get("message", {}).get("items", []):
            title = (item.get("title") or ["Untitled"])[0]
            url = str(item.get("URL") or "")
            container = ((item.get("container-title") or [None])[0] or "").strip()
            hay = f"{title} {url} {container}".lower()
            if "repec" not in hay and "econ" not in hay and "working paper" not in hay:
                continue
            authors = []
            for author in item.get("author", []):
                given = author.get("given", "").strip()
                family = author.get("family", "").strip()
                name = (given + " " + family).strip()
                if name:
                    authors.append(name)
            parts = item.get("published-print") or item.get("published-online") or {}
            date_parts = parts.get("date-parts", [[None]])
            year = date_parts[0][0] if date_parts and date_parts[0] else None
            out.append(
                Paper(
                    source=self.name,
                    paper_id=item.get("DOI") or url,
                    title=title,
                    authors=authors,
                    year=year,
                    venue=container or "RePEc working paper",
                    doi=item.get("DOI"),
                    url=url or None,
                    abstract=item.get("abstract"),
                    citation_count=item.get("is-referenced-by-count"),
                    fields=["working paper", "economics", "repec"],
                )
            )
        return out
