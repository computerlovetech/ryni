from pathlib import Path, PurePosixPath

import pytest
from fake_markdown_repository import InMemoryMarkdownRepository
from pydantic import ValidationError

from ryni.markdown_repository import MarkdownLocationOptions, MarkdownSnapshot, RyniConfig
from ryni.models import Finding
from ryni.rules.markdown_location import ALLOWED_NAMES, MarkdownLocationRule


def findings_for(name: str, **options: object) -> list[Finding]:
    snapshot = MarkdownSnapshot(
        files=(PurePosixPath(name),), options=MarkdownLocationOptions.model_validate(options)
    )
    return MarkdownLocationRule(InMemoryMarkdownRepository(snapshot)).evaluate(Path("/repo"))


@pytest.mark.parametrize(
    "name",
    [
        *sorted(ALLOWED_NAMES),
        "apps/api/README.md",
        "docs/design.md",
        "apps/api/docs/design.md",
        "temp/person/task/notes.md",
        "skills/review/references/guide.md",
        "apps/api/skills/review/guide.md",
        ".github/ISSUE_TEMPLATE/bug.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/PULL_REQUEST_TEMPLATE/change.md",
        ".github/copilot-instructions.md",
        ".github/instructions/python.instructions.md",
        ".github/instructions/api/python.instructions.md",
    ],
)
def test_default_exceptions(name: str) -> None:
    assert findings_for(name) == []


@pytest.mark.parametrize(
    "name",
    [
        "notes.md",
        "apps/api/temp/notes.md",
        "docs-old/notes.md",
        "src/readme.md",
        ".github/arbitrary.md",
        ".github/ISSUE_TEMPLATE/nested/bug.md",
    ],
)
def test_misplaced_markdown_is_reported(name: str) -> None:
    findings = findings_for(name)
    assert len(findings) == 1
    assert findings[0].rule_id == "DOC001"
    assert findings[0].path == str(Path("/repo") / name)


def test_additional_names_extend_defaults_anywhere() -> None:
    assert findings_for("apps/api/OWNERS.md", additional_allowed_names=["OWNERS.md"]) == []
    assert findings_for("README.md", additional_allowed_names=["OWNERS.md"]) == []
    assert findings_for("notes.md", additional_allowed_names=["OWNERS.md"])


@pytest.mark.parametrize(
    "name,allowed",
    [
        ("content/article.md", True),
        ("content/blog/article.md", True),
        ("apps/content/article.md", False),
        ("Content/article.md", False),
        (".changeset/change.md", True),
        (".changeset/nested/change.md", False),
        ("apps/api/ARCHITECTURE.md", True),
        ("apps/web/ARCHITECTURE.md", False),
    ],
)
def test_globs_are_anchored_and_segment_aware(name: str, allowed: bool) -> None:
    assert (
        not findings_for(
            name,
            additional_allowed_paths=[
                "content/**/*.md",
                ".changeset/*.md",
                "apps/api/ARCHITECTURE.md",
            ],
        )
    ) == allowed


@pytest.mark.parametrize(
    "options",
    [
        {"additional_allowed_names": "README.md"},
        {"additional_allowed_names": [1]},
        {"additional_allowed_names": ["dir/file.md"]},
        {"additional_allowed_names": ["*.md"]},
        {"additional_allowed_names": [""]},
        {"additional_allowed_paths": ["../*.md"]},
        {"additional_allowed_paths": ["/absolute/*.md"]},
        {"additional_allowed_paths": ["C:/absolute/*.md"]},
        {"additional_allowed_paths": ["dir\\file.md"]},
        {"additional_allowed_paths": [""]},
        {"additional_allowed_paths": ["dir/"]},
        {"additional_allowed_paths": "*.md"},
        {"allow_names": ["OWNERS.md"]},
    ],
)
def test_invalid_options_are_rejected(options: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        MarkdownLocationOptions.model_validate(options)


def test_unknown_rule_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RyniConfig.model_validate({"rules": {"markdown-locaton": {}}})
