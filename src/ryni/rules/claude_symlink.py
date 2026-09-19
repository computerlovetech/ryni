from pathlib import Path

from ryni.instruction_link import InstructionLink, InstructionLinkRepair
from ryni.instruction_link_local import LocalInstructionLinkRepair
from ryni.models import Finding, Rule


class FixClaudeSymlink:
    def __init__(self, repairer: InstructionLinkRepair) -> None:
        self.repairer = repairer

    def __call__(self, path: Path) -> None:
        self.repairer.repair(InstructionLink(path=path))


def evaluate(path: Path) -> list[Finding]:
    message = None
    if not path.is_symlink():
        message = "CLAUDE.md must be a symlink to its sibling AGENTS.md."
    elif path.resolve() != (path.parent / "AGENTS.md").resolve():
        message = "CLAUDE.md must point to its sibling AGENTS.md."
    elif not path.is_file():
        message = "CLAUDE.md must link to an existing AGENTS.md file."
    return [Finding(str(path), 1, "AGENT001", message)] if message else []


RULE = Rule(
    id="AGENT001",
    name="claude-agents-symlink",
    description=(
        "Wherever CLAUDE.md exists, it must be a symlink resolving to the sibling "
        "AGENTS.md file. AGENTS.md may exist without CLAUDE.md. Regular files, "
        "broken links, and links to another target are violations. "
        "With --fix, repair links when AGENTS.md exists and convert regular files "
        "only when their contents match AGENTS.md exactly.\n\n"
        "Example (in the directory containing AGENTS.md):\nln -s AGENTS.md CLAUDE.md"
    ),
    filename="CLAUDE.md",
    evaluate=evaluate,
    fix=FixClaudeSymlink(LocalInstructionLinkRepair()),
)
