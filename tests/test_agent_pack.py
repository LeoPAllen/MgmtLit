from pathlib import Path

from mgmtlit.agent_pack import AGENT_SPECS, scaffold_agent_pack


def test_scaffold_agent_pack_writes_provider_files(tmp_path: Path):
    written = scaffold_agent_pack(tmp_path)
    assert written

    for spec in AGENT_SPECS:
        assert (tmp_path / ".claude" / "agents" / f"{spec.name}.md").exists()
        assert (tmp_path / ".openai" / "agents" / f"{spec.name}.md").exists()
        assert (tmp_path / ".gemini" / "agents" / f"{spec.name}.md").exists()

    assert (tmp_path / ".openai" / "AGENTS.md").exists()
    assert (tmp_path / ".gemini" / "GEMINI.md").exists()
    assert (tmp_path / ".claude" / "skills" / "literature-review" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "management-research" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "hooks" / "bib_validator.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "metadata_validator.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "metadata_cleaner.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "validate_bib_write.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "subagent_stop_bib.sh").exists()
    assert (tmp_path / "agentic" / "ARCHITECTURE.md").exists()
    assert (tmp_path / "agentic" / "manifest.json").exists()


def test_scaffold_agent_pack_respects_overwrite_false(tmp_path: Path):
    first = scaffold_agent_pack(tmp_path)
    assert first

    marker = tmp_path / ".openai" / "AGENTS.md"
    marker.write_text("custom\n", encoding="utf-8")
    second = scaffold_agent_pack(tmp_path, overwrite=False)

    assert marker.read_text(encoding="utf-8") == "custom\n"
    assert marker not in second
