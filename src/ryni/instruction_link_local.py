from pathlib import Path
from tempfile import TemporaryDirectory

from ryni.instruction_link import InstructionLink


class LocalInstructionLinkRepair:
    def repair(self, link: InstructionLink) -> None:
        path = link.path
        target = path.parent / "AGENTS.md"
        if not target.is_file():
            return
        # AGENTS.md must not point back to the file we are about to replace.
        if target.resolve() == path.parent.resolve() / path.name:
            return
        if not path.is_symlink():
            if not path.is_file() or path.read_bytes() != target.read_bytes():
                return
        # Prepare the replacement before touching the original; replace the link,
        # never its target. A failed replacement leaves the original in place.
        with TemporaryDirectory(prefix=".ryni-fix-", dir=path.parent) as directory:
            replacement = Path(directory) / "CLAUDE.md"
            replacement.symlink_to("AGENTS.md")
            replacement.replace(path)
