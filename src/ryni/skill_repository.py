"""Validated facts used by repository-wide skill rules."""

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class RepositoryRoot(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: Path


class SkillSource(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: Path
    scope: Path
    under_skills: bool


class SkillLayout(BaseModel):
    sources: tuple[SkillSource, ...] = ()
    installation_directories: tuple[Path, ...] = ()


class IgnoreStatus(BaseModel):
    path: Path
    ignored_by_gitignore: bool
    tracked: bool


class InstallationStatus(BaseModel):
    problems: tuple[str, ...] = ()


class SkillRepository(Protocol):
    def layout(self, root: RepositoryRoot) -> SkillLayout: ...

    def ignores(self, root: RepositoryRoot, layout: SkillLayout) -> tuple[IgnoreStatus, ...]: ...

    def installation(self, source: SkillSource) -> InstallationStatus: ...
