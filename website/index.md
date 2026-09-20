# Rýni

**A linter for your agent harness.**

Harness engineering is hard. Keeping a team aligned on it is harder. Rýni checks
your `AGENTS.md`, instructions, skills, and Markdown docs against shared
conventions, so your agents get a consistent and coherent working environment.

- 🔍 **Lint your harness.** Catch structural issues with deterministic checks.
- 📝 **Review your markdown docs.** Structure non-deterministic checks that require judgment.
- 📦 **Share your conventions.** Turn your team’s standards into rule packs you can use across repositories.

## Two kinds of check, one rule pack

=== "Deterministic check"

    Require an `AGENTS.md` at the repository root.

    ```python
    from pathlib import Path

    from ryni.models import Finding, Rule, RuleScope


    def check_instructions(root: Path) -> list[Finding]:
        path = root / "AGENTS.md"
        if path.is_file():
            return []
        return [Finding(str(path), 1, "TEAM001", "Add an AGENTS.md at the repository root.")]


    RULE = Rule(
        id="TEAM001",
        name="require-agent-instructions",
        description="Every repository must have a root AGENTS.md.",
        filename="",
        scope=RuleScope.REPOSITORY,
        evaluate=check_instructions,
    )
    ```

=== "Agent review"

    Ask your coding agent to find contradictory instructions in `AGENTS.md`.

    ```python
    from ryni.models import ReviewRule

    RULE = ReviewRule(
        id="TEAM002",
        name="no-contradictory-instructions",
        description="AGENTS.md must not contain contradictory instructions.",
        instructions="""
    Find contradictory instructions in the root AGENTS.md.
    Cite both sides of each conflict, accounting for scope and exceptions.
    """,
    )
    ```

**[Build your first rule pack →](first-rule-pack.md)**
