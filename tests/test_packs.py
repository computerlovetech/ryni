import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from ryni.cli import app
from ryni.engine import check
from ryni.models import Finding, ReviewRule, Rule, RulePack, RuleScope
from ryni.rules import CatalogLoadError, load_catalog

REVIEW = ReviewRule("TEAM002", "review", "A focused review", "Cite contradictory instructions.")
PYTHON = Rule("TEAM001", "python", "A Python check", "AGENTS.md", lambda path: [])
PACK = RulePack("team-harness", "Our conventions", (PYTHON, REVIEW))


@pytest.fixture
def installed_pack(monkeypatch):
    entry = SimpleNamespace(
        name="team",
        load=lambda: PACK,
        dist=SimpleNamespace(metadata={"Name": "team-rules"}, version="1.2.3"),
    )
    monkeypatch.setattr("ryni.rules.entry_points", lambda **kwargs: [entry])
    return entry


def test_pack_is_automatically_active_with_provenance(installed_pack):
    catalog = load_catalog()
    assert [rule.id for rule in catalog.select()] == [
        "SKILL001",
        "SKILL002",
        "SKILL003",
        "SKILL004",
        "TEAM001",
        "TEAM002",
    ]
    assert catalog.source("TEAM002").name == "team-harness"
    assert catalog.source("TEAM002").package == "team-rules"
    assert catalog.source("TEAM002").version == "1.2.3"


@pytest.mark.parametrize(
    "value",
    [
        replace(PACK, name=""),
        replace(PACK, description=None),
        replace(PACK, rules=()),
        replace(PACK, rules=[PYTHON]),
        replace(PACK, rules=(PYTHON, PYTHON)),
        replace(PACK, rules=(PYTHON, object())),
        replace(REVIEW, instructions=" "),
        replace(REVIEW, filename="AGENTS.md"),
        replace(REVIEW, scope=RuleScope.FILE),
        replace(REVIEW, id=""),
    ],
)
def test_invalid_pack_or_review_fails_with_origin(installed_pack, value):
    installed_pack.load = lambda: value
    with pytest.raises(CatalogLoadError, match="Rule plugin 'team'"):
        load_catalog()


def test_review_instructions_and_source_are_discoverable(installed_pack):
    result = CliRunner().invoke(app, ["rule", "TEAM002", "--output-format", "json"])
    assert result.exit_code == 0
    [record] = json.loads(result.output)
    assert record["kind"] == "review"
    assert record["instructions"] == REVIEW.instructions
    assert record["source"]["version"] == "1.2.3"
    assert "Review instructions" in CliRunner().invoke(app, ["rule", "TEAM002"]).output


def test_repository_reviews_are_deduplicated_and_not_counted_as_checked(tmp_path):
    (tmp_path / ".git").mkdir()
    target = tmp_path / "AGENTS.md"
    target.touch()
    result = check([target, tmp_path, target], [REVIEW])
    assert result.exit_code == 3
    assert result.checked_files == []
    assert len(result.pending_reviews) == 1
    assert result.pending_reviews[0].path == str(tmp_path)


def test_file_reviews_follow_discovery_and_ignore_other_files(tmp_path):
    rule = replace(REVIEW, scope=RuleScope.FILE, filename="AGENTS.md")
    target = tmp_path / "AGENTS.md"
    target.touch()
    (tmp_path / "README.md").touch()
    hidden = tmp_path / ".agents"
    hidden.mkdir()
    (hidden / "AGENTS.md").touch()
    result = check([tmp_path, target], [rule])
    assert [task.path for task in result.pending_reviews] == [
        str(hidden / "AGENTS.md"),
        str(target),
    ]
    assert result.pending_reviews[0].scope == RuleScope.FILE
    assert len(check([hidden], [rule]).pending_reviews) == 1


def test_no_applicable_reviews_means_no_pending_work(tmp_path):
    rule = replace(REVIEW, scope=RuleScope.FILE, filename="AGENTS.md")
    result = check([tmp_path], [rule])
    assert result.exit_code == 0
    assert result.pending_reviews == []


def test_review_only_selection_still_reports_missing_paths(tmp_path):
    result = check([tmp_path / "missing"], [REVIEW])
    assert result.exit_code == 2
    assert len(result.errors) == 1
    assert result.pending_reviews == []


def test_findings_and_errors_do_not_hide_reviews(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.touch()
    bad = replace(PYTHON, evaluate=lambda p: [Finding(str(p), 1, PYTHON.id, "Missing setup")])
    result = check([target], [bad, REVIEW])
    assert result.exit_code == 1
    assert len(result.findings) == len(result.pending_reviews) == 1
    result = check([target, tmp_path / "missing"], [bad, REVIEW])
    assert result.exit_code == 2
    assert len(result.findings) == len(result.pending_reviews) == len(result.errors) == 1


def test_fix_rebuilds_review_plan_after_file_changes(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.touch()
    finding = Finding(str(target), 1, PYTHON.id, "Remove empty instructions")
    rule = replace(PYTHON, evaluate=lambda p: [finding], fix=lambda p: p.unlink())
    review = replace(REVIEW, scope=RuleScope.FILE, filename="AGENTS.md")
    result = check([tmp_path], [rule, review], fix=True)
    assert result.exit_code == 0
    assert result.pending_reviews == []


def test_mixed_cli_run_requires_reviews_and_serializes_provenance(tmp_path, installed_pack):
    (tmp_path / "AGENTS.md").touch()
    result = CliRunner().invoke(app, ["check", str(tmp_path), "--output-format", "json"])
    assert result.exit_code == 3
    report = json.loads(result.output)
    assert report["checked_files"] == [str(tmp_path / "AGENTS.md")]
    assert report["pending_reviews"][0]["source"]["package"] == "team-rules"
    result = CliRunner().invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 3
    assert "agent review pending" in result.output


def test_deterministic_opt_out_is_explicit(tmp_path, installed_pack):
    result = CliRunner().invoke(app, ["check", str(tmp_path), "--deterministic"])
    assert result.exit_code == 0
    assert "Agent reviews excluded" in result.output
    result = CliRunner().invoke(
        app, ["check", str(tmp_path), "--deterministic", "--output-format", "json"]
    )
    assert json.loads(result.output)["pending_reviews"] == []


def test_selection_can_exclude_reviews(tmp_path, installed_pack):
    result = CliRunner().invoke(app, ["check", str(tmp_path), "--select", "SKILL001"])
    assert result.exit_code == 0


def test_default_path_is_current_directory(tmp_path, monkeypatch, installed_pack):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["check", "--output-format", "json"])
    assert result.exit_code == 3
    assert json.loads(result.output)["pending_reviews"][0]["path"] == str(tmp_path)
