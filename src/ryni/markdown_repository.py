"""Validated input to the Markdown placement policy."""

from pathlib import PurePosixPath, PureWindowsPath
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from ryni.skill_repository import RepositoryRoot


class MarkdownLocationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    additional_allowed_names: tuple[StrictStr, ...] = ()
    additional_allowed_paths: tuple[StrictStr, ...] = ()

    @field_validator("additional_allowed_names")
    @classmethod
    def validate_names(cls, names: tuple[str, ...]) -> tuple[str, ...]:
        for name in names:
            if (
                not name.strip()
                or name != name.strip()
                or name in (".", "..")
                or any(character in name for character in "/\\*?[]\0")
            ):
                raise ValueError("additional_allowed_names must contain literal basenames")
        return names

    @field_validator("additional_allowed_paths")
    @classmethod
    def validate_paths(cls, patterns: tuple[str, ...]) -> tuple[str, ...]:
        for pattern in patterns:
            if (
                not pattern.strip()
                or pattern != pattern.strip()
                or PurePosixPath(pattern).is_absolute()
                or PureWindowsPath(pattern).drive
                or ".." in pattern.split("/")
                or "\\" in pattern
                or "\0" in pattern
                or pattern.endswith("/")
            ):
                raise ValueError(
                    "additional_allowed_paths must contain repository-relative file globs"
                )
        return patterns


class RuleOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    markdown_location: MarkdownLocationOptions = Field(
        default_factory=MarkdownLocationOptions, alias="markdown-location"
    )


class RyniConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: RuleOptions = Field(default_factory=RuleOptions)


class MarkdownSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    files: tuple[PurePosixPath, ...] = ()
    options: MarkdownLocationOptions = Field(default_factory=MarkdownLocationOptions)


class MarkdownRepository(Protocol):
    def inspect(self, root: RepositoryRoot) -> MarkdownSnapshot: ...
