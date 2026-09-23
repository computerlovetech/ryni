from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from ryni.engine import check
from ryni.models import Finding, Rule, RuleScope


def _rule(evaluate: Callable[[Path], object], rule_id: str = "TEST001") -> Rule:
    return Rule(
        rule_id,
        "test",
        "Test rule",
        "file.txt",
        cast(Callable[[Path], list[Finding]], evaluate),
    )


@pytest.mark.parametrize(
    "output",
    [
        None,
        "invalid",
        (),
        {},
        [None],
        ["invalid"],
        [Finding("file.txt", 0, "TEST001", "message")],
        [Finding("file.txt", -1, "TEST001", "message")],
        [Finding("file.txt", True, "TEST001", "message")],
        [Finding("file.txt", 1.5, "TEST001", "message")],
        [Finding(12, 1, "TEST001", "message")],
        [Finding("file.txt", 1, "TEST001", None)],
        [Finding("file.txt", 1, "WRONG", "message")],
    ],
)
def test_invalid_rule_output_is_incomplete(tmp_path: Path, output: object) -> None:
    path = tmp_path / "file.txt"
    path.write_text("content")
    result = check([path], [_rule(lambda path: output)])
    assert result.exit_code == 2
    assert result.findings == []
    assert result.checked_files == []
    assert len(result.errors) == 1
    assert "TEST001" in result.errors[0]


def test_mixed_result_is_atomic_but_other_rules_keep_findings(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("content")
    good = Finding(str(path), 1, "GOOD", "preserved")
    bad = _rule(lambda path: [Finding(str(path), 1, "TEST001", "discard"), None])
    result = check([path], [bad, _rule(lambda path: [good], "GOOD")])
    assert result.findings == [good]
    assert len(result.errors) == 1
    assert result.checked_files == []
    assert result.exit_code == 2


def test_failure_does_not_stop_later_files(tmp_path: Path) -> None:
    paths = [tmp_path / name / "file.txt" for name in ("a", "b")]
    for path in paths:
        path.parent.mkdir()
        path.write_text("content")

    def evaluate(path: Path) -> list[Finding]:
        if path == paths[0]:
            raise RuntimeError("checker failed")
        return [Finding(str(path), 1, "TEST001", "preserved")]

    result = check([tmp_path], [_rule(evaluate)])
    assert result.checked_files == [str(paths[1])]
    assert len(result.findings) == 1
    assert "checker failed" in result.errors[0]
    assert result.exit_code == 2


def test_process_control_exceptions_propagate(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.touch()

    def interrupt(path: Path) -> list[Finding]:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        check([path], [_rule(interrupt)])


def test_related_file_diagnostics_are_allowed(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.touch()
    finding = Finding(str(tmp_path / "other.txt"), 3, "TEST001", "related")
    result = check([path], [_rule(lambda path: [finding])])
    assert result.findings == [finding]
    assert result.exit_code == 1


def test_repository_rule_outputs_use_same_validation(tmp_path: Path) -> None:
    rule = Rule(
        "REPO",
        "repo",
        "Repository rule",
        "",
        cast(Callable[[Path], list[Finding]], lambda path: ["invalid"]),
        RuleScope.REPOSITORY,
    )
    result = check([tmp_path], [rule])
    assert result.exit_code == 2
    assert result.findings == []
    assert result.checked_files == []


@pytest.mark.parametrize("with_rule", [False, True])
def test_without_file_rules_skips_walk_but_validates_inputs(tmp_path, monkeypatch, with_rule):
    def unexpected_walk(*args, **kwargs):
        pytest.fail("No file rules need a directory walk")

    monkeypatch.setattr("ryni.engine.os.walk", unexpected_walk)
    rules = [Rule("REPO", "repo", "Repository", "", lambda path: [], RuleScope.REPOSITORY)]
    result = check([tmp_path, tmp_path / "missing"], rules if with_rule else [])
    assert result.checked_files == ([str(tmp_path)] if with_rule else [])
    assert result.exit_code == 2
    assert len(result.errors) == 1
    assert "missing" in result.errors[0]


def test_indexed_rules_preserve_file_and_rule_order(tmp_path):
    for name in ("b.txt", "a.txt"):
        (tmp_path / name).touch()
    calls = []

    def rule(code, filename):
        def evaluate(path):
            calls.append((path.name, code))
            return []
        return Rule(code, code, code, filename, evaluate)

    result = check([tmp_path], [rule("B", "b.txt"), rule("A2", "a.txt"), rule("A1", "a.txt")])
    assert result.exit_code == 0
    assert calls == [("a.txt", "A2"), ("a.txt", "A1"), ("b.txt", "B")]
