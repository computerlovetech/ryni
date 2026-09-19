from collections.abc import Sequence
from importlib.metadata import entry_points
from pathlib import PurePosixPath, PureWindowsPath

from ryni.models import Rule, RuleScope
from ryni.rules.skill_frontmatter import RULE as SKILL_FRONTMATTER

BUILTINS = (SKILL_FRONTMATTER,)

class CatalogLoadError(ValueError):
    """No complete catalog could be loaded."""


class UnknownRulesError(ValueError):
    def __init__(self, ids: Sequence[str]) -> None:
        self.ids = tuple(ids)
        super().__init__(f"Unknown rules: {', '.join(item or '<empty>' for item in self.ids)}")


class RuleCatalog:
    def __init__(self, rules: dict[str, Rule]) -> None:
        self._rules = dict(rules)

    def select(self, ids: Sequence[str] | None = None) -> tuple[Rule, ...]:
        if ids is None:
            return tuple(self._rules.values())
        requested = tuple(dict.fromkeys(rule_id.strip() for rule_id in ids))
        if not requested:
            raise UnknownRulesError(("",))
        unknown = tuple(rule_id for rule_id in requested if rule_id not in self._rules)
        if unknown:
            raise UnknownRulesError(unknown)
        return tuple(self._rules[rule_id] for rule_id in requested)

    def get(self, rule_id: str) -> Rule:
        return self.select((rule_id,))[0]


def _register(rules: dict[str, Rule], rule: object, origin: str) -> None:
    try:
        if not isinstance(rule, Rule) or not callable(rule.evaluate):
            raise ValueError("must export a ryni.models.Rule with a callable evaluator")
        if not callable(rule.fix):
            raise ValueError("fix must be callable")
        for field in ("id", "name", "description"):
            value = getattr(rule, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if rule.id != rule.id.strip() or "," in rule.id:
            raise ValueError("id must not contain surrounding whitespace or commas")
        if not isinstance(rule.scope, RuleScope):
            raise ValueError("scope must be a RuleScope value")
        if rule.scope == RuleScope.REPOSITORY:
            if rule.filename != "":
                raise ValueError("repository rules must use an empty filename")
        elif (
            not isinstance(rule.filename, str)
            or not rule.filename.strip()
            or rule.filename in (".", "..")
            or "\0" in rule.filename
            or PurePosixPath(rule.filename).name != rule.filename
            or PureWindowsPath(rule.filename).name != rule.filename
        ):
            raise ValueError("filename must be a basename")
        if rule.id in rules:
            raise ValueError(f"Duplicate rule ID: {rule.id}")
        rules[rule.id] = rule
    except ValueError as error:
        raise CatalogLoadError(f"{origin}: {error}") from error


def load_catalog() -> RuleCatalog:
    """Load and validate all rules atomically, retaining plugin provenance in failures."""
    rules: dict[str, Rule] = {}
    for index, rule in enumerate(BUILTINS):
        _register(rules, rule, f"Built-in rule {index + 1}")
    try:
        entries = sorted(entry_points(group="ryni.rules"), key=lambda item: item.name)
    except Exception as error:
        raise CatalogLoadError(f"Cannot discover rule plugins: {error}") from error
    for entry in entries:
        try:
            rule = entry.load()
        except Exception as error:
            raise CatalogLoadError(f"Rule plugin {entry.name!r}: {error}") from error
        _register(rules, rule, f"Rule plugin {entry.name!r}")
    return RuleCatalog(rules)
