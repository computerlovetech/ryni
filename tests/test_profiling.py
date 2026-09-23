import json

import pytest
from typer.testing import CliRunner

from ryni.cache import cached_per_check
from ryni.cli import app
from ryni.engine import check
from ryni.models import Finding, ReviewRule, Rule
from ryni.profiling import CheckProfile, current_profile
from ryni.rules import RuleCatalog


def rows(profile):
    return {(row["kind"], row["name"]): row for row in profile.to_dict()["timings"]}


def test_profile_attributes_shared_work_and_keeps_results(tmp_path, monkeypatch):
    path = tmp_path / "config.ini"
    path.write_text("value")
    clock = [0.0]
    monkeypatch.setattr("ryni.profiling.perf_counter", lambda: clock[0])
    reads = []

    @cached_per_check
    def read(path):
        reads.append(path)
        clock[0] += 3
        return path.read_text()

    @cached_per_check
    def analyze(path):
        value = read(path)
        clock[0] += 2
        return value

    def evaluate(path):
        assert analyze(path) == "value"
        clock[0] += 1
        return []

    rules = [Rule(code, code, code, path.name, evaluate) for code in ("FIRST", "SECOND")]
    baseline = check([path], rules)
    reads.clear()
    profile = CheckProfile()
    assert check([path], rules, profile=profile) == baseline
    assert reads == [path]
    timings = rows(profile)
    assert timings["stage", "check"]["seconds"] == 7
    assert timings["stage", "discovery"]["seconds"] == 0
    assert timings["rule", "FIRST"]["seconds"] == 6
    assert timings["rule", "SECOND"]["seconds"] == 1
    analysis = next(row for (kind, name), row in timings.items() if name.endswith(".analyze"))
    assert analysis == {
        "kind": "helper",
        "name": analysis["name"],
        "calls": 2,
        "seconds": 5,
        "failures": 0,
        "cache_hits": 1,
        "cache_misses": 1,
    }
    assert str(path) not in json.dumps(profile.to_dict())
    assert current_profile() is None


def test_unprofiled_checks_do_not_read_clock(tmp_path, monkeypatch):
    def unexpected():
        pytest.fail("Disabled profiling must not read the clock")

    monkeypatch.setattr("ryni.profiling.perf_counter", unexpected)
    path = tmp_path / "config.ini"
    path.touch()

    @cached_per_check
    def read(path):
        return path.read_text()

    def evaluate(path):
        read(path)
        read(path)
        return []

    assert check([path], [Rule("TEST", "test", "Test", path.name, evaluate)]).exit_code == 0


def test_profile_records_failures_and_retries_failed_helpers(tmp_path):
    path = tmp_path / "config.ini"
    path.touch()

    @cached_per_check
    def fail(path):
        raise OSError("Unreadable")

    rules = [Rule(code, code, code, path.name, fail) for code in ("FIRST", "SECOND")]
    rules.append(Rule("INVALID", "invalid", "Invalid output", path.name, lambda path: None))
    rules.append(Rule("GOOD", "good", "Good", path.name, lambda path: []))
    profile = CheckProfile()
    result = check([path], rules, profile=profile)
    assert result.exit_code == 2
    assert len(result.errors) == 3
    timings = rows(profile)
    for code in ("FIRST", "SECOND", "INVALID"):
        assert timings["rule", code]["failures"] == 1
    assert timings["rule", "GOOD"]["failures"] == 0
    helper = next(row for (kind, _), row in timings.items() if kind == "helper")
    assert helper["cache_misses"] == helper["failures"] == 2
    assert helper["cache_hits"] == 0


@pytest.mark.parametrize("fail_fix", [False, True])
def test_profile_includes_fixes_and_fresh_recheck(tmp_path, fail_fix):
    path = tmp_path / "config.ini"
    path.write_text("old")
    reads = []

    @cached_per_check
    def read(path):
        reads.append(path.read_text())
        return reads[-1]

    def evaluate(path):
        return [Finding(str(path), 1, "EDIT", "Repair")] if read(path) == "old" else []

    def fix(path):
        path.write_text("new")
        if fail_fix:
            raise OSError("Partial fix")

    def observe(path):
        assert read(path) == "new"
        return []

    rules = [
        Rule("EDIT", "edit", "Edit", path.name, evaluate, fix=fix),
        Rule("SEE", "see", "See edit", path.name, observe),
    ]
    profile = CheckProfile()
    result = check([path], rules, fix=True, profile=profile)
    assert result.exit_code == (2 if fail_fix else 0)
    assert reads == ["old", "new", "new"]
    timings = rows(profile)
    assert timings["rule", "EDIT"]["calls"] == timings["rule", "SEE"]["calls"] == 2
    assert timings["fix", "EDIT"]["calls"] == 1
    assert timings["fix", "EDIT"]["failures"] == int(fail_fix)
    assert timings["stage", "check"]["calls"] == timings["stage", "recheck"]["calls"] == 1


@pytest.mark.parametrize("profile_nested", [False, True])
def test_nested_check_and_interrupt_restore_profile(tmp_path, profile_nested):
    path = tmp_path / "config.ini"
    path.touch()
    inner_profile = CheckProfile() if profile_nested else None
    outer_profile = CheckProfile()

    def inner(path):
        assert current_profile() is inner_profile
        raise KeyboardInterrupt()

    inner_rule = Rule("INNER", "inner", "Inner", path.name, inner)

    def outer(path):
        with pytest.raises(KeyboardInterrupt):
            check([path], [inner_rule], profile=inner_profile)
        assert current_profile() is outer_profile
        return []

    outer_rule = Rule("OUTER", "outer", "Outer", path.name, outer)
    assert check([path], [outer_rule], profile=outer_profile).exit_code == 0
    assert ("rule", "INNER") not in rows(outer_profile)
    if inner_profile is not None:
        assert rows(inner_profile)["rule", "INNER"]["failures"] == 1
    assert current_profile() is None


@pytest.mark.parametrize("status", [0, 1, 2, 3])
def test_cli_profile_is_opt_in_and_preserves_report_and_exit_code(tmp_path, monkeypatch, status):
    path = tmp_path / "config.ini"
    path.touch()

    def evaluate(path):
        if status == 2:
            raise OSError("Cannot read")
        return [Finding(str(path), 1, "CUSTOM", "Change this")] if status == 1 else []

    rules = {"CUSTOM": Rule("CUSTOM", "custom", "Custom", path.name, evaluate)}
    if status == 3:
        rules["REVIEW"] = ReviewRule("REVIEW", "review", "Review", "Read the config")
    monkeypatch.setattr("ryni.cli.available_rules", lambda: RuleCatalog(rules))
    runner = CliRunner()
    command = ["check", str(path), "--output-format", "json"]
    baseline = runner.invoke(app, command)
    measured = runner.invoke(app, [*command, "--profile"])
    assert baseline.exit_code == measured.exit_code == status
    report = json.loads(measured.output)
    timings = report.pop("profile")["timings"]
    assert report == json.loads(baseline.output)
    assert any(row["kind"] == "stage" and row["name"] == "catalog" for row in timings)
    assert not any(row["kind"] == "rule" and row["name"] == "REVIEW" for row in timings)
    text = runner.invoke(app, ["check", str(path), "--profile"])
    assert text.exit_code == status
    assert "nested rows overlap" in text.output
    assert "rule CUSTOM" in text.output
