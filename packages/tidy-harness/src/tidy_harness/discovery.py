"""Shared, bounded discovery for harness documents."""

import os
import subprocess
from pathlib import Path

EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "_build",
    "site",
    "fixtures",
    "testdata",
    "generated",
}
AGENT_DIRS = {".agents", ".claude", ".github"}


def installed(path: Path) -> bool:
    return any(a in AGENT_DIRS and b == "skills" for a, b in zip(path.parts, path.parts[1:]))


def git(root: Path, *args: str, input: bytes | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", "-C", str(root), *args], input=input, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    return result


def is_checkout(root: Path) -> bool:
    return (root / ".git").exists()


def inventory(root: Path) -> tuple[list[Path], list[Path]]:
    files, directories = [], []

    def fail(error):
        raise error

    for base, names, leaves in os.walk(root, followlinks=False, onerror=fail):
        directory = Path(base)
        names[:] = sorted(
            n
            for n in names
            if n not in EXCLUDED
            and not installed((directory / n).relative_to(root))
            and not (directory / n).is_symlink()
        )
        directories.append(directory)
        files.extend(directory / n for n in sorted(leaves))
    if is_checkout(root):
        candidates = files + directories[1:]
        data = b"".join(os.fsencode(p.relative_to(root)) + b"\0" for p in candidates)
        ignored = set(git(root, "check-ignore", "-z", "--stdin", input=data).stdout.split(b"\0"))
        files = [p for p in files if os.fsencode(p.relative_to(root)) not in ignored]
        directories = [p for p in directories if os.fsencode(p.relative_to(root)) not in ignored]
    return files, directories


def documents(root: Path) -> list[Path]:
    files, _ = inventory(root)
    return [
        p
        for p in files
        if p.name == "AGENTS.md"
        or (
            p.suffix.lower() == ".md"
            and (
                "docs" in p.relative_to(root).parts[:-1]
                or "skills" in p.relative_to(root).parts[:-1]
            )
        )
    ]


def read(path: Path, root: Path) -> str:
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Refusing to read outside the repository: {path}")
    return path.read_text(encoding="utf-8")
