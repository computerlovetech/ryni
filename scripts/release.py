"""Validate Rýni release metadata and extract GitHub release notes."""

import argparse
from datetime import date
from pathlib import Path
import re
import tomllib

from packaging.version import Version


VERSION_PATTERN = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:(?:a|b|rc)[0-9]+)?"


def release_metadata(root: Path, tag: str | None = None) -> tuple[str, str]:
    core = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    version = core["version"]
    if not re.fullmatch(VERSION_PATTERN, version) or str(Version(version)) != version:
        raise ValueError("Use X.Y.Z or a canonical aN, bN, or rcN prerelease version.")
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"Tag must be v{version}, got {tag!r}.")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    section = version if tag else "Unreleased"
    headings = list(re.finditer(r"^## (.+)$", changelog, re.MULTILINE))
    matches = [
        i
        for i, heading in enumerate(headings)
        if heading[1] == f"[{section}]" or heading[1].startswith(f"[{section}] - ")
    ]
    if len(matches) != 1:
        raise ValueError(f"CHANGELOG.md must contain exactly one [{section}] section.")
    index = matches[0]
    heading = headings[index]
    if tag:
        dated_heading = re.fullmatch(
            rf"\[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})", heading[1]
        )
        if not dated_heading:
            raise ValueError(f"Expected changelog heading: ## [{version}] - YYYY-MM-DD")
        date.fromisoformat(dated_heading[1])
    end = headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
    notes = changelog[heading.end() : end].strip()
    if tag and not any(line.strip() and not line.startswith("#") for line in notes.splitlines()):
        raise ValueError(f"Changelog section [{version}] must contain release notes.")
    return version, notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tag", help="Validate an actual release; omit for a branch dry run.")
    parser.add_argument("--notes-file", type=Path)
    args = parser.parse_args()
    try:
        version, notes = release_metadata(args.root, args.tag)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"Release validation failed: {error}\n")
    if args.notes_file:
        args.notes_file.write_text(notes + "\n", encoding="utf-8")
    print(version)


if __name__ == "__main__":
    main()
