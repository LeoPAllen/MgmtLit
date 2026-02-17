from __future__ import annotations

from datetime import datetime
from xml.etree import ElementTree as ET

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mgmtlit.models import Paper
from mgmtlit.net import cached_get_text
from mgmtlit.sources.base import PaperSource


class ArxivSource(PaperSource):
    name = "arxiv"

    def __init__(self, timeout: float = 25.0) -> None:
        self.client = httpx.Client(timeout=timeout)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
    def _get(self, params: dict[str, str]) -> str:
        return cached_get_text(
            self.client,
            "https://export.arxiv.org/api/query",
            params=params,
            headers=None,
            ttl_seconds=24 * 60 * 60,
            min_interval_sec=0.25,
        )

    def search(
        self,
        query: str,
        *,
        from_year: int | None = None,
        to_year: int | None = None,
        max_results: int = 50,
    ) -> list[Paper]:
        params = {
            "search_query": f"all:{query}",
            "start": "0",
            "max_results": str(min(max_results, 100)),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        xml = self._get(params)
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        out: list[Paper] = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()
            year: int | None = None
            if published:
                try:
                    year = datetime.fromisoformat(published.replace("Z", "+00:00")).year
                except ValueError:
                    year = None
            if from_year and year and year < from_year:
                continue
            if to_year and year and year > to_year:
                continue

            authors = [
                (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
                for a in entry.findall("atom:author", ns)
            ]
            paper_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
            url = ""
            for link in entry.findall("atom:link", ns):
                href = link.attrib.get("href")
                rel = link.attrib.get("rel", "")
                if href and (rel == "alternate" or not url):
                    url = href
            out.append(
                Paper(
                    source=self.name,
                    paper_id=paper_id,
                    title=title or "Untitled",
                    authors=[a for a in authors if a],
                    year=year,
                    venue="arXiv",
                    doi=None,
                    url=url or None,
                    abstract=summary or None,
                    citation_count=None,
                    fields=[],
                )
            )
        return out
