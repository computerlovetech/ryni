import unicodedata
from pathlib import Path

from ryni.models import Finding, Rule
from ryni.rules.skill_frontmatter import read_frontmatter


def _text_field(path: Path, key: str) -> str | None:
    metadata, _ = read_frontmatter(path)
    value = metadata.get(key)
    # Missing or invalid fields are reported by SKILL001, without cascading findings.
    return value if isinstance(value, str) and value.strip() else None


def evaluate_name(path: Path) -> list[Finding]:
    value = _text_field(path, "name")
    if value is None:
        return []
    name = unicodedata.normalize("NFKC", value)
    if (
        len(name) > 64
        or name != name.lower()
        or not all(character.isalnum() or character == "-" for character in name)
        or name.startswith("-")
        or name.endswith("-")
        or "--" in name
    ):
        return [
            Finding(
                str(path),
                1,
                "SKILL002",
                "Use a skill name of 1–64 lowercase alphanumeric characters or hyphens, "
                "without leading, trailing, or consecutive hyphens.",
            )
        ]
    return []


def evaluate_directory(path: Path) -> list[Finding]:
    name = _text_field(path, "name")
    if name is None:
        return []
    # Preserve the discovery path, including symlinks; handle bare 'SKILL.md' too.
    directory = path.absolute().parent.name
    if unicodedata.normalize("NFKC", name) != unicodedata.normalize("NFKC", directory):
        return [
            Finding(
                str(path),
                1,
                "SKILL003",
                f"Skill name {name!r} must match its containing directory {directory!r}.",
            )
        ]
    return []


def evaluate_description(path: Path) -> list[Finding]:
    description = _text_field(path, "description")
    if description is not None and len(description) > 1024:
        return [
            Finding(
                str(path),
                1,
                "SKILL004",
                f"Shorten the skill description to at most 1024 characters "
                f"(currently {len(description)}).",
            )
        ]
    return []


NAME_RULE = Rule(
    id="SKILL002",
    name="skill-name",
    description=(
        "Skill names must contain 1–64 lowercase alphanumeric characters or hyphens, "
        "with no leading, trailing, or consecutive hyphens. Unicode names are supported; "
        "validation uses NFKC normalization. Required fields are checked by SKILL001."
    ),
    filename="SKILL.md",
    evaluate=evaluate_name,
)

DIRECTORY_RULE = Rule(
    id="SKILL003",
    name="skill-directory-match",
    description=(
        "The skill's name must match its containing directory name after Unicode NFKC "
        "normalization. The discovery path is used without resolving symlinks. "
        "Required fields are checked by SKILL001."
    ),
    filename="SKILL.md",
    evaluate=evaluate_directory,
)

DESCRIPTION_RULE = Rule(
    id="SKILL004",
    name="skill-description-length",
    description=(
        "A skill description must contain at most 1024 characters. Count the parsed YAML "
        "string, including whitespace and newlines, not its byte length or source notation. "
        "Required fields are checked by SKILL001."
    ),
    filename="SKILL.md",
    evaluate=evaluate_description,
)
