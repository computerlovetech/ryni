"""Jobs-oriented, deterministic team conventions. No agent reviews or auto-fixes."""

import re
from collections import defaultdict

from ryni.models import Finding, Rule, RulePack, RuleScope
from ryni.rules.skill_frontmatter import read_frontmatter

from .analysis import documents, inventory, local, parse, read


def finding(path, code, message, line=1):
    return Finding(str(path), line, code, message)


def entrypoint(root):
    if not any((root / name).is_file() for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md")):
        return [
            finding(
                root / "AGENTS.md",
                "TEAM001",
                "Add a root agent entry point with shared commands and guidance links.",
            )
        ]
    return []


def nonempty(root):
    return [
        finding(p, "TEAM002", "Replace the empty harness document with actionable guidance.")
        for p in inventory(root)
        if not read(p, root).strip()
    ]


def budget(root):
    findings = []
    for p in inventory(root):
        if p.name not in {
            "AGENTS.md",
            "AGENTS.override.md",
            "CLAUDE.md",
            "GEMINI.md",
            "copilot-instructions.md",
            ".cursorrules",
        }:
            continue
        text = read(p, root)
        if len(text.splitlines()) > 250 or len(text.encode("utf-8")) > 16384:
            findings.append(
                finding(
                    p,
                    "TEAM003",
                    "Keep always-loaded guidance within 250 lines and 16 KiB; link task details.",
                )
            )
    return findings


def skill_budget(root):
    return [
        finding(p, "TEAM004", "Keep SKILL.md within 500 lines; move detail to references.")
        for p in inventory(root)
        if p.name == "SKILL.md" and len(read(p, root).splitlines()) > 500
    ]


def conflict_markers(root):
    findings = []
    for p in documents(root):
        text = read(p, root)
        code_lines = parse(text).code_lines
        for number, line in enumerate(text.splitlines(), 1):
            if number not in code_lines and re.match(r"^(<<<<<<< |>>>>>>> |\|\|\|\|\|\|\| )", line):
                findings.append(finding(p, "TEAM005", "Resolve the Git conflict marker.", number))
    return findings


def links(root):
    findings = []
    for p in documents(root):
        for href, line in parse(read(p, root)).links:
            target = local(p, href, root)
            if target is not None and not target.exists():
                findings.append(finding(p, "TEAM006", f"Repair missing local link: {href}", line))
    return findings


def imports(root):
    findings = []
    for p in documents(root):
        for href, line in parse(read(p, root)).imports:
            target = local(p, href, root)
            if target is not None and not target.is_file():
                findings.append(finding(p, "TEAM007", f"Repair missing file import: {href}", line))
    return findings


def import_cycles(root):
    edges = {}
    for p in documents(root):
        edges[p.resolve()] = tuple(
            target.resolve()
            for href, _ in parse(read(p, root)).imports
            if (target := local(p, href, root)) is not None and target.is_file()
        )
    findings, done, active = [], set(), set()

    def visit(path):
        if path in active:
            findings.append(finding(path, "TEAM008", "Break the recursive @import cycle."))
            return
        if path in done:
            return
        active.add(path)
        for target in edges.get(path, ()):
            visit(target)
        active.remove(path)
        done.add(path)

    for path in sorted(edges):
        visit(path)
    return findings


def portable(root):
    return [
        finding(p, "TEAM009", "Replace the machine-specific home path with a portable path.", line)
        for p in inventory(root)
        for text, line in parse(read(p, root)).prose
        if re.search(r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)[\w.-]+[/\\]", text)
    ]


def aliases(root):
    findings = []
    for p in inventory(root):
        if p.name not in {"CLAUDE.md", "GEMINI.md"}:
            continue
        canonical = p.with_name("AGENTS.md")
        if canonical.is_file() and not p.is_symlink() and len(read(p, root).strip()) >= 200:
            if read(p, root).strip() == read(canonical, root).strip():
                findings.append(
                    finding(
                        p,
                        "TEAM010",
                        "Replace the duplicated adjacent AGENTS.md copy with a link/import or symlink.",
                    )
                )
    return findings


def inherited_duplicates(root):
    findings = []
    agents = {p.parent: p for p in inventory(root) if p.name == "AGENTS.md"}
    for folder, path in agents.items():
        paragraphs = {text for text, _ in parse(read(path, root)).prose if len(text) >= 160}
        for ancestor in folder.parents:
            if ancestor in agents:
                repeats = paragraphs & {
                    text for text, _ in parse(read(agents[ancestor], root)).prose
                }
                if repeats:
                    findings.append(
                        finding(
                            path,
                            "TEAM011",
                            f"Remove {len(repeats)} verbatim inherited paragraph(s) from {agents[ancestor]}.",
                        )
                    )
                    break
    return findings


def skill_metadata(root):
    findings = []
    for p in inventory(root):
        if p.name != "SKILL.md":
            continue
        metadata, errors = read_frontmatter(p)
        if errors:
            findings.extend(finding(p, "TEAM012", item.message, item.line) for item in errors)
            continue
        for key in ("name", "description"):
            if not isinstance(metadata.get(key), str) or not metadata[key].strip():
                findings.append(finding(p, "TEAM012", f"Provide a nonempty skill {key}."))
    return findings


def skill_identity(root):
    findings = []
    for p in inventory(root):
        if p.name != "SKILL.md":
            continue
        metadata, errors = read_frontmatter(p)
        name = metadata.get("name")
        if errors or not isinstance(name, str) or not name.strip():
            continue
        if (
            len(name) > 64
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
            or name != p.parent.name
        ):
            findings.append(
                finding(
                    p,
                    "TEAM013",
                    "Use a lowercase ASCII kebab-case skill name matching its directory, at most 64 chars.",
                )
            )
    return findings


def skill_description(root):
    findings = []
    for p in inventory(root):
        if p.name != "SKILL.md":
            continue
        metadata, errors = read_frontmatter(p)
        description = metadata.get("description")
        if not errors and isinstance(description, str) and len(description) > 1024:
            findings.append(
                finding(p, "TEAM014", "Keep skill discovery descriptions within 1024 chars.")
            )
    return findings


def skill_collisions(root):
    groups = defaultdict(list)
    for p in inventory(root):
        if p.name == "SKILL.md":
            metadata, errors = read_frontmatter(p)
            name = metadata.get("name")
            # Different vendor installations are separate discovery namespaces.
            parts = p.relative_to(root).parts
            if not errors and isinstance(name, str) and "skills" in parts:
                namespace = parts[: parts.index("skills") + 1]
                groups[namespace, name].append(p)
    return [
        finding(p, "TEAM015", f"Skill name {name!r} collides within {'/'.join(namespace)}.")
        for (namespace, name), paths in groups.items()
        if len(paths) > 1
        for p in paths
    ]


def linked_labels(root):
    findings = []
    for p in inventory(root):
        # Narrow, explicit placeholder convention, not a semantic clarity judgement.
        for text, line in parse(read(p, root)).prose:
            if re.search(r"\b(?:TODO|FIXME):?\s+(?:fill|write|add|replace)\b", text):
                findings.append(
                    finding(p, "TEAM016", "Complete the unfinished harness placeholder.", line)
                )
    return findings


def skill_body(root):
    findings = []
    for p in inventory(root):
        if p.name == "SKILL.md":
            text = read(p, root)
            if not parse(text).prose and not parse(text).links and "```" not in text:
                findings.append(finding(p, "TEAM017", "Add the skill procedure after frontmatter."))
    return findings


def ignored_reference(root):
    # Do not mandate Git ownership: report only explicit personal local-file imports.
    return [
        finding(p, "TEAM018", "Replace the personal @import with shared repository guidance.", line)
        for p in inventory(root)
        for href, line in parse(read(p, root)).imports
        if href.startswith(("~/", "/Users/", "/home/"))
    ]


CHECKS = (
    ("entry-point", entrypoint),
    ("nonempty-guidance", nonempty),
    ("instruction-budget", budget),
    ("skill-budget", skill_budget),
    ("merge-conflicts", conflict_markers),
    ("local-links", links),
    ("local-imports", imports),
    ("import-cycles", import_cycles),
    ("portable-paths", portable),
    ("canonical-aliases", aliases),
    ("inherited-duplication", inherited_duplicates),
    ("skill-metadata", skill_metadata),
    ("skill-identity", skill_identity),
    ("skill-discovery-budget", skill_description),
    ("skill-name-collisions", skill_collisions),
    ("unfinished-guidance", linked_labels),
    ("skill-procedure", skill_body),
    ("shared-imports", ignored_reference),
)
DESCRIPTIONS = (
    "Provide a root AGENTS.md, CLAUDE.md or GEMINI.md for shared project guidance.",
    "Discovered harness documents must contain non-whitespace text.",
    "Keep named always-loaded instructions within 250 lines and 16 KiB UTF-8.",
    "Keep SKILL.md within 500 lines; link supporting references.",
    "Resolve Git start/end/base conflict markers outside Markdown code examples.",
    "Local CommonMark links/images reachable from harness files must exist; fragments are not checked.",
    "Standalone file @imports must exist; use ./ for extensionless paths. GitHub mentions are ignored.",
    "Break cycles between standalone local Markdown @imports.",
    "Avoid literal machine-specific home paths in prose outside code examples.",
    "Replace identical adjacent vendor instruction copies of at least 200 characters with pointers.",
    "Avoid verbatim AGENTS.md paragraphs of at least 160 characters repeated from an ancestor.",
    "Start SKILL.md with YAML frontmatter containing nonempty string name and description fields.",
    "Use an ASCII kebab-case skill name matching the directory, at most 64 characters.",
    "Keep parsed skill descriptions within 1024 characters.",
    "Skill names must be unique within each skills-directory namespace; vendors are separate.",
    "Complete prose placeholders beginning TODO/FIXME followed by fill, write, add or replace.",
    "Supply body prose, links or a fenced procedure after skill frontmatter.",
    "Keep standalone @imports out of personal home directories; use shared repository guidance.",
)

PACK = RulePack(
    "team-harness",
    "Keep team guidance discoverable, lean, portable and maintained.",
    tuple(
        Rule(
            f"TEAM{i:03}",
            name,
            DESCRIPTIONS[i - 1],
            "",
            function,
            RuleScope.REPOSITORY,
        )
        for i, (name, function) in enumerate(CHECKS, 1)
    ),
)
