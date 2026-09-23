from pathlib import Path

from ryni.cache import cached_per_check
from ryni.models import Finding, Rule


@cached_per_check
def read_frontmatter(path: Path) -> tuple[dict, list[Finding]]:
    """Read metadata; structural failures belong to SKILL001 alone."""
    def finding(message: str, line: int = 1) -> Finding:
        return Finding(str(path), line, "SKILL001", message)

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0] != "---":
        return {}, [finding("Start SKILL.md with YAML frontmatter delimited by ---.")]
    end = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
    if end is None:
        return {}, [finding("Close YAML frontmatter with a --- line.")]
    import yaml

    try:
        metadata = yaml.safe_load("\n".join(lines[1:end]) + "\n")
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        line = min(mark.line + 2, end + 1) if mark else 1
        return {}, [finding("Frontmatter must contain valid YAML.", line)]
    if not isinstance(metadata, dict):
        return {}, [finding("Frontmatter must be a YAML mapping.")]
    return metadata, []


def evaluate(path: Path) -> list[Finding]:
    metadata, errors = read_frontmatter(path)
    if errors:
        return errors
    return [
        Finding(str(path), 1, "SKILL001", f"Frontmatter field '{key}' must be a non-empty string.")
        for key in ("name", "description")
        if not isinstance(metadata.get(key), str) or not metadata[key].strip()
    ]


RULE = Rule(
    id="SKILL001",
    name="skill-frontmatter",
    description=(
        "SKILL.md must begin with YAML frontmatter between exact --- delimiter lines. "
        "The YAML must be a mapping containing non-empty string fields 'name' and "
        "'description'. Additional fields are allowed. This rule checks basic structure, "
        "not naming conventions or description quality.\n\n"
        "Example:\n---\nname: review-migrations\n"
        "description: Use when reviewing database migrations.\n---"
    ),
    filename="SKILL.md",
    evaluate=evaluate,
)
