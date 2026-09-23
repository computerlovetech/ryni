from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Install bundled Rýni agent skills.", no_args_is_help=True)


class SkillName(StrEnum):
    CHECK = "ryni-check"
    AUTHOR = "ryni-rule-author"


def _resources(source, relative: Path = Path()):
    for child in sorted(source.iterdir(), key=lambda item: item.name):
        path = relative / child.name
        if child.is_dir():
            if child.name != "__pycache__":
                yield from _resources(child, path)
        else:
            yield path, child.read_bytes()


@app.command()
def install(
    directory: Annotated[
        Path, typer.Argument(help="Agent skills directory (for example .agents/skills).")
    ] = Path(".agents/skills"),
    name: Annotated[SkillName, typer.Option(help="Bundled skill to install.")] = SkillName.CHECK,
) -> None:
    """Install the bundled skill. Existing custom instructions are never overwritten."""
    from importlib.resources import files

    source = files("ryni").joinpath("skills", name.value)
    destination = directory / name.value
    try:
        pending = []
        # Validate every resource before writing, including nested reference files.
        for relative, content in _resources(source):
            target = destination / relative
            for part in (target, *target.parents):
                if part == directory:
                    break
                if part.is_symlink():
                    raise ValueError(f"Refusing to write through a skill symlink: {part}")
                if part != target and part.exists() and not part.is_dir():
                    raise ValueError(f"Skill directory is not a directory: {part}")
            if target.exists():
                if not target.is_file() or target.read_bytes() != content:
                    raise ValueError(
                        f"Existing skill differs: {target}. Review it before replacing it."
                    )
            else:
                pending.append((target, content))
        if not pending:
            typer.echo(f"Already installed: {destination / 'SKILL.md'}")
            return
        for target, content in pending:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(content)
    except (OSError, ValueError) as error:
        typer.echo(f"Cannot install skill: {error}", err=True)
        raise typer.Exit(2) from error
    purpose = "check the full policy" if name == SkillName.CHECK else "build a rule pack"
    typer.echo(f"Installed: {destination / 'SKILL.md'}\nInvoke {name.value} to {purpose}.")
