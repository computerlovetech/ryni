from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class RuleScope(StrEnum):
    FILE = "file"
    REPOSITORY = "repository"


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule_id: str
    message: str


def no_fix(path: Path) -> None:
    """Leave findings for manual resolution when a rule has no automatic fix."""


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    description: str
    filename: str
    evaluate: Callable[[Path], list[Finding]]
    scope: RuleScope = RuleScope.FILE
    fix: Callable[[Path], None] = no_fix


@dataclass
class CheckResult:
    checked_files: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 2 if self.errors else int(bool(self.findings))
