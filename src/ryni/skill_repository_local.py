"""Read-only filesystem and Git adapter for skill repository facts."""

import os
import re
import subprocess
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from ryni.skill_repository import (
    IgnoreStatus,
    InstallationStatus,
    RepositoryRoot,
    SkillLayout,
    SkillSource,
)

# Project destinations follow vercel-labs/skills/src/agents.ts. Existing legacy
# installations remain supported when no shared installation directory exists.
SHARED_AGENTS = {".codex", ".cursor", ".gemini", ".github", ".opencode"}
AGENT_DIRECTORIES = frozenset(
    {
        ".agents",
        ".claude",
        ".codex",
        ".github",
        ".cursor",
        ".gemini",
        ".opencode",
        ".windsurf",
        ".kiro",
        ".roo",
        ".qwen",
        ".kilocode",
    }
)
SKIP_DIRECTORIES = {".git", ".venv", "venv", "node_modules", "__pycache__"}


class LockEntry(BaseModel):
    source: StrictStr = Field(min_length=1)
    sourceType: StrictStr
    computedHash: StrictStr = Field(pattern=r"^[a-fA-F0-9]{64}$")


class SkillsLock(BaseModel):
    model_config = ConfigDict(strict=True)
    version: Literal[1]
    skills: dict[str, LockEntry]


def repository_root(path: Path) -> Path:
    """Use the nearest Git checkout, including worktrees; otherwise the supplied directory."""
    directory = Path(os.path.abspath(path if path.is_dir() else path.parent))
    for candidate in (directory, *directory.parents):
        if (candidate / ".git").exists():
            return candidate
    return directory


def configured_installations(scope: Path) -> tuple[Path, ...]:
    directories: set[Path] = set()
    for agent in AGENT_DIRECTORIES:
        config = scope / agent
        if not config.is_dir():
            continue
        if agent == ".github" and not (
            (config / "skills").exists() or (config / "copilot-instructions.md").is_file()
        ):
            continue
        destination = config
        if agent in SHARED_AGENTS and (
            (scope / ".agents/skills").is_dir() or not (config / "skills").is_dir()
        ):
            destination = scope / ".agents"
        directories.add(destination / "skills")
    return tuple(sorted(directories))


def _raise_walk_error(error: OSError) -> None:
    raise error


def _git(root: Path, arguments: list[str], stdin: str = "") -> subprocess.CompletedProcess[str]:
    # Keep repository selection independent of the invoking shell's Git environment.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(
        ["git", "-c", f"core.excludesFile={os.devnull}", "-C", str(root), *arguments],
        input=stdin,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise OSError(result.stderr.strip() or "Git inspection failed")
    return result


class LocalSkillRepository:
    def layout(self, root: RepositoryRoot) -> SkillLayout:
        sources: list[SkillSource] = []
        installations: set[Path] = set()
        for current, directories, names in os.walk(root.path, onerror=_raise_walk_error):
            directory = Path(current)
            if directory != root.path and (directory / ".git").exists():
                directories[:] = []
                continue
            installations.update(configured_installations(directory))
            installations.update(
                directory / agent / "skills"
                for agent in AGENT_DIRECTORIES
                if (directory / agent / "skills").exists()
                or (directory / agent / "skills").is_symlink()
            )
            directories[:] = sorted(
                name
                for name in directories
                if name not in SKIP_DIRECTORIES
                and not (name == "skills" and directory.name in AGENT_DIRECTORIES)
            )
            if "SKILL.md" not in names:
                continue
            relative = directory.relative_to(root.path)
            parts = relative.parts
            under_skills = "skills" in parts or root.path.name == "skills"
            if "skills" in parts:
                scope = root.path.joinpath(*parts[: parts.index("skills")])
            elif root.path.name == "skills":
                scope = root.path.parent
            else:
                scope = root.path
            sources.append(
                SkillSource(
                    path=directory / "SKILL.md",
                    scope=scope,
                    under_skills=under_skills,
                )
            )
        return SkillLayout(
            sources=tuple(sorted(sources, key=lambda source: str(source.path))),
            installation_directories=tuple(sorted(installations)),
        )

    def ignores(self, root: RepositoryRoot, layout: SkillLayout) -> tuple[IgnoreStatus, ...]:
        if not layout.installation_directories:
            return ()
        relative = [
            path.relative_to(root.path).as_posix() for path in layout.installation_directories
        ]
        # Git treats a symlink as a file and refuses queries below it.
        queries: list[str] = []
        for directory in layout.installation_directories:
            query_path = directory.relative_to(root.path).as_posix() + "/"
            for parent in reversed((directory, *directory.parents)):
                if parent.is_relative_to(root.path) and parent.is_symlink():
                    query_path = parent.relative_to(root.path).as_posix()
                    break
            queries.append(query_path)
        # Query directories themselves, so coverage of only some contents is insufficient.
        query = "\0".join(queries) + "\0"
        response = _git(root.path, ["check-ignore", "--no-index", "-v", "-z", "--stdin"], query)
        fields = response.stdout.split("\0")
        covered: set[str] = set()
        for offset in range(0, len(fields) - 1, 4):
            origin, _, pattern, path = fields[offset : offset + 4]
            if Path(origin).name == ".gitignore" and not pattern.startswith("!"):
                covered.add(path.rstrip("/"))
        tracked = _git(root.path, ["ls-files", "--cached", "-z"]).stdout.split("\0")
        return tuple(
            IgnoreStatus(
                path=directory,
                ignored_by_gitignore=query_path.rstrip("/") in covered,
                tracked=any(
                    item == query_path.rstrip("/") or item.startswith(name + "/")
                    for item in tracked
                    if item
                ),
            )
            for directory, name, query_path in zip(
                layout.installation_directories, relative, queries, strict=True
            )
        )

    def installation(self, source: SkillSource) -> InstallationStatus:
        destinations = configured_installations(source.scope)
        if not destinations:
            return InstallationStatus()
        lines = source.path.read_text(encoding="utf-8-sig").splitlines()
        try:
            if not lines or lines[0] != "---":
                raise ValueError("missing frontmatter")
            end = lines.index("---", 1)
            metadata = yaml.safe_load("\n".join(lines[1:end]))
            if not isinstance(metadata, dict):
                raise ValueError("frontmatter is not a mapping")
            name = metadata.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("missing skill name")
        except (ValueError, yaml.YAMLError) as error:
            return InstallationStatus(problems=(f"Cannot identify local skill: {error}.",))
        lock_path = source.scope / "skills-lock.json"
        try:
            lock = SkillsLock.model_validate_json(lock_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError) as error:
            reason = "missing" if isinstance(error, FileNotFoundError) else "invalid"
            return InstallationStatus(
                problems=(f"{lock_path} is {reason}; install with npx skills.",)
            )
        if name not in lock.skills:
            return InstallationStatus(problems=(f"No npx skills lock entry for {name!r}.",))
        entry = lock.skills[name]
        origin = (source.scope / entry.source).resolve()
        if entry.sourceType != "local" or not source.path.parent.resolve().is_relative_to(origin):
            return InstallationStatus(
                problems=(f"Lock entry for {name!r} does not reference its local source.",)
            )
        # Match the installer's directory-name normalization, without executing npx.
        installed_name = (
            re.sub(r"[^a-z0-9._]+", "-", name.lower()).strip(".-")[:255] or "unnamed-skill"
        )
        problems: list[str] = []
        for destination in destinations:
            installed = destination / installed_name / "SKILL.md"
            if not installed.is_file():
                problems.append(
                    f"{name!r} is not installed at {installed}; run npx skills in {source.scope}."
                )
            elif installed.read_bytes() != source.path.read_bytes():
                problems.append(
                    f"{installed} differs from its local SKILL.md; reinstall with npx skills."
                )
        return InstallationStatus(problems=tuple(problems))
