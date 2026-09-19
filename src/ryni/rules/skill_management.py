from pathlib import Path

from ryni.models import Finding, Rule, RuleScope
from ryni.skill_repository import RepositoryRoot, SkillRepository
from ryni.skill_repository_local import LocalSkillRepository


class SkillManagementRules:
    def __init__(self, repository: SkillRepository) -> None:
        self.repository = repository

    def ignored_installations(self, path: Path) -> list[Finding]:
        root = RepositoryRoot(path=path)
        layout = self.repository.layout(root)
        findings: list[Finding] = []
        for status in self.repository.ignores(root, layout):
            if not status.ignored_by_gitignore:
                findings.append(
                    Finding(
                        str(status.path),
                        1,
                        "SKILL002",
                        "Ignore this installed-skills directory in .gitignore; ignoring its parent is also valid.",
                    )
                )
            if status.tracked:
                findings.append(
                    Finding(
                        str(status.path),
                        1,
                        "SKILL002",
                        "Installed skills are tracked by Git; remove them from the index and keep them ignored.",
                    )
                )
        return findings

    def source_locations(self, path: Path) -> list[Finding]:
        layout = self.repository.layout(RepositoryRoot(path=path))
        return [
            Finding(
                str(source.path),
                1,
                "SKILL003",
                "Keep locally owned skills under a skills/ directory; nested categories are allowed.",
            )
            for source in layout.sources
            if not source.under_skills
        ]

    def local_installations(self, path: Path) -> list[Finding]:
        layout = self.repository.layout(RepositoryRoot(path=path))
        return [
            Finding(str(source.path), 1, "SKILL004", problem)
            for source in layout.sources
            if source.under_skills
            for problem in self.repository.installation(source).problems
        ]


_checks = SkillManagementRules(LocalSkillRepository())

IGNORED_INSTALLATIONS = Rule(
    id="SKILL002",
    name="installed-skills-gitignored",
    description=(
        "Installed skills for configured agents must be covered by repository .gitignore rules "
        "and must not be tracked. Parent-directory patterns are valid. Git is required.\n\n"
        "Example: .claude/ or .claude/skills/"
    ),
    filename="",
    evaluate=_checks.ignored_installations,
    scope=RuleScope.REPOSITORY,
)
SOURCE_LOCATIONS = Rule(
    id="SKILL003",
    name="local-skills-source-location",
    description=(
        "Local SKILL.md files must be under a directory named skills/. "
        "Installed agent skills are excluded.\n\nExample: apps/api/skills/review/python/SKILL.md"
    ),
    filename="",
    evaluate=_checks.source_locations,
    scope=RuleScope.REPOSITORY,
)
LOCAL_INSTALLATIONS = Rule(
    id="SKILL004",
    name="local-skills-installed",
    description=(
        "Local skills need a local-source skills-lock.json entry and matching installed SKILL.md "
        "files for agents configured in the source scope. Copies and symlinks are accepted. "
        "This checks installation evidence, not command history.\n\n"
        "Example: npx skills add ./skills --skill '*' --agent claude-code --agent codex --full-depth -y"
    ),
    filename="",
    evaluate=_checks.local_installations,
    scope=RuleScope.REPOSITORY,
)
