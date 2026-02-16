from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:  # type: ignore[override]
        return False


@dataclass(slots=True)
class EnvConfig:
    openai_api_key: str | None
    openai_model: str
    gemini_api_key: str | None
    gemini_model: str
    llm_backend: str
    claude_model: str
    claude_command: str
    openalex_email: str | None
    semantic_scholar_api_key: str | None


def load_env() -> EnvConfig:
    load_dotenv()
    return EnvConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        llm_backend=os.getenv("LLM_BACKEND", "openai"),
        claude_model=os.getenv("CLAUDE_MODEL", "sonnet"),
        claude_command=os.getenv("CLAUDE_CODE_CMD", "claude"),
        openalex_email=os.getenv("OPENALEX_EMAIL"),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
    )
