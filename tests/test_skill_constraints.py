import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ryni.cli import app
from ryni.engine import check
from ryni.rules import BUILTINS


def skill_file(tmp_path: Path, name="example", description="Use when testing.") -> Path:
    path = tmp_path / "example" / "SKILL.md"
    path.parent.mkdir(exist_ok=True)
    metadata = yaml.safe_dump({"name": name, "description": description}, allow_unicode=True)
    path.write_text(f"---\n{metadata}---\n\nInstructions.\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "name,valid",
    [
        ("a", True),
        ("a" * 64, True),
        ("a" * 65, False),
        ("review-2", True),
        ("rýni", True),
        ("ry\u0301ni", True),
        ("技能", True),
        ("Review", False),
        ("review skill", False),
        (" review", False),
        ("review ", False),
        ("review_skill", False),
        ("review/skill", False),
        ("-review", False),
        ("review-", False),
        ("review--skill", False),
        ("review🙂", False),
    ],
)
def test_skill_name_constraints(tmp_path, name, valid):
    path = skill_file(tmp_path, name=name)
    result = CliRunner().invoke(
        app, ["check", str(path), "--select", "SKILL002", "--output-format", "json"]
    )
    assert result.exit_code == (0 if valid else 1)
    report = json.loads(result.output)
    assert [finding["rule_id"] for finding in report["findings"]] == ([] if valid else ["SKILL002"])


@pytest.mark.parametrize("length,valid", [(1, True), (1024, True), (1025, False)])
def test_description_counts_characters_not_bytes(tmp_path, length, valid):
    path = skill_file(tmp_path, description="ø" * length)
    result = check([path], BUILTINS)
    assert result.exit_code == (0 if valid else 1)
    assert [finding.rule_id for finding in result.findings] == ([] if valid else ["SKILL004"])


def test_description_counts_parsed_multiline_value(tmp_path):
    path = skill_file(tmp_path)
    path.write_text("---\nname: example\ndescription: >-\n  " + "x" * 1022 + "\n  y\n---\n")
    assert check([path], BUILTINS).exit_code == 0  # Folded space makes 1024 characters.
    path.write_text("---\nname: example\ndescription: |\n  " + "x" * 1022 + "\n  y\n---\n")
    assert [finding.rule_id for finding in check([path], BUILTINS).findings] == ["SKILL004"]


@pytest.mark.parametrize("target", ["absolute", "relative", "basename"])
def test_directory_match_for_all_path_forms(tmp_path, monkeypatch, target):
    path = skill_file(tmp_path, name="other")
    if target == "relative":
        monkeypatch.chdir(tmp_path)
        path = Path("example/SKILL.md")
    elif target == "basename":
        monkeypatch.chdir(path.parent)
        path = Path("SKILL.md")
    result = check([path], BUILTINS)
    assert [finding.rule_id for finding in result.findings] == ["SKILL003"]
    assert "'other'" in result.findings[0].message
    assert "'example'" in result.findings[0].message
    assert result.findings[0].path == str(path)


def test_directory_match_supports_unicode_normalization(tmp_path):
    path = skill_file(tmp_path, name="ry\u0301ni")
    directory = path.parent.rename(tmp_path / "rýni")
    assert check([directory / "SKILL.md"], BUILTINS).exit_code == 0


def test_directory_match_uses_symlink_location(tmp_path):
    source = tmp_path / "shared.md"
    source.write_text("---\nname: example\ndescription: Example\n---\n")
    directory = tmp_path / "example"
    directory.mkdir()
    path = directory / "SKILL.md"
    path.symlink_to(source)
    assert check([path], BUILTINS).exit_code == 0


@pytest.mark.parametrize(
    "content",
    [
        "# No frontmatter\n",
        "---\nname: example\n",
        "---\nname: [\n---\n",
        "---\n- item\n---\n",
        "---\nname: example\n---\n",
        "---\ndescription: Example\n---\n",
        "---\nname: 123\ndescription: []\n---\n",
        "---\nname: ''\ndescription: ' '\n---\n",
    ],
)
def test_structural_failures_do_not_cascade(tmp_path, content):
    path = skill_file(tmp_path)
    path.write_text(content)
    result = check([path], BUILTINS)
    assert result.exit_code == 1
    assert {finding.rule_id for finding in result.findings} == {"SKILL001"}
    assert result.errors == []


def test_default_cli_runs_all_constraints_and_allows_extensions(tmp_path):
    path = skill_file(tmp_path, name="BAD NAME", description="x" * 1025)
    path.write_text(path.read_text().replace("---\n\n", "disable-model-invocation: true\n---\n\n"))
    result = CliRunner().invoke(app, ["check", str(tmp_path), "--output-format", "json"])
    assert result.exit_code == 1
    report = json.loads(result.output)
    assert [finding["rule_id"] for finding in report["findings"]] == [
        "SKILL002",
        "SKILL003",
        "SKILL004",
    ]
    assert report["checked_files"] == [str(path)]
    path.write_text(
        "\ufeff---\r\nname: example\r\ndescription: >\r\n  Example\r\n"
        "disable-model-invocation: true\r\n---\r\n"
    )
    assert check([path], BUILTINS).exit_code == 0


def test_baseline_does_not_require_or_validate_agents_md(tmp_path):
    (tmp_path / "AGENTS.md").write_text("")
    result = check([tmp_path], BUILTINS)
    assert result.exit_code == 0
    assert result.checked_files == []
