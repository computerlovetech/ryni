import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from ryni.cli import app
from ryni.models import Finding, Rule
from ryni.rules import BUILTINS


def install_plugin(monkeypatch: pytest.MonkeyPatch, rule: object) -> None:
    entry = SimpleNamespace(name="example", load=lambda: rule)
    monkeypatch.setattr("ryni.rules.entry_points", lambda **kwargs: [entry])


def test_plugin_is_discoverable_selectable_and_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rule = Rule(
        id="CUSTOM001",
        name="example",
        description="An example third-party rule.",
        filename="example.txt",
        evaluate=lambda path: [Finding(str(path), 1, "CUSTOM001", "Example finding")],
    )
    install_plugin(monkeypatch, rule)
    (tmp_path / "example.txt").write_text("content")
    runner = CliRunner()
    assert "CUSTOM001  example\n" in runner.invoke(app, ["rule"]).output
    assert runner.invoke(app, ["rule", "CUSTOM001"]).output == (
        "CUSTOM001: example\n\nAn example third-party rule.\n"
    )
    result = runner.invoke(app, ["check", str(tmp_path), "--select", "CUSTOM001"])
    assert result.exit_code == 1
    assert "Example finding" in result.output


def test_catalog_failure_is_rendered_as_exit_two(monkeypatch: pytest.MonkeyPatch) -> None:
    install_plugin(monkeypatch, BUILTINS[0])
    result = CliRunner().invoke(app, ["rule"])
    assert result.exit_code == 2
    assert "Error loading rules" in result.output


@pytest.mark.parametrize("format", ["text", "json"])
def test_malformed_plugin_report_is_renderable_and_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    format: str,
) -> None:
    rule = Rule(
        "FAIL001",
        "failure",
        "Fails",
        "file.txt",
        lambda path: ["bad finding"],
    )
    install_plugin(monkeypatch, rule)
    (tmp_path / "file.txt").write_text("content")
    result = CliRunner().invoke(
        app,
        [
            "check",
            str(tmp_path),
            "--select",
            "FAIL001",
            "--output-format",
            format,
        ],
    )
    assert result.exit_code == 2
    assert "Finding objects" in result.output
    if format == "json":
        report = json.loads(result.output)
        assert report["findings"] == []
        assert len(report["errors"]) == 1
