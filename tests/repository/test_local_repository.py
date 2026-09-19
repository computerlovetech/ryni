import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ryni.cli import app
from ryni.skill_repository import RepositoryRoot
from ryni.skill_repository_local import LocalSkillRepository

VALID = "---\nname: example\ndescription: Test skill.\n---\n# Example\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def _skill(root: Path, relative: str = "skills/category/example/SKILL.md") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(VALID)
    return path


def _lock(scope: Path, source: str = "./skills", source_type: str = "local") -> None:
    (scope / "skills-lock.json").write_text(
        json.dumps(
            {
                "version": 1,
                "skills": {
                    "example": {
                        "source": source,
                        "sourceType": source_type,
                        "computedHash": "a" * 64,
                    }
                },
            }
        )
    )


def _report(repo: Path, select: str) -> tuple[int, dict]:
    result = CliRunner().invoke(
        app, ["check", str(repo), "--select", select, "--output-format", "json"]
    )
    return result.exit_code, json.loads(result.output)


@pytest.mark.parametrize(
    "pattern", [".claude/", ".claude/skills/", "**/.claude/", "/.claude/skills/"]
)
def test_gitignore_accepts_parent_or_skills_directory_patterns(repo: Path, pattern: str) -> None:
    (repo / ".claude/skills").mkdir(parents=True)
    (repo / ".gitignore").write_text(pattern + "\n")
    code, report = _report(repo, "SKILL002")
    assert code == 0
    assert report["findings"] == []


@pytest.mark.parametrize("pattern", ["", ".claude/\n!.claude/\n", ".claude/skills/example/"])
def test_gitignore_rejects_missing_negated_or_partial_coverage(repo: Path, pattern: str) -> None:
    (repo / ".claude/skills/example").mkdir(parents=True)
    (repo / ".gitignore").write_text(pattern)
    code, report = _report(repo, "SKILL002")
    assert code == 1
    assert len(report["findings"]) == 1


def test_missing_gitignore_is_reported(repo: Path) -> None:
    (repo / ".claude").mkdir()
    code, report = _report(repo, "SKILL002")
    assert code == 1
    assert ".claude/skills" in report["findings"][0]["path"]


def test_info_exclude_does_not_replace_repository_gitignore(repo: Path) -> None:
    (repo / ".claude").mkdir()
    (repo / ".git/info/exclude").write_text(".claude/\n")
    assert _report(repo, "SKILL002")[0] == 1


def test_ignore_rule_reports_tracked_installed_skills(repo: Path) -> None:
    installed = _skill(repo, ".agents/skills/example/SKILL.md")
    subprocess.run(["git", "-C", str(repo), "add", str(installed)], check=True)
    (repo / ".gitignore").write_text(".agents/\n")
    code, report = _report(repo, "SKILL002")
    assert code == 1
    assert "tracked" in report["findings"][0]["message"]


def test_scoped_gitignore_can_cover_scoped_agents(repo: Path) -> None:
    scope = repo / "apps/api"
    (scope / ".claude").mkdir(parents=True)
    (scope / ".gitignore").write_text(".claude/\n")
    assert _report(repo, "SKILL002")[0] == 0


def test_location_scan_excludes_installed_skills_but_not_other_agent_content(repo: Path) -> None:
    _skill(repo)
    _skill(repo, "apps/api/skills/category/example/SKILL.md")
    _skill(repo, ".agents/skills/example/SKILL.md")
    _skill(repo, ".claude/skills/example/SKILL.md")
    _skill(repo, ".github/skills/example/SKILL.md")
    misplaced = _skill(repo, ".github/other/example/SKILL.md")
    code, report = _report(repo, "SKILL003")
    assert code == 1
    assert [finding["path"] for finding in report["findings"]] == [str(misplaced)]


def test_directory_symlinks_and_nested_repositories_are_not_scanned(
    repo: Path, tmp_path: Path
) -> None:
    other = repo / "external"
    other.mkdir()
    subprocess.run(["git", "init", "-q", str(other)], check=True)
    _skill(other, "misplaced/SKILL.md")
    (repo / "loop").symlink_to(repo, target_is_directory=True)
    assert _report(repo, "SKILL003")[0] == 0


def test_nested_source_uses_containing_scope_not_category(repo: Path) -> None:
    _skill(repo, "apps/api/skills/deep/category/example/SKILL.md")
    sources = LocalSkillRepository().layout(RepositoryRoot(path=repo)).sources
    assert sources[0].scope == repo / "apps/api"


@pytest.mark.parametrize("symlink", [True, False])
def test_local_install_accepts_copied_and_symlinked_skills(repo: Path, symlink: bool) -> None:
    source = _skill(repo)
    installed = repo / ".agents/skills/example"
    installed.parent.mkdir(parents=True)
    shutil.copytree(source.parent, installed)
    claude = repo / ".claude/skills/example"
    claude.parent.mkdir(parents=True)
    if symlink:
        claude.symlink_to("../../.agents/skills/example", target_is_directory=True)
    else:
        shutil.copytree(source.parent, claude)
    _lock(repo)
    assert _report(repo, "SKILL004")[0] == 0


def test_no_configured_agents_requires_no_installation(repo: Path) -> None:
    _skill(repo)
    (repo / ".github/workflows").mkdir(parents=True)
    assert _report(repo, "SKILL004")[0] == 0


def test_only_configured_agents_are_required(repo: Path) -> None:
    source = _skill(repo)
    shutil.copytree(source.parent, repo / ".agents/skills/example")
    _lock(repo)
    assert _report(repo, "SKILL004")[0] == 0


def test_missing_lockfile_reports_install_command(repo: Path) -> None:
    _skill(repo)
    (repo / ".claude").mkdir()
    code, report = _report(repo, "SKILL004")
    assert code == 1
    assert "npx skills" in report["findings"][0]["message"]


@pytest.mark.parametrize(
    "lock_contents", ["{", '{"version": 9, "skills": {}}', '{"version": 1, "skills": {}}']
)
def test_invalid_or_incomplete_lockfile_does_not_crash(repo: Path, lock_contents: str) -> None:
    _skill(repo)
    (repo / ".claude").mkdir()
    (repo / "skills-lock.json").write_text(lock_contents)
    code, report = _report(repo, "SKILL004")
    assert code == 1
    assert report["errors"] == []


@pytest.mark.parametrize("source,source_type", [("./elsewhere", "local"), ("owner/repo", "github")])
def test_lock_entry_must_reference_the_local_source(
    repo: Path, source: str, source_type: str
) -> None:
    _skill(repo)
    (repo / ".claude").mkdir()
    _lock(repo, source, source_type)
    code, report = _report(repo, "SKILL004")
    assert code == 1
    assert "local source" in report["findings"][0]["message"]


@pytest.mark.parametrize("state", ["missing", "broken", "stale"])
def test_lock_entry_alone_is_not_proof_of_installation(repo: Path, state: str) -> None:
    _skill(repo)
    target = repo / ".claude/skills/example"
    target.parent.mkdir(parents=True)
    if state == "broken":
        target.symlink_to("missing")
    elif state == "stale":
        target.mkdir()
        (target / "SKILL.md").write_text("old")
    _lock(repo)
    code, report = _report(repo, "SKILL004")
    assert code == 1
    assert len(report["findings"]) == 1


def test_scope_installation_does_not_use_root_lock_or_agents(repo: Path) -> None:
    _skill(repo, "apps/api/skills/example/SKILL.md")
    (repo / ".claude").mkdir()
    _lock(repo)
    assert _report(repo, "SKILL004")[0] == 0
    (repo / "apps/api/.claude").mkdir()
    code, report = _report(repo, "SKILL004")
    assert code == 1
    assert "apps/api/skills-lock.json" in report["findings"][0]["message"]


def test_repository_rules_run_once_for_overlapping_file_and_directory_inputs(repo: Path) -> None:
    misplaced = _skill(repo, "docs/example/SKILL.md")
    result = CliRunner().invoke(
        app,
        [
            "check",
            str(repo),
            str(misplaced),
            "--select",
            "SKILL003",
            "--output-format",
            "json",
        ],
    )
    assert result.exit_code == 1
    report = json.loads(result.output)
    assert len(report["findings"]) == 1
    assert report["checked_files"] == [str(repo)]


def test_git_failure_is_incomplete_not_clean(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    code, report = _report(tmp_path, "SKILL002")
    assert code == 2
    assert report["errors"]


def test_gitignore_accepts_symlinked_installation_directory(repo: Path) -> None:
    (repo / ".agents/skills").mkdir(parents=True)
    (repo / ".claude").mkdir()
    (repo / ".claude/skills").symlink_to("../.agents/skills", target_is_directory=True)
    (repo / ".gitignore").write_text(".agents/\n.claude/\n")
    assert _report(repo, "SKILL002")[0] == 0


@pytest.mark.parametrize("agent", [".codex", ".cursor", ".gemini", ".opencode", ".github"])
def test_shared_agents_use_agents_installation(repo: Path, agent: str) -> None:
    source = _skill(repo)
    (repo / agent).mkdir()
    if agent == ".github":
        (repo / agent / "copilot-instructions.md").write_text("Instructions")
    shutil.copytree(source.parent, repo / ".agents/skills/example")
    _lock(repo)
    assert _report(repo, "SKILL004")[0] == 0


def test_existing_legacy_agent_installation_is_accepted(repo: Path) -> None:
    source = _skill(repo)
    shutil.copytree(source.parent, repo / ".github/skills/example")
    _lock(repo)
    (repo / ".gitignore").write_text(".github/skills/\n")
    assert _report(repo, "SKILL002,SKILL004")[0] == 0


def test_legacy_directories_still_need_ignore_coverage_when_shared_install_exists(
    repo: Path,
) -> None:
    (repo / ".agents/skills").mkdir(parents=True)
    (repo / ".cursor/skills").mkdir(parents=True)
    (repo / ".gitignore").write_text(".agents/\n")
    code, report = _report(repo, "SKILL002")
    assert code == 1
    assert report["findings"][0]["path"] == str(repo / ".cursor/skills")
