from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(slots=True)
class EnvConfig:
    openai_api_key: str | None
    openai_model: str
    openalex_email: str | None
    semantic_scholar_api_key: str | None


def load_env() -> EnvConfig:
    load_dotenv()
    return EnvConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openalex_email=os.getenv("OPENALEX_EMAIL"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
    )
