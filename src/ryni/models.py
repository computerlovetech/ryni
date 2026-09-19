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


@dataclass(frozen=True)
class ReviewRule:
    """A convention reviewed by the user's agent, never executed by Rýni."""

    id: str
    name: str
    description: str
    instructions: str
    filename: str = ""
    scope: RuleScope = RuleScope.REPOSITORY


@dataclass(frozen=True)
class RulePack:
    name: str
    description: str
    rules: tuple[Rule | ReviewRule, ...]


@dataclass(frozen=True)
class RuleSource:
    name: str
    description: str = ""
    package: str = ""
    version: str = ""


@dataclass(frozen=True)
class ReviewTask:
    rule_id: str
    name: str
    description: str
    path: str
    instructions: str
    scope: RuleScope = RuleScope.REPOSITORY
    source: RuleSource | None = None


@dataclass
class CheckResult:
    checked_files: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pending_reviews: list[ReviewTask] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        if self.errors:
            return 2
        if self.findings:
            return 1
        return 3 if self.pending_reviews else 0
