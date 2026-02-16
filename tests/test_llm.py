import httpx
import pytest

from mgmtlit.llm import GeminiBackend, NullBackend, _coerce_json, create_backend


def test_create_backend_openai_without_key_falls_back_to_null():
    backend = create_backend(
        "openai",
        openai_api_key=None,
        openai_model="gpt-5-mini",
        claude_command="claude",
        claude_model="sonnet",
        gemini_api_key=None,
        gemini_model="gemini-2.0-flash",
    )
    assert isinstance(backend, NullBackend)


def test_create_backend_none_returns_null():
    backend = create_backend(
        "none",
        openai_api_key="x",
        openai_model="gpt-5-mini",
        claude_command="claude",
        claude_model="sonnet",
        gemini_api_key="x",
        gemini_model="gemini-2.0-flash",
    )
    assert isinstance(backend, NullBackend)


def test_coerce_json_parses_fenced_output():
    text = "```json\n{\"queries\":[\"a\", \"b\"]}\n```"
    out = _coerce_json(text)
    assert out["queries"] == ["a", "b"]


def test_create_backend_gemini_requires_key():
    backend = create_backend(
        "gemini",
        openai_api_key=None,
        openai_model="gpt-5-mini",
        claude_command="claude",
        claude_model="sonnet",
        gemini_api_key=None,
        gemini_model="gemini-2.0-flash",
    )
    assert isinstance(backend, NullBackend)


def test_create_backend_gemini_with_key():
    backend = create_backend(
        "gemini",
        openai_api_key=None,
        openai_model="gpt-5-mini",
        claude_command="claude",
        claude_model="sonnet",
        gemini_api_key="test-key",
        gemini_model="gemini-2.0-flash",
    )
    assert isinstance(backend, GeminiBackend)


def test_gemini_uses_header_for_api_key_not_query_param():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.query == b""
        assert request.headers.get("x-goog-api-key") == "test-key"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": '{"ok": true}'}]}},
                ]
            },
            request=request,
        )

    backend = GeminiBackend(api_key="test-key", max_retries=1)
    backend.client = httpx.Client(transport=httpx.MockTransport(handler))

    out = backend.ask_text({"task": "test"})
    assert out == '{"ok": true}'


def test_gemini_429_raises_actionable_error_message():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"message": "Resource has been exhausted"}},
            request=request,
        )

    backend = GeminiBackend(api_key="test-key", max_retries=1)
    backend.client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="HTTP 429"):
        backend.ask_text({"task": "test"})
