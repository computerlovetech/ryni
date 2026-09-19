import json
from pathlib import Path, PurePosixPath

import pytest
from typer.testing import CliRunner

from ryni.cli import app
from ryni.markdown_repository_local import LocalMarkdownRepository
from ryni.skill_repository import RepositoryRoot


def write(root: Path, name: str, text: str = "# Example\n") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_discovery_includes_github_but_skips_dependencies_and_nested_repos(tmp_path: Path) -> None:
    for name in [
        "notes.md",
        "upper.MD",
        "long.markdown",
        ".github/notes.md",
        "node_modules/pkg/notes.md",
        ".venv/notes.md",
        ".git/notes.md",
        ".agents/skills/review/notes.md",
        ".claude/skills/review/notes.md",
        "nested/.git/HEAD",
        "nested/notes.md",
    ]:
        write(tmp_path, name)
    snapshot = LocalMarkdownRepository().inspect(RepositoryRoot(path=tmp_path))
    assert snapshot.files == tuple(
        map(PurePosixPath, [".github/notes.md", "long.markdown", "notes.md", "upper.MD"])
    )


def test_symlink_directories_are_not_traversed(tmp_path: Path) -> None:
    write(tmp_path, "docs/guide.md")
    (tmp_path / "linked").symlink_to("docs", target_is_directory=True)
    snapshot = LocalMarkdownRepository().inspect(RepositoryRoot(path=tmp_path))
    assert snapshot.files == (PurePosixPath("docs/guide.md"),)


def test_cli_loads_root_config_from_nested_path_and_does_not_fix(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    write(
        tmp_path,
        "ryni.toml",
        '[rules.markdown-location]\nadditional_allowed_names = ["OWNERS.md"]\nadditional_allowed_paths = ["content/**/*.md"]\n',
    )
    write(tmp_path, "OWNERS.md")
    write(tmp_path, "content/post.md")
    bad = write(tmp_path, "app/design.md")
    result = CliRunner().invoke(
        app, ["check", str(bad.parent), "--select", "DOC001", "--fix", "--output-format", "json"]
    )
    assert result.exit_code == 1, result.output
    report = json.loads(result.output)
    assert [finding["path"] for finding in report["findings"]] == [str(bad)]
    assert bad.read_text() == "# Example\n"
    assert report["errors"] == []


@pytest.mark.parametrize(
    "text",
    ["not toml", "[rules.markdown-location]\nadditional_allowed_names = 123", "[rules.typo]"],
)
def test_invalid_configuration_is_execution_error(tmp_path: Path, text: str) -> None:
    write(tmp_path, "ryni.toml", text)
    result = CliRunner().invoke(
        app, ["check", str(tmp_path), "--select", "DOC001", "--output-format", "json"]
    )
    assert result.exit_code == 2
    assert "ryni.toml" in json.loads(result.output)["errors"][0]


def test_location_exception_does_not_suppress_other_rules(tmp_path: Path) -> None:
    write(
        tmp_path, "ryni.toml", '[rules.markdown-location]\nadditional_allowed_paths = ["**/*.md"]\n'
    )
    write(tmp_path, "SKILL.md", "invalid")
    result = CliRunner().invoke(
        app, ["check", str(tmp_path), "--select", "DOC001,SKILL001", "--output-format", "json"]
    )
    assert result.exit_code == 1
    assert {finding["rule_id"] for finding in json.loads(result.output)["findings"]} == {"SKILL001"}
