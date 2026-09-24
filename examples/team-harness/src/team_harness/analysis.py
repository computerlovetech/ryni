"""Read-only analysis shared for one check; no commands from scanned repositories run."""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from ryni.cache import cached_per_check

NAMES = frozenset(
    {
        "AGENTS.md",
        "AGENTS.override.md",
        "CLAUDE.md",
        "GEMINI.md",
        "SKILL.md",
        "copilot-instructions.md",
        ".cursorrules",
    }
)
EXCLUDED = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".worktrees",
        "test-repos",
        "vendor",
        "third_party",
    }
)
PARSER = MarkdownIt("commonmark")


def is_harness(path: Path) -> bool:
    return path.name in NAMES or (
        path.suffix in {".md", ".mdc"}
        and any(
            f"{a}/{b}" in path.as_posix()
            for a, b in (
                (".claude", "rules"),
                (".cursor", "rules"),
                (".github", "instructions"),
                (".agents", "skills"),
                (".claude", "skills"),
            )
        )
    )


@cached_per_check
def inventory(root: Path) -> tuple[Path, ...]:
    if (root / ".git").exists():
        output = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            check=True,
            capture_output=True,
        ).stdout
        # Most large-repository paths cannot be harness documents. Reject those
        # before allocating and parsing pathlib objects; keep Git's ignore semantics.
        paths = set()
        for raw in output.split(b"\0"):
            if not raw:
                continue
            name = os.fsdecode(raw)
            basename = name.rsplit("/", 1)[-1]
            if basename not in NAMES and not name.endswith((".md", ".mdc")):
                continue
            path = Path(name)
            if not EXCLUDED.intersection(path.parts) and is_harness(path):
                paths.add(root / path)
        return tuple(sorted(paths))
    paths = []

    def fail(error):
        raise error

    for directory, folders, names in os.walk(root, onerror=fail):
        folders[:] = [name for name in folders if name not in EXCLUDED]
        for name in names + folders:
            path = Path(directory) / name
            if is_harness(path.relative_to(root)):
                paths.append(path)
    return tuple(sorted(paths))


@cached_per_check
def read(path: Path, root: Path) -> str:
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Harness target escapes repository: {path}")
    return path.read_text(encoding="utf-8-sig")


@dataclass(frozen=True)
class Document:
    links: tuple[tuple[str, int], ...]
    imports: tuple[tuple[str, int], ...]
    prose: tuple[tuple[str, int], ...]


@cached_per_check
def parse(text: str) -> Document:
    # Remove frontmatter without changing line offsets.
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            lines[: end + 1] = ["\n"] * (end + 1)
    tokens = PARSER.parse("".join(lines))
    links, imports, prose = [], [], []
    for token in tokens:
        if token.type != "inline":
            continue
        line = token.map[0] + 1
        children = token.children or []
        for child in children:
            if child.type in {"link_open", "image"}:
                links.append((child.attrGet("href" if child.type == "link_open" else "src"), line))
        plain = "".join(c.content for c in children if c.type == "text")
        prose.append((plain, line))
        for offset, raw in enumerate(token.content.splitlines()):
            match = re.fullmatch(r"\s*@([^\s]+)\s*", raw)
            if match:
                imports.append((match[1], line + offset))
    return Document(tuple(links), tuple(imports), tuple(prose))


def local(source: Path, href: str, root: Path) -> Path | None:
    url = urlsplit(href)
    # Absolute paths may be website routes; checked separately for machine paths.
    if url.scheme or url.netloc or not url.path or url.path.startswith(("/", "~")):
        return None
    path = source.parent / unquote(url.path)
    if not path.resolve().is_relative_to(root.resolve()):
        return None
    return path


@cached_per_check
def documents(root: Path) -> tuple[Path, ...]:
    """Harness files plus local Markdown reachable through explicit links/imports."""
    pending = list(inventory(root))
    found = set()
    while pending:
        source = pending.pop()
        if source in found:
            continue
        found.add(source)
        doc = parse(read(source, root))
        for href, _ in doc.links + doc.imports:
            target = local(source, href, root)
            if target is not None and target.suffix.lower() == ".md" and target.is_file():
                # Collapse .. for finite traversal while retaining symlink paths in inventory.
                target = Path(os.path.abspath(target))
                if target not in found:
                    pending.append(target)
    return tuple(sorted(found))
