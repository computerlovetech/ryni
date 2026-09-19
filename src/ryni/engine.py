import os
from collections.abc import Sequence
from pathlib import Path

from ryni.models import CheckResult, Finding, ReviewRule, ReviewTask, Rule, RuleScope

EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".agents",
    ".claude",
    ".codex",
    ".github",
}


def repository_root(path: Path) -> Path:
    """Use the nearest Git checkout, including worktrees; otherwise the supplied directory."""
    directory = Path(os.path.abspath(path if path.is_dir() else path.parent))
    for candidate in (directory, *directory.parents):
        if (candidate / ".git").exists():
            return candidate
    return directory


def discover(paths: list[Path], result: CheckResult) -> list[Path]:
    files: dict[Path, Path] = {}
    for path in paths:
        if path.is_file() or path.is_symlink():
            files.setdefault(path.absolute(), path)
        elif path.is_dir():
            files.setdefault(path.absolute(), path)
            for root, directories, names in os.walk(
                path, onerror=lambda error: result.errors.append(str(error))
            ):
                directories[:] = sorted(
                    name for name in directories if name not in EXCLUDED_DIRECTORIES
                )
                # Preserve named directories too: a directory named SKILL.md is invalid.
                for name in sorted(names + directories):
                    candidate = Path(root) / name
                    files.setdefault(candidate.absolute(), candidate)
        else:
            result.errors.append(f"Path does not exist or is not a regular file/directory: {path}")
    return sorted(files.values(), key=str)


def check(
    paths: list[Path], rules: Sequence[Rule | ReviewRule], *, fix: bool = False
) -> CheckResult:
    result = CheckResult()
    repository_rules = [rule for rule in rules if rule.scope == RuleScope.REPOSITORY]
    file_rules = [rule for rule in rules if rule.scope == RuleScope.FILE]
    if repository_rules:
        roots = {repository_root(path) for path in paths if path.exists()}
        for root in sorted(roots):
            _evaluate(root, repository_rules, result, fix=fix)
    for path in discover(paths, result):
        applicable = [rule for rule in file_rules if path.name == rule.filename]
        if not applicable:
            continue
        _evaluate(path, applicable, result, fix=fix)
    if fix:
        # Recheck every rule after all edits, including effects on other rules/targets.
        remaining = check(paths, rules)
        remaining.errors = list(dict.fromkeys([*result.errors, *remaining.errors]))
        return remaining
    return result


def _evaluate(
    path: Path, rules: Sequence[Rule | ReviewRule], result: CheckResult, *, fix: bool = False
) -> None:
    complete = True
    evaluated = False
    for rule in rules:
        if isinstance(rule, ReviewRule):
            result.pending_reviews.append(
                ReviewTask(
                    rule.id, rule.name, rule.description, str(path), rule.instructions, rule.scope
                )
            )
            continue
        evaluated = True
        try:
            findings = _validated_findings(rule.evaluate(path), rule.id)
        except Exception as error:
            result.errors.append(f"Cannot check {path} with {rule.id}: {error}")
            complete = False
            continue
        result.findings.extend(findings)
        if fix and findings:
            try:
                rule.fix(path)
            except Exception as error:
                result.errors.append(f"Cannot fix {path} with {rule.id}: {error}")
                complete = False
    if complete and evaluated:
        result.checked_files.append(str(path))


def _validated_findings(output: object, rule_id: str) -> list[Finding]:
    if not isinstance(output, list):
        raise ValueError("Rule must return a list of Finding objects")
    validated: list[Finding] = []
    for finding in output:
        if not isinstance(finding, Finding):
            raise ValueError("Rule must return a list of Finding objects")
        if not all(
            isinstance(value, str) for value in (finding.path, finding.rule_id, finding.message)
        ):
            raise ValueError("Finding path, rule_id, and message must be strings")
        if type(finding.line) is not int or finding.line < 1:
            raise ValueError("Finding line must be a positive integer")
        if finding.rule_id != rule_id:
            raise ValueError(f"Finding rule_id must match {rule_id}")
        validated.append(finding)
    return validated
