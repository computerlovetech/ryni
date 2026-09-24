import json
from dataclasses import asdict, replace
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer

from ryni.engine import check as run_checks
from ryni.models import ReviewRule, Rule
from ryni.profiling import CheckProfile, measure, profile_run
from ryni.reporting import count_label, render_report
from ryni.rules import CatalogLoadError, RuleCatalog, UnknownRulesError, load_catalog
from ryni.skill import app as skill_app

app = typer.Typer(help="Rýni: adopt conventions, catch harness drift.", no_args_is_help=True)
app.add_typer(skill_app, name="skill")


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class CheckOutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"
    COMPACT = "compact"


def available_rules() -> RuleCatalog:
    try:
        return load_catalog()
    except CatalogLoadError as error:
        typer.echo(f"Error loading rules: {error}", err=True)
        raise typer.Exit(2) from error


@app.command()
def check(
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Files or directories. Defaults to .")
    ] = None,
    select: Annotated[str | None, typer.Option(help="Comma-separated rule IDs.")] = None,
    fix: Annotated[
        bool, typer.Option(help="Apply available deterministic fixes, then recheck.")
    ] = False,
    deterministic: Annotated[
        bool, typer.Option(help="Run only Python checks; explicitly omit agent reviews.")
    ] = False,
    profile: Annotated[
        bool, typer.Option(help="Report rule timings and shared-helper cache statistics.")
    ] = False,
    output_format: Annotated[CheckOutputFormat, typer.Option(help="Diagnostic output format.")] = (
        CheckOutputFormat.TEXT
    ),
) -> None:
    """Run checks and prepare agent reviews. Exit 0: clean, 1: findings, 2: error, 3: reviews pending."""
    started = perf_counter()
    timings = CheckProfile() if profile else None
    with profile_run(timings), measure("stage", "catalog"):
        catalog = available_rules()
    try:
        rules = catalog.select(select.split(",") if select is not None else None)
    except UnknownRulesError as error:
        raise typer.BadParameter(str(error), param_hint="--select") from error
    if deterministic:
        rules = tuple(rule for rule in rules if isinstance(rule, Rule))
    result = run_checks(paths or [Path(".")], rules, fix=fix, profile=timings)
    result.pending_reviews = [
        replace(task, source=catalog.source(task.rule_id)) for task in result.pending_reviews
    ]
    elapsed = perf_counter() - started
    if output_format == CheckOutputFormat.JSON:
        report = asdict(result)
        if timings is not None:
            report["profile"] = timings.to_dict()
        typer.echo(json.dumps(report, indent=2))
    elif output_format == CheckOutputFormat.TEXT:
        render_report(result, elapsed=elapsed, deterministic=deterministic)
    else:
        for finding in result.findings:
            typer.echo(f"{finding.path}:{finding.line}: {finding.rule_id} {finding.message}")
        for error in result.errors:
            typer.echo(f"Error: {error}", err=True)
        summary = (
            f"{count_label(len(result.checked_files), 'target')} checked · "
            f"{count_label(len(result.findings), 'finding')}"
        )
        if result.errors:
            summary += f" · {count_label(len(result.errors), 'error')}"
        typer.echo(summary)
        if result.pending_reviews:
            typer.echo(f"{count_label(len(result.pending_reviews), 'agent review')} pending:")
            for task in result.pending_reviews:
                typer.echo(f"  {task.rule_id}  {task.name}  {task.path}")
            typer.echo("Use the ryni-check skill in your agent to complete these reviews.")
        if deterministic:
            typer.echo("Agent reviews excluded (--deterministic).")
    if timings is not None and output_format != CheckOutputFormat.JSON:
        typer.echo("Profile: inclusive wall time; nested rows overlap. Startup/output excluded.")
        for timing in timings.to_dict()["timings"]:
            detail = (
                f"{count_label(timing['calls'], 'call')} · "
                f"{count_label(timing['failures'], 'failure')}"
            )
            if timing["kind"] == "helper":
                detail += (
                    f" · {timing['cache_hits']} cache hits · {timing['cache_misses']} cache misses"
                )
            typer.echo(
                f"  {timing['kind']} {timing['name']}  {timing['seconds'] * 1000:.3f} ms · {detail}"
            )
    raise typer.Exit(result.exit_code)


@app.command()
def rule(
    rule_id: Annotated[str | None, typer.Argument(help="Rule ID to explain.")] = None,
    output_format: Annotated[
        OutputFormat, typer.Option(help="Rule output format.")
    ] = OutputFormat.TEXT,
) -> None:
    """List active conventions and their packs, or explain one."""
    catalog = available_rules()
    try:
        selected = (catalog.get(rule_id),) if rule_id is not None else catalog.select()
    except UnknownRulesError as error:
        raise typer.BadParameter(str(error)) from error
    records = []
    for item in selected:
        record = {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "kind": "review" if isinstance(item, ReviewRule) else "deterministic",
            "scope": item.scope.value,
            "filename": item.filename,
            "source": asdict(catalog.source(item.id)),
        }
        if isinstance(item, ReviewRule):
            record["instructions"] = item.instructions
        records.append(record)
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(records, indent=2))
        return
    if rule_id is None:
        for record in records:
            source = record["source"]
            label = " ".join(filter(None, (source["name"], source["version"])))
            typer.echo(f"{record['id']}  {record['name']}  [{record['kind']}]  {label}")
    else:
        record = records[0]
        source = record["source"]
        typer.echo(
            f"{record['id']}: {record['name']}\n"
            f"{record['kind']} · {source['name']} {source['version']}\n\n"
            f"{record['description']}"
        )
        if "instructions" in record:
            typer.echo(f"\nReview instructions\n\n{record['instructions']}")
