from mgmtlit.llm import NullBackend, _coerce_json, create_backend


def test_create_backend_openai_without_key_falls_back_to_null():
    backend = create_backend(
        "openai",
        openai_api_key=None,
        openai_model="gpt-5-mini",
        claude_command="claude",
        claude_model="sonnet",
    )
    assert isinstance(backend, NullBackend)


def test_create_backend_none_returns_null():
    backend = create_backend(
        "none",
        openai_api_key="x",
        openai_model="gpt-5-mini",
        claude_command="claude",
        claude_model="sonnet",
    )
    assert isinstance(backend, NullBackend)


def test_coerce_json_parses_fenced_output():
    text = "```json\n{\"queries\":[\"a\", \"b\"]}\n```"
    out = _coerce_json(text)
    assert out["queries"] == ["a", "b"]
