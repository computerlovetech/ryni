from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from ryni.cli import app
from ryni.models import CheckResult, Finding, ReviewTask
from ryni.reporting import render_report


def render(result, *, width=80, **options):
    output, errors = StringIO(), StringIO()
    render_report(
        result,
        elapsed=1.25,
        console=Console(file=output, width=width, **options),
        error_console=Console(file=errors, width=width, **options),
    )
    return output.getvalue(), errors.getvalue()


def test_groups_findings_and_wraps_literal_content():
    path = "skills/[example]/SKILL.md"
    result = CheckResult(
        checked_files=[path],
        findings=[
            Finding(path, 1, "SKILL001", "Keep [bold]literal[/bold] content in this message."),
            Finding(path, 12, "SKILL004", "Shorten the description to at most 1024 characters."),
        ],
    )
    output, errors = render(result, width=48)
    assert output.count(path) == 1
    assert "[bold]literal[/bold]" in output
    assert "SKILL001" in output and "SKILL004" in output
    assert "2 findings" in output
    assert "1 file checked · 1.25s" in output
    assert all(len(line) <= 48 for line in output.splitlines())
    assert "\x1b" not in output
    assert errors == ""


@pytest.mark.parametrize(
    "result,status",
    [
        (CheckResult(), "No matching files"),
        (CheckResult(checked_files=["SKILL.md"]), "All checks passed"),
        (CheckResult(errors=["Cannot read [file]"]), "Check incomplete"),
        (
            CheckResult(pending_reviews=[ReviewTask("REV001", "Review", "", ".", "Read")]),
            "Agent reviews pending",
        ),
    ],
)
def test_status_is_not_misleading(result, status):
    output, errors = render(result)
    assert status in output
    if result.errors:
        assert "Error: Cannot read [file]" in errors
        assert "1 error" in output
    if result.pending_reviews:
        assert "1 agent review pending" in output
        assert "REV001" in output
        assert "ryni-check" in output


def test_counts_unique_files_and_directories_separately(tmp_path):
    path = tmp_path / "SKILL.md"
    path.touch()
    output, _ = render(CheckResult(checked_files=[str(path), str(path), str(tmp_path)]))
    assert "1 file checked · 1 directory checked · 1.25s" in output


def test_no_color_keeps_status_readable():
    output, _ = render(CheckResult(), force_terminal=True, no_color=True)
    # NO_COLOR disables hues; Rich may retain bold/dim emphasis.
    assert "\x1b[33m" not in output
    assert "No matching files" in output


def test_cli_reports_elapsed_time_including_catalog(tmp_path: Path, monkeypatch):
    ticks = iter([10.0, 11.25])
    monkeypatch.setattr("ryni.cli.perf_counter", lambda: next(ticks))
    path = tmp_path / "SKILL.md"
    path.write_text("invalid")
    result = CliRunner().invoke(app, ["check", str(path), "--select", "SKILL001"])
    assert result.exit_code == 1
    assert "1 file checked · 1.25s" in result.output
    assert "Changes needed" in result.output


def test_compact_preserves_one_line_diagnostics(tmp_path: Path):
    path = tmp_path / "SKILL.md"
    path.write_text("invalid")
    result = CliRunner().invoke(
        app, ["check", str(path), "--select", "SKILL001", "--output-format", "compact"]
    )
    assert result.exit_code == 1
    assert f"{path}:1: SKILL001 " in result.output
    assert "1 target checked · 1 finding" in result.output
