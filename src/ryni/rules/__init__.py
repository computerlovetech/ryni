from collections.abc import Sequence
from importlib.metadata import entry_points, version
from pathlib import PurePosixPath, PureWindowsPath

from ryni.models import ReviewRule, Rule, RulePack, RuleScope, RuleSource
from ryni.rules.skill_constraints import DESCRIPTION_RULE, DIRECTORY_RULE, NAME_RULE
from ryni.rules.skill_frontmatter import RULE as SKILL_FRONTMATTER

BUILTINS = (SKILL_FRONTMATTER, NAME_RULE, DIRECTORY_RULE, DESCRIPTION_RULE)
type AnyRule = Rule | ReviewRule


class CatalogLoadError(ValueError):
    """No complete catalog could be loaded."""


class UnknownRulesError(ValueError):
    def __init__(self, ids: Sequence[str]) -> None:
        self.ids = tuple(ids)
        super().__init__(f"Unknown rules: {', '.join(item or '<empty>' for item in self.ids)}")


class RuleCatalog:
    def __init__(
        self, rules: dict[str, AnyRule], sources: dict[str, RuleSource] | None = None
    ) -> None:
        self._rules = dict(rules)
        self._sources = dict(sources or {})

    def select(self, ids: Sequence[str] | None = None) -> tuple[AnyRule, ...]:
        if ids is None:
            return tuple(self._rules.values())
        requested = tuple(dict.fromkeys(rule_id.strip() for rule_id in ids))
        if not requested:
            raise UnknownRulesError(("",))
        unknown = tuple(rule_id for rule_id in requested if rule_id not in self._rules)
        if unknown:
            raise UnknownRulesError(unknown)
        return tuple(self._rules[rule_id] for rule_id in requested)

    def get(self, rule_id: str) -> AnyRule:
        return self.select((rule_id,))[0]

    def source(self, rule_id: str) -> RuleSource:
        return self._sources.get(rule_id, RuleSource("unknown"))


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _register(rules: dict[str, AnyRule], rule: object, origin: str) -> None:
    try:
        if not isinstance(rule, (Rule, ReviewRule)):
            raise ValueError("must export a Rule, ReviewRule, or RulePack")
        if isinstance(rule, Rule):
            if not callable(rule.evaluate):
                raise ValueError("evaluate must be callable")
            if not callable(rule.fix):
                raise ValueError("fix must be callable")
        else:
            _text(rule.instructions, "instructions")
        for field in ("id", "name", "description"):
            _text(getattr(rule, field), field)
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
    """Discover installed conventions atomically. Installation is activation."""
    rules: dict[str, AnyRule] = {}
    sources: dict[str, RuleSource] = {}
    for rule in BUILTINS:
        _register(rules, rule, "Built-in rule")
        sources[rule.id] = RuleSource("ryni", "Baseline checks", "ryni", version("ryni"))
    try:
        entries = sorted(entry_points(group="ryni.rules"), key=lambda item: item.name)
    except Exception as error:
        raise CatalogLoadError(f"Cannot discover rule plugins: {error}") from error
    for entry in entries:
        origin = f"Rule plugin {entry.name!r}"
        try:
            exported = entry.load()
            dist = getattr(entry, "dist", None)
            package = dist.metadata["Name"] if dist else ""
            package_version = dist.version if dist else ""
            if isinstance(exported, RulePack):
                _text(exported.name, "pack name")
                _text(exported.description, "pack description")
                if not isinstance(exported.rules, tuple) or not exported.rules:
                    raise ValueError("pack rules must be a non-empty tuple")
                members = exported.rules
                source = RuleSource(exported.name, exported.description, package, package_version)
            else:
                members = (exported,)
                source = RuleSource(entry.name, package=package, version=package_version)
            for rule in members:
                _register(rules, rule, origin)
                sources[rule.id] = source
        except CatalogLoadError:
            raise
        except Exception as error:
            raise CatalogLoadError(f"{origin}: {error}") from error
    return RuleCatalog(rules, sources)
