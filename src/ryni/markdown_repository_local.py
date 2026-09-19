"""Filesystem adapter for repository Markdown and ryni.toml."""

import os
import tomllib
from pathlib import Path, PurePosixPath

from ryni.markdown_repository import MarkdownSnapshot, RyniConfig
from ryni.skill_repository import RepositoryRoot
from ryni.skill_repository_local import AGENT_DIRECTORIES, SKIP_DIRECTORIES


def _raise_walk_error(error: OSError) -> None:
    raise error


class LocalMarkdownRepository:
    def inspect(self, root: RepositoryRoot) -> MarkdownSnapshot:
        config_path = root.path / "ryni.toml"
        try:
            raw = config_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            config = RyniConfig()
        else:
            try:
                config = RyniConfig.model_validate(tomllib.loads(raw))
            except ValueError as error:
                raise ValueError(f"Invalid {config_path}: {error}") from error
        files: list[PurePosixPath] = []
        for current, directories, names in os.walk(root.path, onerror=_raise_walk_error):
            directory = Path(current)
            if directory != root.path and (directory / ".git").exists():
                directories[:] = []
                continue
            directories[:] = sorted(
                name
                for name in directories
                if name not in SKIP_DIRECTORIES
                and not (name == "skills" and directory.name in AGENT_DIRECTORIES)
            )
            files.extend(
                PurePosixPath((directory / name).relative_to(root.path).as_posix())
                for name in names
                if Path(name).suffix.lower() in (".md", ".markdown")
            )
        return MarkdownSnapshot(files=tuple(sorted(files)), options=config.rules.markdown_location)
