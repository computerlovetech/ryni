import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from fake_instruction_link import InMemoryInstructionLinkRepair
from typer.testing import CliRunner

from ryni.cli import app
from ryni.engine import check
from ryni.instruction_link import InstructionLink
from ryni.models import Finding, Rule, RuleScope
from ryni.rules.claude_symlink import FixClaudeSymlink


@pytest.fixture
def path(tmp_path: Path) -> Path:
    path = tmp_path / "CLAUDE.md"
    path.touch()
    return path


@pytest.mark.parametrize("apply_fix", [False, True])
def test_fixes_require_opt_in_and_report_remaining_findings(path: Path, apply_fix: bool) -> None:
    findings = [Finding(str(path), 1, "CUSTOM", "Needs repair")]
    repairer = InMemoryInstructionLinkRepair(findings)
    rule = Rule(
        "CUSTOM",
        "custom",
        "Example",
        path.name,
        lambda path: list(findings),
        fix=FixClaudeSymlink(repairer),
    )

    result = check([path], [rule], fix=apply_fix)

    assert result.exit_code == (0 if apply_fix else 1)
    assert result.findings == findings
    assert repairer.repaired == ([InstructionLink(path=path)] if apply_fix else [])


def test_rule_without_fixer_keeps_findings(path: Path) -> None:
    finding = Finding(str(path), 1, "CUSTOM", "Manual fix required")
    rule = Rule("CUSTOM", "custom", "Example", path.name, lambda path: [finding])
    result = check([path], [rule], fix=True)
    assert result.findings == [finding]
    assert result.exit_code == 1


def test_clean_rules_do_not_call_fixer(path: Path) -> None:
    repairer = InMemoryInstructionLinkRepair([])
    rule = Rule(
        "CUSTOM", "custom", "Example", path.name, lambda path: [], fix=FixClaudeSymlink(repairer)
    )
    assert check([path], [rule], fix=True).exit_code == 0
    assert repairer.repaired == []


def test_invalid_evaluation_does_not_call_fixer(path: Path) -> None:
    repairer = InMemoryInstructionLinkRepair([])
    rule = Rule(
        "CUSTOM",
        "custom",
        "Example",
        path.name,
        lambda path: ["invalid"],
        fix=FixClaudeSymlink(repairer),
    )
    assert check([path], [rule], fix=True).exit_code == 2
    assert repairer.repaired == []


def test_repository_fixer_receives_root_once_for_repeated_paths(path: Path) -> None:
    findings = [Finding(str(path), 1, "CUSTOM", "Needs repair")]
    repairer = InMemoryInstructionLinkRepair(findings)
    rule = Rule(
        "CUSTOM",
        "custom",
        "Example",
        "",
        lambda path: list(findings),
        scope=RuleScope.REPOSITORY,
        fix=FixClaudeSymlink(repairer),
    )
    assert check([path, path.parent, path], [rule], fix=True).exit_code == 0
    assert repairer.repaired == [InstructionLink(path=path.parent)]


def test_all_rules_are_rechecked_after_fixes(path: Path) -> None:
    findings = [Finding(str(path), 1, "FIRST", "Needs repair")]
    first = Rule("FIRST", "first", "Example", path.name, lambda path: list(findings))
    second = replace(
        first,
        id="SECOND",
        evaluate=lambda path: [replace(finding, rule_id="SECOND") for finding in findings],
        fix=FixClaudeSymlink(InMemoryInstructionLinkRepair(findings)),
    )
    assert check([path], [first, second], fix=True).exit_code == 0


def test_fix_failure_preserves_error_and_other_rules_continue(path: Path) -> None:
    def fail(path: Path) -> None:
        raise OSError("Cannot write")

    finding = Finding(str(path), 1, "FAIL", "Needs repair")
    broken = Rule("FAIL", "broken", "Example", path.name, lambda path: [finding], fix=fail)
    findings = [replace(finding, rule_id="GOOD")]
    repairer = InMemoryInstructionLinkRepair(findings)
    good = replace(
        broken, id="GOOD", evaluate=lambda path: list(findings), fix=FixClaudeSymlink(repairer)
    )
    result = check([path], [broken, good], fix=True)
    assert result.exit_code == 2
    assert result.findings == [finding]
    assert len(result.errors) == 1
    assert "Cannot fix" in result.errors[0]
    assert "Cannot write" in result.errors[0]
    assert repairer.repaired == [InstructionLink(path=path)]


def test_plugin_fix_is_selectable_through_cli(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    findings = [Finding(str(path), 1, "CUSTOM", "Needs repair")]
    rule = Rule(
        "CUSTOM",
        "custom",
        "Example",
        path.name,
        lambda path: list(findings),
        fix=FixClaudeSymlink(InMemoryInstructionLinkRepair(findings)),
    )
    monkeypatch.setattr(
        "ryni.rules.entry_points",
        lambda **kwargs: [SimpleNamespace(name="example", load=lambda: rule)],
    )
    result = CliRunner().invoke(
        app, ["check", str(path), "--select", "CUSTOM", "--fix", "--output-format", "json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == {"checked_files": [str(path)], "findings": [], "errors": []}
