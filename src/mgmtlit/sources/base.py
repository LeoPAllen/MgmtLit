from __future__ import annotations

from abc import ABC, abstractmethod

from mgmtlit.models import Paper


class PaperSource(ABC):
    name: str

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        from_year: int | None = None,
        to_year: int | None = None,
        max_results: int = 50,
    ) -> list[Paper]:
        raise NotImplementedError
