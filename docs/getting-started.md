# Getting started

Rýni requires Python 3.14 or later. Use [uv](https://docs.astral.sh/uv/) to install it:

```bash
uv tool install ryni
ryni check .
```

Or run it without a persistent installation:

```bash
uvx ryni check .
```

## Your first finding

Given a `skills/review/SKILL.md` containing only a heading:

```markdown
# Review changes
```

Rýni reports:

```text
skills/review/SKILL.md:1: SKILL001 Start SKILL.md with YAML frontmatter delimited by ---.
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

When a pack author publishes a package, install it alongside Rýni in the same tool
environment. Here `your-team-rules` is a placeholder for that package's name:

```bash
uv tool install --with your-team-rules ryni
ryni rule
ryni check .
```

Every installed rule is active. See [adopting packs](adopting-packs.md) for version
pinning and a runnable local example.

## Run the full check in your agent

Install the bundled skill into your agent's skills directory once per repository:

```bash
ryni skill install .claude/skills
```

In Claude Code, invoke `/ryni-check`. For Codex, install into `.agents/skills` and
invoke `$ryni-check`. Your agent must support sub-agents to complete review rules.
See [agent checks](agent-checks.md) for the complete workflow and supported paths.

Installing the CLI does not silently modify repositories or global agent settings.
The skill installation places the agent entry point; it does not select or activate
rules.
