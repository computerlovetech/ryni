"""Deterministic conventions TIDY001–TIDY006."""

import os
from pathlib import Path

from ryni.models import Finding, Rule, RuleScope

from .discovery import AGENT_DIRS, documents, git, installed, inventory, is_checkout, read
from .markdown import local, parse


def finding(root, path, code, message, line=1):
    return Finding(path.relative_to(root).as_posix(), line, code, message)


def brief_instructions(root: Path) -> list[Finding]:
    return [
        finding(root, p, "TIDY001", "Keep AGENTS.md at or below 250 lines.", 251)
        for p in inventory(root)[0]
        if p.name == "AGENTS.md" and len(read(p, root).splitlines()) > 250
    ]


def canonical_instructions(root: Path) -> list[Finding]:
    findings = []
    files, directories = inventory(root)
    for path in files + directories:
        if path.name != "CLAUDE.md":
            continue
        target = path.with_name("AGENTS.md")
        if not (path.is_symlink() and target.is_file() and path.resolve() == target.resolve()):
            findings.append(
                finding(
                    root, path, "TIDY002", "Make CLAUDE.md a symlink to the adjacent AGENTS.md."
                )
            )
    return findings


def documentation_indexes(root: Path) -> list[Finding]:
    files, directories = inventory(root)
    markdown_parents = {
        ancestor
        for p in files
        if p.suffix.lower() == ".md"
        for ancestor in p.parents
        if ancestor.is_relative_to(root)
    }
    return [
        finding(
            root,
            directory / "README.md",
            "TIDY003",
            "Add README.md to introduce and index this documentation directory.",
        )
        for directory in directories
        if "docs" in directory.relative_to(root).parts
        and (directory.name == "docs" or directory in markdown_parents)
        and not (directory / "README.md").is_file()
    ]


def valid_links(root: Path) -> list[Finding]:
    findings = []
    for source in documents(root):
        links, _ = parse(read(source, root))
        for href, line in links:
            destination = local(href)
            if destination is None:
                continue
            name, fragment = destination
            target = source.parent / name if name else source
            # Absolute web routes and targets outside this repository are outside scope.
            if not target.resolve().is_relative_to(root.resolve()):
                continue
            if not target.exists():
                message = f"Local link target does not exist: {href}"
            elif fragment and target.is_file() and target.suffix.lower() == ".md":
                if fragment in parse(read(target, root))[1]:
                    continue
                message = f"Markdown heading or anchor does not exist: {href}"
            else:
                continue
            findings.append(finding(root, source, "TIDY004", message, line))
    return findings


def reachable_documentation(root: Path) -> list[Finding]:
    files = documents(root)
    docs = {p.resolve(): p for p in files if "docs" in p.relative_to(root).parts[:-1]}
    if not docs:
        return []
    entry = root / "AGENTS.md"
    if not entry.is_file():
        return [
            finding(
                root, entry, "TIDY005", "Add a root AGENTS.md linking to the documentation index."
            )
        ]
    visited, queue = set(), [entry]
    while queue:
        source = queue.pop()
        resolved = source.resolve()
        if resolved in visited or not resolved.is_relative_to(root.resolve()):
            continue
        visited.add(resolved)
        for href, _ in parse(read(source, root), include_images=False)[0]:
            destination = local(href)
            if destination is None:
                continue
            name, _ = destination
            target = source.parent / name if name else source
            if not target.resolve().is_relative_to(root.resolve()):
                continue
            if target.is_dir():
                target = target / "README.md"
            if target.is_file() and target.suffix.lower() == ".md":
                queue.append(target)
    return [
        finding(root, path, "TIDY005", "Link this document from AGENTS.md or a reachable index.")
        for resolved, path in sorted(docs.items())
        if resolved not in visited
    ]


def untracked_installations(root: Path) -> list[Finding]:
    if not is_checkout(root):
        return []
    findings, directories = [], set()
    tracked = git(root, "ls-files", "-z", "--cached").stdout.split(b"\0")
    exposed = [
        Path(os.fsdecode(p))
        for p in git(root, "ls-files", "-z", "--others", "--exclude-standard").stdout.split(b"\0")
        if p and installed(Path(os.fsdecode(p)))
    ]
    for value in tracked:
        if not value:
            continue
        relative = Path(os.fsdecode(value))
        if installed(relative):
            findings.append(
                finding(
                    root,
                    root / relative,
                    "TIDY006",
                    "Untrack installed skills; track their source under skills/.",
                )
            )
            for i, part in enumerate(relative.parts[:-1]):
                if part in AGENT_DIRS and relative.parts[i + 1] == "skills":
                    directories.add(Path(*relative.parts[: i + 2]))
    # Installed folders are deliberately excluded from normal document discovery.
    for directory in inventory(root)[1]:
        for name in AGENT_DIRS:
            candidate = directory / name / "skills"
            if candidate.is_dir():
                directories.add(candidate.relative_to(root))
        if directory.name in AGENT_DIRS and (directory / "skills").is_dir():
            directories.add((directory / "skills").relative_to(root))
    for directory in sorted(directories):
        probe = directory / "__tidy_harness_ignore_probe__"
        result = git(root, "check-ignore", "--no-index", "--quiet", "--", str(probe))
        if result.returncode or any(p.is_relative_to(directory) for p in exposed):
            findings.append(
                finding(
                    root,
                    root / directory,
                    "TIDY006",
                    f"Ignore installed skills in Git: {directory.as_posix()}/",
                )
            )
    return findings


DEFINITIONS = (
    (
        "TIDY001",
        "brief-agent-instructions",
        "AGENTS.md must be at most 250 lines.",
        brief_instructions,
    ),
    (
        "TIDY002",
        "canonical-agent-instructions",
        "CLAUDE.md must link to AGENTS.md.",
        canonical_instructions,
    ),
    (
        "TIDY003",
        "documentation-indexes",
        "Documentation directories must have README.md indexes.",
        documentation_indexes,
    ),
    ("TIDY004", "valid-local-links", "Local Markdown links must resolve.", valid_links),
    (
        "TIDY005",
        "reachable-documentation",
        "Documentation must be reachable from root AGENTS.md.",
        reachable_documentation,
    ),
    (
        "TIDY006",
        "untracked-installed-skills",
        "Installed skills must be untracked and ignored.",
        untracked_installations,
    ),
)
RULES = tuple(
    Rule(
        id=code,
        name=name,
        description=description,
        filename="",
        scope=RuleScope.REPOSITORY,
        evaluate=evaluate,
    )
    for code, name, description, evaluate in DEFINITIONS
)
