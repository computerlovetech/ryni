from dataclasses import replace
from types import SimpleNamespace

import pytest

from ryni.models import Rule, RuleScope
from ryni.rules import BUILTINS, CatalogLoadError, UnknownRulesError, load_catalog


@pytest.fixture(autouse=True)
def no_installed_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ryni.rules.entry_points", lambda **kwargs: [])


def _plugin(monkeypatch: pytest.MonkeyPatch, value: object) -> None:
    monkeypatch.setattr(
        "ryni.rules.entry_points",
        lambda **kwargs: [
            SimpleNamespace(name="example-plugin", load=lambda: value),
        ],
    )


def test_default_selection_preserves_builtin_order() -> None:
    assert load_catalog().select() == BUILTINS


def test_selection_trims_and_deduplicates_preserving_requested_order() -> None:
    selected = load_catalog().select([" AGENT001 ", "SKILL001", "AGENT001"])
    assert tuple(rule.id for rule in selected) == ("AGENT001", "SKILL001")


def test_selection_reports_all_unknown_ids() -> None:
    with pytest.raises(UnknownRulesError) as caught:
        load_catalog().select(["UNKNOWN", "SKILL001", "OTHER", "UNKNOWN"])
    assert caught.value.ids == ("UNKNOWN", "OTHER")


@pytest.mark.parametrize("selection", [[], [""], ["  "], ["SKILL001", ""]])
def test_explicit_empty_selection_is_invalid(selection: list[str]) -> None:
    with pytest.raises(UnknownRulesError):
        load_catalog().select(selection)


def test_lookup_uses_selection_policy() -> None:
    catalog = load_catalog()
    assert catalog.get(" SKILL001 ") == catalog.select(["SKILL001"])[0]
    with pytest.raises(UnknownRulesError):
        catalog.get("UNKNOWN")


@pytest.mark.parametrize(
    "plugin",
    [
        object(),
        BUILTINS[0],
        replace(BUILTINS[0], id="CUSTOM", name=" "),
        replace(BUILTINS[0], id="CUSTOM", description=12),
        replace(BUILTINS[0], id="CUSTOM", filename="../SKILL.md"),
        replace(BUILTINS[0], id="CUSTOM", filename="foo\\SKILL.md"),
        replace(BUILTINS[0], id="CUSTOM", filename=""),
        replace(BUILTINS[0], id=" CUSTOM"),
        replace(BUILTINS[0], id="A,B"),
        replace(BUILTINS[0], id="CUSTOM", scope="repository"),
        replace(BUILTINS[0], id="CUSTOM", evaluate=None),
        replace(BUILTINS[0], id="CUSTOM", fix=None),
        replace(BUILTINS[0], id="CUSTOM", scope=RuleScope.REPOSITORY),
    ],
)
def test_invalid_plugin_fails_with_provenance(
    monkeypatch: pytest.MonkeyPatch, plugin: object
) -> None:
    _plugin(monkeypatch, plugin)
    with pytest.raises(CatalogLoadError, match="example-plugin"):
        load_catalog()


def test_loader_failure_is_wrapped_with_plugin_name(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> Rule:
        raise RuntimeError("missing optional dependency")

    monkeypatch.setattr(
        "ryni.rules.entry_points",
        lambda **kwargs: [
            SimpleNamespace(name="broken-package", load=fail),
        ],
    )
    with pytest.raises(CatalogLoadError, match="broken-package.*missing optional dependency"):
        load_catalog()


def test_entry_point_discovery_failure_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(**kwargs: object) -> list:
        raise OSError("broken metadata")

    monkeypatch.setattr("ryni.rules.entry_points", fail)
    with pytest.raises(CatalogLoadError, match="Cannot discover"):
        load_catalog()


def test_plugin_order_follows_entry_point_names(monkeypatch: pytest.MonkeyPatch) -> None:
    first = replace(BUILTINS[0], id="FIRST")
    last = replace(BUILTINS[0], id="LAST")
    monkeypatch.setattr(
        "ryni.rules.entry_points",
        lambda **kwargs: [
            SimpleNamespace(name="z", load=lambda: last),
            SimpleNamespace(name="a", load=lambda: first),
        ],
    )
    assert load_catalog().select()[-2:] == (first, last)
