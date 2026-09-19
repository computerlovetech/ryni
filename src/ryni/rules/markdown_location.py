from pathlib import Path, PurePosixPath

from ryni.markdown_repository import MarkdownLocationOptions, MarkdownRepository
from ryni.markdown_repository_local import LocalMarkdownRepository
from ryni.models import Finding, Rule, RuleScope
from ryni.skill_repository import RepositoryRoot

ALLOWED_NAMES = frozenset(
    {
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "SKILL.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "LICENSE.md",
        "LICENCE.md",
        "NOTICE.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "SUPPORT.md",
        "GOVERNANCE.md",
        "MAINTAINERS.md",
        "AUTHORS.md",
        "CONTRIBUTORS.md",
    }
)
ALLOWED_PATHS = (
    ".github/ISSUE_TEMPLATE/*.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/PULL_REQUEST_TEMPLATE/*.md",
    ".github/copilot-instructions.md",
    ".github/instructions/**/*.instructions.md",
)


def is_allowed(path: PurePosixPath, options: MarkdownLocationOptions) -> bool:
    return (
        "docs" in path.parts[:-1]
        or "skills" in path.parts[:-1]
        or path.parts[0] == "temp"
        or path.name in ALLOWED_NAMES
        or path.name in options.additional_allowed_names
        or any(
            path.full_match(pattern, case_sensitive=True)
            for pattern in (*ALLOWED_PATHS, *options.additional_allowed_paths)
        )
    )


class MarkdownLocationRule:
    def __init__(self, repository: MarkdownRepository) -> None:
        self.repository = repository

    def evaluate(self, path: Path) -> list[Finding]:
        snapshot = self.repository.inspect(RepositoryRoot(path=path))
        return [
            Finding(
                str(path / file),
                1,
                "DOC001",
                "Keep Markdown under docs/ or root temp/, or add an exception in "
                "ryni.toml [rules.markdown-location].",
            )
            for file in snapshot.files
            if not is_allowed(file, snapshot.options)
        ]


RULE = Rule(
    id="DOC001",
    name="markdown-location",
    description=(
        "Markdown files belong under docs/ (at any scope) or repository-root temp/. "
        "Conventional filenames, skills/ sources, and standard GitHub Markdown paths "
        "are allowed. Extend defaults with additional_allowed_names and "
        "additional_allowed_paths in ryni.toml [rules.markdown-location]. "
        "Path globs are relative to the repository root. No automatic fix.\n\n"
        "Example: apps/api/docs/architecture.md"
    ),
    filename="",
    evaluate=MarkdownLocationRule(LocalMarkdownRepository()).evaluate,
    scope=RuleScope.REPOSITORY,
)
