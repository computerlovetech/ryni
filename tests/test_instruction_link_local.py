import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ryni.cli import app
from ryni.instruction_link import InstructionLink
from ryni.instruction_link_local import LocalInstructionLinkRepair


@pytest.mark.parametrize("kind", ["identical", "wrong", "broken", "loop"])
def test_fix_repairs_safe_cases_and_is_idempotent(tmp_path: Path, kind: str) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text("Instructions")
    other = tmp_path / "OTHER.md"
    other.write_text("Other instructions")
    claude = tmp_path / "CLAUDE.md"
    if kind == "identical":
        claude.write_bytes(agents.read_bytes())
    else:
        claude.symlink_to({"wrong": "OTHER.md", "broken": "missing", "loop": "CLAUDE.md"}[kind])
    arguments = ["check", str(claude), "--select", "AGENT001", "--fix", "--output-format", "json"]

    for _ in range(2):
        result = CliRunner().invoke(app, arguments)
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["findings"] == []
        assert claude.is_symlink()
        assert claude.readlink() == Path("AGENTS.md")
        assert agents.read_text() == "Instructions"
        assert other.read_text() == "Other instructions"
    assert not list(tmp_path.glob(".ryni-fix-*"))


@pytest.mark.parametrize("kind", ["different", "directory", "missing-target", "backlink"])
def test_fix_leaves_unsafe_cases_as_findings(tmp_path: Path, kind: str) -> None:
    agents = tmp_path / "AGENTS.md"
    claude = tmp_path / "CLAUDE.md"
    if kind == "missing-target":
        claude.symlink_to("AGENTS.md")
    elif kind == "backlink":
        claude.write_text("Preserve me")
        agents.symlink_to("CLAUDE.md")
    else:
        agents.write_text("Instructions")
        if kind == "directory":
            claude.mkdir()
            (claude / "keep").write_text("Preserve me")
        else:
            claude.write_text("Preserve me")

    result = CliRunner().invoke(app, ["check", str(claude), "--select", "AGENT001", "--fix"])

    assert result.exit_code == 1, result.output
    assert "AGENT001" in result.output
    if kind == "missing-target":
        assert claude.readlink() == Path("AGENTS.md")
        assert not agents.exists()
    elif kind == "directory":
        assert (claude / "keep").read_text() == "Preserve me"
    else:
        assert not claude.is_symlink()
        assert claude.read_text() == "Preserve me"


def test_failed_replacement_preserves_original_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claude = tmp_path / "CLAUDE.md"
    claude.symlink_to("missing")
    (tmp_path / "AGENTS.md").write_text("Instructions")

    def fail(self: Path, target: Path) -> Path:
        raise PermissionError("Cannot replace")

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(PermissionError, match="Cannot replace"):
        LocalInstructionLinkRepair().repair(InstructionLink(path=claude))
    assert claude.readlink() == Path("missing")
    assert not list(tmp_path.glob(".ryni-fix-*"))
