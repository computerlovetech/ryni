import os
from collections.abc import Collection, Sequence
from pathlib import Path

from ryni.cache import check_cache, clear_check_cache
from ryni.models import CheckResult, Finding, ReviewRule, ReviewTask, Rule, RuleScope
from ryni.profiling import CheckProfile, current_profile, measure, profile_run

EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
}


def repository_root(path: Path) -> Path:
    """Use the nearest Git checkout, including worktrees; otherwise the supplied directory."""
    directory = Path(os.path.abspath(path if path.is_dir() else path.parent))
    for candidate in (directory, *directory.parents):
        if (candidate / ".git").exists():
            return candidate
    return directory


def _walk_targets(path: Path, result: CheckResult, filenames: Collection[str] | None):
    """Use DirEntry metadata while live, avoiding os.walk's directory lstat pass.

    Evaluation happens after discovery, so no caller can prune or replace entries
    between yielding a directory and descending into it. Never follow directory
    symlinks. Sort descent for deterministic error order as well as final targets.
    """
    pending = [str(path)]
    while pending:
        root = pending.pop()
        directories = []
        targets = []
        try:
            with os.scandir(root) as entries:
                for entry in entries:
                    try:
                        is_directory = entry.is_dir()
                    except OSError:
                        # Match os.walk: an entry with unknown type is a file.
                        is_directory = False
                    if is_directory and entry.name in EXCLUDED_DIRECTORIES:
                        continue
                    if filenames is None or entry.name in filenames:
                        targets.append(Path(root) / entry.name)
                    if is_directory and not entry.is_symlink():
                        directories.append(entry.path)
        except OSError as error:
            result.errors.append(str(error))
            continue
        yield from targets
        pending.extend(sorted(directories, reverse=True))


def discover(
    paths: list[Path], result: CheckResult, *, filenames: Collection[str] | None = None
) -> list[Path]:
    """Find targets, retaining only requested basenames when a filter is supplied."""
    files: dict[Path, Path] = {}
    for path in paths:
        if path.is_file() or path.is_symlink():
            if filenames is None or path.name in filenames:
                files.setdefault(path.absolute(), path)
        elif path.is_dir():
            if filenames is None or path.name in filenames:
                files.setdefault(path.absolute(), path)
            for candidate in _walk_targets(path, result, filenames):
                files.setdefault(candidate.absolute(), candidate)
        else:
            result.errors.append(f"Path does not exist or is not a regular file/directory: {path}")
    return sorted(files.values(), key=str)


def check(
    paths: list[Path],
    rules: Sequence[Rule | ReviewRule],
    *,
    fix: bool = False,
    profile: CheckProfile | None = None,
) -> CheckResult:
    try:
        with profile_run(profile), check_cache(), measure("stage", "check"):
            result = _check(paths, rules, fix=fix)
            if fix:
                # Recheck all rules with fresh data, including cross-target edits.
                clear_check_cache()
                with measure("stage", "recheck"):
                    remaining = _check(paths, rules)
                remaining.errors = list(dict.fromkeys([*result.errors, *remaining.errors]))
                return remaining
            return result
    finally:
        # A nested fixing check can also change data cached by its caller.
        if fix:
            clear_check_cache()


def _check(
    paths: list[Path], rules: Sequence[Rule | ReviewRule], *, fix: bool = False
) -> CheckResult:
    result = CheckResult()
    repository_rules = [rule for rule in rules if rule.scope == RuleScope.REPOSITORY]
    file_rules: dict[str, list[Rule | ReviewRule]] = {}
    for rule in rules:
        if rule.scope == RuleScope.FILE:
            file_rules.setdefault(rule.filename, []).append(rule)
    if repository_rules:
        with measure("stage", "repository_roots"):
            roots = {repository_root(path) for path in paths if path.exists()}
        for root in sorted(roots):
            _evaluate(root, repository_rules, result, fix=fix)
    if file_rules:
        with measure("stage", "discovery"):
            targets = discover(paths, result, filenames=file_rules)
        for path in targets:
            applicable = file_rules.get(path.name)
            if applicable:
                _evaluate(path, applicable, result, fix=fix)
    else:
        # Validate explicit inputs without walking files that no rule can use.
        for path in paths:
            if not (path.is_file() or path.is_symlink() or path.is_dir()):
                result.errors.append(
                    f"Path does not exist or is not a regular file/directory: {path}"
                )
    return result


def _evaluate(
    path: Path, rules: Sequence[Rule | ReviewRule], result: CheckResult, *, fix: bool = False
) -> None:
    complete = True
    evaluated = False
    profile = current_profile()
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
            if profile is None:
                findings = _validated_findings(rule.evaluate(path), rule.id)
            else:
                with profile.measure("rule", rule.id):
                    findings = _validated_findings(rule.evaluate(path), rule.id)
        except Exception as error:
            result.errors.append(f"Cannot check {path} with {rule.id}: {error}")
            complete = False
            continue
        result.findings.extend(findings)
        if fix and findings:
            try:
                if profile is None:
                    rule.fix(path)
                else:
                    with profile.measure("fix", rule.id):
                        rule.fix(path)
            except Exception as error:
                result.errors.append(f"Cannot fix {path} with {rule.id}: {error}")
                complete = False
            finally:
                # Fixers can change any file, even when they fail partway through.
                clear_check_cache()
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
