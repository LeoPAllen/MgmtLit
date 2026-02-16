from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from typing import Any

SYSTEM_PROMPT = (
    "You are a careful literature review assistant for management, organizations, "
    "and information systems. Never invent citations. Ground all claims in supplied abstracts."
)


class LLMBackend(ABC):
    name: str

    @abstractmethod
    def ask_text(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError

    def ask_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = self.ask_text(payload)
        return _coerce_json(text)


class OpenAIBackend(LLMBackend):
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for openai backend.") from exc
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def ask_text(self, payload: dict[str, Any]) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
            ],
        )
        return response.output_text.strip()


class ClaudeCodeBackend(LLMBackend):
    name = "claude_code"

    def __init__(self, command: str = "claude", model: str = "sonnet") -> None:
        self.command = command
        self.model = model

    def ask_text(self, payload: dict[str, Any]) -> str:
        prompt = "\n\n".join(
            [
                SYSTEM_PROMPT,
                "Return valid JSON only when the task asks for JSON.",
                json.dumps(payload, ensure_ascii=True),
            ]
        )
        cmd = [self.command, "-p", prompt]
        if self.model:
            cmd.extend(["--model", self.model])
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"Claude Code command failed: {msg}")
        text = (proc.stdout or "").strip()
        if not text:
            raise RuntimeError("Claude Code command returned empty output.")
        return text


class NullBackend(LLMBackend):
    name = "none"

    def ask_text(self, payload: dict[str, Any]) -> str:
        raise RuntimeError("No LLM backend configured.")


def create_backend(
    backend_name: str,
    *,
    openai_api_key: str | None,
    openai_model: str,
    claude_command: str,
    claude_model: str,
) -> LLMBackend:
    normalized = backend_name.strip().lower()
    if normalized == "openai":
        if not openai_api_key:
            return NullBackend()
        return OpenAIBackend(api_key=openai_api_key, model=openai_model)
    if normalized == "claude_code":
        return ClaudeCodeBackend(command=claude_command, model=claude_model)
    return NullBackend()


def _coerce_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        trimmed = text.strip().strip("`")
        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        data = json.loads(trimmed[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Model did not return a JSON object.")
    return data
