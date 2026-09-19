import json
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from ryni.engine import check as run_checks
from ryni.rules import CatalogLoadError, RuleCatalog, UnknownRulesError, load_catalog

app = typer.Typer(help="Rýni: rule-based linting for agent harnesses.", no_args_is_help=True)


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


def available_rules() -> RuleCatalog:
    try:
        return load_catalog()
    except CatalogLoadError as error:
        typer.echo(f"Error loading rules: {error}", err=True)
        raise typer.Exit(2) from error


@app.command()
def check(
    paths: Annotated[list[Path], typer.Argument(help="Files or directories to check.")],
    select: Annotated[str | None, typer.Option(help="Comma-separated rule IDs.")] = None,
    fix: Annotated[
        bool, typer.Option(help="Apply available fixes, then report remaining findings.")
    ] = False,
    output_format: Annotated[OutputFormat, typer.Option(help="Diagnostic output format.")] = (
        OutputFormat.TEXT
    ),
) -> None:
    """Check selected paths. Exit 0: clean, 1: findings, 2: error/incomplete."""
    catalog = available_rules()
    try:
        rules = catalog.select(select.split(",") if select is not None else None)
    except UnknownRulesError as error:
        raise typer.BadParameter(str(error), param_hint="--select") from error
    result = run_checks(paths, rules, fix=fix)
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(asdict(result), indent=2))
    else:
        for finding in result.findings:
            typer.echo(f"{finding.path}:{finding.line}: {finding.rule_id} {finding.message}")
        for error in result.errors:
            typer.echo(f"Error: {error}", err=True)
        typer.echo(
            f"Checked {len(result.checked_files)} targets · {len(result.findings)} findings · "
            f"{len(result.errors)} errors"
        )
    raise typer.Exit(result.exit_code)


@app.command()
def rule(rule_id: Annotated[str | None, typer.Argument(help="Rule ID to explain.")] = None) -> None:
    """List rules, or explain one rule with an example."""
    catalog = available_rules()
    if rule_id is None:
        for item in catalog.select():
            typer.echo(f"{item.id}  {item.name}")
        return
    try:
        item = catalog.get(rule_id)
    except UnknownRulesError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"{item.id}: {item.name}\n\n{item.description}")
