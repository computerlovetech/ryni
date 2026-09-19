import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ryni.cli import app

runner = CliRunner()


@pytest.mark.parametrize("absolute", [False, True])
def test_valid_symlink_is_checked_even_with_target_in_scope(tmp_path: Path, absolute: bool):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("Instructions")
    claude = tmp_path / "CLAUDE.md"
    claude.symlink_to(agents if absolute else "AGENTS.md")
    result = runner.invoke(
        app, ["check", str(tmp_path), "--select", "AGENT001", "--output-format", "json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["checked_files"] == [str(claude)]


@pytest.mark.parametrize("kind", ["regular", "wrong", "broken", "directory", "loop"])
def test_invalid_claude_file(tmp_path: Path, kind: str):
    claude = tmp_path / "CLAUDE.md"
    if kind == "regular":
        claude.write_text("Instructions")
    elif kind == "directory":
        claude.mkdir()
    elif kind == "loop":
        claude.symlink_to("CLAUDE.md")
    elif kind == "wrong":
        (tmp_path / "OTHER.md").write_text("Instructions")
        claude.symlink_to("OTHER.md")
    else:
        claude.symlink_to("AGENTS.md")
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1
    assert "AGENT001" in result.output


def test_explicit_broken_link_is_a_finding(tmp_path: Path):
    claude = tmp_path / "CLAUDE.md"
    claude.symlink_to("AGENTS.md")
    assert runner.invoke(app, ["check", str(claude)]).exit_code == 1


def test_agents_without_claude_is_allowed(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("Instructions")
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 findings" in result.output
