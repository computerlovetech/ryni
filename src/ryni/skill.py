from importlib.resources import files
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Install the ryni-check agent skill.", no_args_is_help=True)


@app.command()
def install(
    directory: Annotated[
        Path, typer.Argument(help="Agent skills directory (for example .agents/skills).")
    ] = Path(".agents/skills"),
) -> None:
    """Install the bundled skill. Existing custom instructions are never overwritten."""
    content = files("ryni").joinpath("skills/ryni-check/SKILL.md").read_text(encoding="utf-8")
    target = directory / "ryni-check" / "SKILL.md"
    try:
        if target.is_symlink() or target.parent.is_symlink():
            raise ValueError(f"Refusing to write through a skill symlink: {target}")
        if target.exists():
            if target.read_text(encoding="utf-8") != content:
                raise ValueError(
                    f"Existing skill differs: {target}. Review it before replacing it."
                )
            typer.echo(f"Already installed: {target}")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as handle:
            handle.write(content)
    except (OSError, ValueError) as error:
        typer.echo(f"Cannot install skill: {error}", err=True)
        raise typer.Exit(2) from error
    typer.echo(f"Installed: {target}\nInvoke ryni-check in your agent to check the full policy.")
