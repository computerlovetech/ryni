"""Human-readable check reports; structured output stays in the CLI."""

from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from ryni.models import CheckResult, Finding


def count_label(count: int, noun: str) -> str:
    return f"{count} {noun}{'s' if count != 1 else ''}"


def render_report(
    result: CheckResult,
    *,
    elapsed: float,
    deterministic: bool = False,
    console: Console | None = None,
    error_console: Console | None = None,
) -> None:
    """Group diagnostics by path and finish with coverage and wall-clock time.

    Use Text for all external content so filenames/messages cannot become markup.
    Rich handles terminal width and disables ANSI when output is redirected.
    """
    console = console or Console(highlight=False)
    error_console = error_console or Console(stderr=True, highlight=False)
    console.print()
    console.print(Text.assemble(("Rýni", "bold cyan"), ("  check", "dim")))
    console.print()

    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in result.findings:
        grouped[finding.path].append(finding)
    for path, findings in grouped.items():
        console.print(Text(path, style="bold", overflow="fold"))
        rows = Table.grid(padding=(0, 2))
        rows.add_column(style="dim", justify="right", no_wrap=True)
        rows.add_column(style="yellow", no_wrap=True)
        rows.add_column(ratio=1, overflow="fold")
        for finding in findings:
            rows.add_row(Text(f"{finding.line}"), Text(finding.rule_id), Text(finding.message))
        console.print(Padding(rows, (0, 0, 0, 2)))
        console.print()

    for error in result.errors:
        error_console.print(Text.assemble(("Error: ", "bold red"), error))

    if result.errors:
        status, style = "Check incomplete", "bold red"
    elif result.findings:
        status, style = "Changes needed", "bold yellow"
    elif result.pending_reviews:
        status, style = "Agent reviews pending", "bold yellow"
    elif not result.checked_files:
        status, style = "No matching files", "bold yellow"
    else:
        status, style = "All checks passed", "bold green"

    console.print(Text(status, style=style))
    totals = [count_label(len(result.findings), "finding")]
    if result.errors:
        totals.append(count_label(len(result.errors), "error"))
    if result.pending_reviews:
        totals.append(f"{count_label(len(result.pending_reviews), 'agent review')} pending")
    console.print(Text(" · ".join(totals)))

    # checked_files also contains directory targets (including repository rules).
    targets = set(result.checked_files)
    directories = sum(Path(path).is_dir() for path in targets)
    coverage = f"{count_label(len(targets) - directories, 'file')} checked"
    if directories:
        coverage += f" · {directories} {'directory' if directories == 1 else 'directories'} checked"
    console.print(Text(f"{coverage} · {elapsed:.2f}s", style="dim"))

    if result.pending_reviews:
        console.print()
        console.print(Text("Agent reviews", style="bold"))
        for task in result.pending_reviews:
            console.print(Text(f"  {task.rule_id}  {task.name}  {task.path}"))
        console.print(
            Text("Use the ryni-check skill in your agent to complete these reviews.", "dim")
        )
    if deterministic:
        console.print(Text("Agent reviews excluded (--deterministic).", style="dim"))
    console.print()
