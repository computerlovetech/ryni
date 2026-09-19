from pathlib import Path

from typer.testing import CliRunner

from ryni.cli import app
from ryni.rules.skill_frontmatter import evaluate


def test_install_creates_valid_skill_and_is_idempotent(tmp_path: Path):
    directory = tmp_path / "skills"
    runner = CliRunner()
    result = runner.invoke(app, ["skill", "install", str(directory)])
    assert result.exit_code == 0, result.output
    target = directory / "ryni-check" / "SKILL.md"
    assert evaluate(target) == []
    original = target.stat().st_mtime_ns
    result = runner.invoke(app, ["skill", "install", str(directory)])
    assert result.exit_code == 0
    assert target.stat().st_mtime_ns == original


def test_default_install_is_local(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert CliRunner().invoke(app, ["skill", "install"]).exit_code == 0
    assert (tmp_path / ".agents/skills/ryni-check/SKILL.md").is_file()


def test_install_preserves_custom_skill(tmp_path: Path):
    target = tmp_path / "ryni-check" / "SKILL.md"
    target.parent.mkdir()
    target.write_text("custom instructions")
    result = CliRunner().invoke(app, ["skill", "install", str(tmp_path)])
    assert result.exit_code == 2
    assert target.read_text() == "custom instructions"


def test_install_rejects_skill_symlink_without_touching_target(tmp_path: Path):
    external = tmp_path / "custom"
    external.mkdir()
    (tmp_path / "ryni-check").symlink_to(external, target_is_directory=True)
    result = CliRunner().invoke(app, ["skill", "install", str(tmp_path)])
    assert result.exit_code == 2
    assert list(external.iterdir()) == []


def test_install_handles_unwritable_destination(tmp_path: Path):
    blocker = tmp_path / "file"
    blocker.touch()
    result = CliRunner().invoke(app, ["skill", "install", str(blocker)])
    assert result.exit_code == 2
    assert "Cannot install skill" in result.output
