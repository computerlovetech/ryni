# Your first rule pack

Create a deterministic check, package it, then add a review for your coding agent.

## Create a deterministic rule

Require an `AGENTS.md` at the repository root:

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

The function receives the repository root and returns findings—or an empty list
when the check passes. The `Rule` gives the check an identity and tells Rýni when
to run it.

### Share expensive reads between checks

For rules that inspect the same files, decorate shared discovery, reading or
parsing helpers with `ryni.cache.cached_per_check`:

```python
from ryni.cache import cached_per_check


@cached_per_check
def read_document(path: Path) -> str:
    return path.read_text(encoding="utf-8")
```

Calls with the same arguments reuse their result during one check run. Arguments
must be hashable; treat returned data as read-only. The cache is discarded after
the run and cleared after every attempted fix, including failed fixes. Direct
calls outside the engine are not cached. Keep rule evaluation read-only and put
edits in the rule's `fix` function so later checks see fresh data. Do not decorate
rule evaluation or fix functions.

See [Efficient rule packs](efficient-rule-packs.md) for composing shared analysis,
profiling a complete pack, and using the bundled rule-authoring skill.

## Put it in a rule pack

A rule pack is a Python package. Save the rule above in `require_instructions.py`:

```text
team-rules/
├── pyproject.toml
└── src/
    └── team_rules/
        ├── __init__.py
        └── require_instructions.py   # The rule above
```

Bundle it in `src/team_rules/__init__.py`:

```python
from ryni.models import RulePack

from .require_instructions import RULE

PACK = RulePack(
    name="team-rules",
    description="Our team's agent harness conventions.",
    rules=(RULE,),
)
```

Register the pack in `pyproject.toml` so Rýni discovers it when installed:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "team-rules"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["ryni>=0.1.1"]

[project.entry-points."ryni.rules"]
team = "team_rules:PACK"

[tool.hatch.build.targets.wheel]
packages = ["src/team_rules"]
```

## Install and run

From the repository you want to check, add Rýni and your rule pack as development
dependencies. Here, `../team-rules` points to the pack you just created:

```bash
uv add --dev ryni ../team-rules
uv run ryni check .
```

Installed rules are active automatically. If the repository has no `AGENTS.md`,
your rule reports:

```text
AGENTS.md
  1  TEAM001  Add an AGENTS.md at the repository root.
```

Add the file and rerun the check. Commit `pyproject.toml` and `uv.lock` to record
the team's dependencies; anyone installing them will also need access to the pack.

## Create a non-deterministic rule

Check `AGENTS.md` for contradictory instructions with a `ReviewRule`.
Save this as `src/team_rules/contradictions.py`:

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

Add it alongside the deterministic rule in `src/team_rules/__init__.py`:

```python
from ryni.models import RulePack

from .require_instructions import RULE as REQUIRE_INSTRUCTIONS
from .contradictions import RULE as CONTRADICTIONS

PACK = RulePack(
    name="team-rules",
    description="Our team's agent harness conventions.",
    rules=(REQUIRE_INSTRUCTIONS, CONTRADICTIONS),
)
```

## Run with your agent

`ryni check` prepares reviews; your agent completes them with the `ryni-check`
skill. From the repository you want to check, refresh the pack and install the skill:

=== "Claude Code"

    ```bash
    uv add --dev --editable ../team-rules
    uv run ryni skill install .claude/skills
    ```

    Open Claude Code in this repository and send:

    ```text
    /ryni-check
    ```

=== "Codex"

    ```bash
    uv add --dev --editable ../team-rules
    uv run ryni skill install .agents/skills
    ```

    Open Codex in this repository and send:

    ```text
    $ryni-check
    ```

The skill runs deterministic checks, delegates reviews to sub-agents, and reports
the combined findings. Your agent must support sub-agents to complete reviews.
