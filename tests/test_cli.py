import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ryni.cli import app

runner = CliRunner()
VALID = "---\nname: example\ndescription: Use when testing.\n---\n# Example\n"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# Example\n", "Start SKILL.md"),
        ("---\nname: example\n", "Close YAML frontmatter"),
        ("---\nname: [\n---\n", "valid YAML"),
        ("---\n- example\n---\n", "YAML mapping"),
        ("---\nname: example\n---\n", "'description'"),
        ("---\nname: 123\ndescription: ' '\n---\n", "'name'"),
    ],
)
def test_invalid_frontmatter(tmp_path: Path, text: str, expected: str):
    skill = tmp_path / "SKILL.md"
    skill.write_text(text)
    result = runner.invoke(app, ["check", str(skill)])
    assert result.exit_code == 1
    assert "SKILL001" in result.output
    assert expected in result.output


def test_discovery_deduplicates_and_excludes_dependencies(tmp_path: Path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(VALID)
    installed = tmp_path / "node_modules" / "skills"
    installed.mkdir(parents=True)
    (installed / "SKILL.md").write_text("invalid")
    (tmp_path / "README.md").write_text("not a skill")
    result = runner.invoke(
        app, ["check", str(tmp_path), str(skill), "--select", "SKILL001", "--output-format", "json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "checked_files": [str(skill)],
        "findings": [],
        "errors": [],
        "pending_reviews": [],
    }


@pytest.mark.parametrize("directory", [".agents", ".claude", ".codex", ".github"])
def test_discovery_checks_harness_skills(tmp_path: Path, directory: str):
    skill = tmp_path / directory / "skills" / "example" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("invalid")
    result = runner.invoke(
        app, ["check", str(tmp_path), "--select", "SKILL001", "--output-format", "json"]
    )
    assert result.exit_code == 1
    report = json.loads(result.output)
    assert report["checked_files"] == [str(skill)]
    assert [finding["path"] for finding in report["findings"]] == [str(skill)]


def test_missing_path_preserves_other_findings(tmp_path: Path):
    skill = tmp_path / "SKILL.md"
    skill.write_text("invalid")
    result = runner.invoke(
        app,
        [
            "check",
            str(skill),
            str(tmp_path / "missing"),
            "--select",
            "SKILL001",
            "--output-format",
            "json",
        ],
    )
    assert result.exit_code == 2
    report = json.loads(result.output)
    assert len(report["findings"]) == 1
    assert len(report["errors"]) == 1


def test_invalid_utf8_is_execution_error(tmp_path: Path):
    skill = tmp_path / "SKILL.md"
    skill.write_bytes(b"\xff")
    result = runner.invoke(app, ["check", str(skill)])
    assert result.exit_code == 2
    assert "Cannot check" in result.output


def test_valid_multiline_description_and_bom(tmp_path: Path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "\ufeff---\r\nname: example\r\ndescription: >\r\n  Use when testing.\r\n---\r\n"
    )
    result = runner.invoke(app, ["check", str(skill), "--select", "SKILL001"])
    assert result.exit_code == 0


@pytest.mark.parametrize("arguments", [["rule", "UNKNOWN"], ["check", ".", "--select", "UNKNOWN"]])
def test_unknown_rule_is_usage_error(arguments: list[str]):
    assert runner.invoke(app, arguments).exit_code == 2


def test_rule_discovery_and_help():
    assert "check" in runner.invoke(app, ["--help"]).output
    assert "SKILL001" in runner.invoke(app, ["rule"]).output
    result = runner.invoke(app, ["rule", "SKILL001"])
    assert result.exit_code == 0
    assert "Example:" in result.output
