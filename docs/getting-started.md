# Getting started

Rýni requires Python 3.14 or later. In a shared repository, use
[uv](https://docs.astral.sh/uv/) to add it as a development dependency:

```bash
uv add --dev ryni
uv run ryni check .
```

Commit `pyproject.toml` and `uv.lock` so the team can install the same versions.
If your repository has no `pyproject.toml`, use `uv init --bare` first.
For a quick trial outside a project environment, use `uvx ryni check .`.

## Your first finding

Given a `skills/review-changes/SKILL.md` containing only a heading:

```markdown
# Review changes
```

Rýni reports:

```text
skills/review-changes/SKILL.md:1: SKILL001 Start SKILL.md with YAML frontmatter delimited by ---.
1 target checked · 1 finding
```

Add the metadata and rerun:

```markdown
---
name: review-changes
description: Review changes for correctness and missing tests.
---

# Review changes
```

## Adopt your team's policy

Add your team's published rule pack as a development dependency too.
Here `your-team-rules` is a placeholder for that package's name:

```bash
uv add --dev your-team-rules
uv run ryni rule
uv run ryni check .
```

Every installed rule is active. See [adopting packs](adopting-packs.md) for
the shared setup, standalone alternatives, and a runnable local example.

## Run the full check in your agent

Install the bundled skill into your agent's skills directory once per repository:

```bash
uv run ryni skill install .claude/skills
```

In Claude Code, invoke `/ryni-check`. For Codex, install into `.agents/skills` and
invoke `$ryni-check`. Your agent must support sub-agents to complete review rules.
Tell your agent to use `uv run ryni` so it loads the project's packs.
See [agent checks](agent-checks.md) for the complete workflow and supported paths.

Installing the CLI does not silently modify repositories or global agent settings.
The skill installation places the agent entry point; it does not select or activate
rules.
