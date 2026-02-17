from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

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

    def ask_agent_text(self, agent_name: str, payload: dict[str, Any]) -> str:
        del agent_name
        return self.ask_text(payload)

    def ask_agent_json(self, agent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        text = self.ask_agent_text(agent_name, payload)
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
        return self._ask(payload, None)

    def ask_agent_text(self, agent_name: str, payload: dict[str, Any]) -> str:
        return self._ask(payload, _load_agent_prompt("openai", agent_name))

    def _ask(self, payload: dict[str, Any], agent_prompt: str | None) -> str:
        system = SYSTEM_PROMPT if not agent_prompt else f"{SYSTEM_PROMPT}\n\n{agent_prompt}"
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system},
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
        return self._ask(payload, None)

    def ask_agent_text(self, agent_name: str, payload: dict[str, Any]) -> str:
        return self._ask(payload, _load_agent_prompt("claude", agent_name))

    def _ask(self, payload: dict[str, Any], agent_prompt: str | None) -> str:
        extra = agent_prompt or ""
        prompt = "\n\n".join(
            [
                SYSTEM_PROMPT,
                extra,
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


class GeminiBackend(LLMBackend):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        max_retries: int = 3,
        retry_backoff_sec: float = 1.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=60.0)
        self.max_retries = max(max_retries, 1)
        self.retry_backoff_sec = max(retry_backoff_sec, 0.0)

    def ask_text(self, payload: dict[str, Any]) -> str:
        return self._ask(payload, None)

    def ask_agent_text(self, agent_name: str, payload: dict[str, Any]) -> str:
        return self._ask(payload, _load_agent_prompt("gemini", agent_name))

    def _ask(self, payload: dict[str, Any], agent_prompt: str | None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        system = SYSTEM_PROMPT if not agent_prompt else f"{SYSTEM_PROMPT}\n\n{agent_prompt}"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": "Return valid JSON only when the task asks for JSON."},
                        {"text": json.dumps(payload, ensure_ascii=True)},
                    ],
                }
            ],
            "generationConfig": {"temperature": 0.2},
        }
        for attempt in range(self.max_retries):
            try:
                resp = self.client.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json=body,
                )
                resp.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code == 429
                    and attempt < self.max_retries - 1
                ):
                    retry_after = _parse_retry_after(exc.response)
                    if retry_after is None:
                        retry_after = self.retry_backoff_sec * (2**attempt)
                    time.sleep(retry_after)
                    continue
                raise RuntimeError(_format_gemini_http_error(exc)) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Gemini request failed: {exc}") from exc

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")
        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
        if not text:
            raise RuntimeError("Gemini returned empty output.")
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
    gemini_api_key: str | None,
    gemini_model: str,
) -> LLMBackend:
    normalized = backend_name.strip().lower()
    if normalized == "openai":
        if not openai_api_key:
            return NullBackend()
        return OpenAIBackend(api_key=openai_api_key, model=openai_model)
    if normalized == "claude_code":
        return ClaudeCodeBackend(command=claude_command, model=claude_model)
    if normalized == "gemini":
        if not gemini_api_key:
            return NullBackend()
        return GeminiBackend(api_key=gemini_api_key, model=gemini_model)
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


def _parse_retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None


def _format_gemini_http_error(exc: httpx.HTTPStatusError) -> str:
    status_code = exc.response.status_code
    message = f"Gemini API request failed with HTTP {status_code}."
    if status_code == 429:
        message += (
            " Rate limit or quota exceeded; check Gemini API quotas/billing "
            "and reduce request rate."
        )

    try:
        payload = exc.response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        error_message = payload.get("error", {}).get("message")
        if isinstance(error_message, str) and error_message.strip():
            message += f" Details: {error_message.strip()}"
    return message


def _load_agent_prompt(provider: str, agent_name: str) -> str | None:
    mapping = {"openai": ".openai", "gemini": ".gemini", "claude": ".claude"}
    folder = mapping.get(provider)
    if not folder:
        return None
    path = Path.cwd() / folder / "agents" / f"{agent_name}.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
