from pathlib import Path

from ryni.models import Finding, ReviewRule, Rule, RulePack, RuleScope


def check_instructions(root: Path) -> list[Finding]:
    path = root / "AGENTS.md"
    if path.is_file() and path.read_text(encoding="utf-8").strip():
        return []
    return [Finding(str(path), 1, "TEAM001", "Add AGENTS.md with project setup instructions.")]


PACK = RulePack(
    name="team-harness",
    description="Give agents an explicit starting point and accurate testing instructions.",
    rules=(
        Rule(
            id="TEAM001",
            name="project-instructions",
            description="The repository must contain a nonempty root AGENTS.md.",
            filename="",
            scope=RuleScope.REPOSITORY,
            evaluate=check_instructions,
        ),
        ReviewRule(
            id="TEAM002",
            name="accurate-test-instructions",
            description="Documented test commands must agree with the repository's tooling.",
            instructions=(
                "Read the root AGENTS.md and manifests or task definitions referenced by its "
                "test instructions. Report a violation only when a documented command directly "
                "contradicts those definitions, such as an npm script that does not exist. "
                "Cite both the instruction and the conflicting definition. Do not execute "
                "commands or infer that an unfamiliar command is invalid. If no test commands "
                "are documented, mark this review not_applicable; missing instructions are "
                "outside this rule. If verification needs unavailable files or execution, "
                "mark the review incomplete and explain what is missing."
            ),
        ),
    ),
)
