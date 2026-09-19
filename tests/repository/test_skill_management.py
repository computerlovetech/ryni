from pathlib import Path

from ryni.rules.skill_management import SkillManagementRules
from ryni.skill_repository import IgnoreStatus, InstallationStatus, SkillLayout, SkillSource

from .fake_repository import InMemorySkillRepository


def test_ignore_rule_reports_missing_coverage_and_tracked_installations() -> None:
    repository = InMemorySkillRepository(
        ignores=(
            IgnoreStatus(
                path=Path("/repo/.claude/skills"), ignored_by_gitignore=False, tracked=False
            ),
            IgnoreStatus(
                path=Path("/repo/.agents/skills"), ignored_by_gitignore=True, tracked=True
            ),
            IgnoreStatus(
                path=Path("/repo/.cursor/skills"), ignored_by_gitignore=True, tracked=False
            ),
        )
    )
    findings = SkillManagementRules(repository).ignored_installations(Path("/repo"))
    assert [(finding.path, finding.rule_id) for finding in findings] == [
        ("/repo/.claude/skills", "SKILL002"),
        ("/repo/.agents/skills", "SKILL002"),
    ]
    assert "Ignore" in findings[0].message
    assert "tracked" in findings[1].message


def test_location_rule_only_reports_sources_outside_skills() -> None:
    repository = InMemorySkillRepository(
        layout=SkillLayout(
            sources=(
                SkillSource(
                    path=Path("/repo/skills/category/example/SKILL.md"),
                    scope=Path("/repo"),
                    under_skills=True,
                ),
                SkillSource(
                    path=Path("/repo/docs/example/SKILL.md"),
                    scope=Path("/repo"),
                    under_skills=False,
                ),
            )
        )
    )
    findings = SkillManagementRules(repository).source_locations(Path("/repo"))
    assert [(finding.path, finding.rule_id) for finding in findings] == [
        ("/repo/docs/example/SKILL.md", "SKILL003"),
    ]


def test_installation_rule_preserves_problems_for_each_source() -> None:
    source = SkillSource(
        path=Path("/repo/skills/example/SKILL.md"), scope=Path("/repo"), under_skills=True
    )
    misplaced = SkillSource(
        path=Path("/repo/docs/SKILL.md"), scope=Path("/repo"), under_skills=False
    )
    repository = InMemorySkillRepository(
        layout=SkillLayout(sources=(source, misplaced)),
        installations={
            source: InstallationStatus(problems=("Missing lock entry.", "Missing Claude install."))
        },
    )
    findings = SkillManagementRules(repository).local_installations(Path("/repo"))
    assert [finding.message for finding in findings] == [
        "Missing lock entry.",
        "Missing Claude install.",
    ]
    assert all(finding.rule_id == "SKILL004" for finding in findings)
