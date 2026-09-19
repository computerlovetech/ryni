# Check with your agent

The `ryni-check` skill is the entry point for a complete harness convention check.
It runs deterministic rules, delegates every pending review to a sub-agent, and
returns one evidence-backed report.

## Install the skill

Install Rýni with your pack first. Then install its bundled skill into the directory
your agent discovers:

| Agent | Command, from your repository | Invocation |
| --- | --- | --- |
| Claude Code | `ryni skill install .claude/skills` | `/ryni-check` |
| Codex | `ryni skill install .agents/skills` | `$ryni-check` |
| Another skill-capable agent | `ryni skill install PATH_TO_SKILLS` | Use that agent's skill picker or invocation syntax. |

The directory defaults to `.agents/skills`. You may provide an absolute path to
install in a personal skills directory. Identical installations are a no-op;
customized or older skill content is never silently overwritten. Review the
existing file before removing it and reinstalling.

Discovery and invocation follow the host agent's conventions:
[Claude Code skills](https://code.claude.com/docs/en/skills) and
[Codex skills](https://developers.openai.com/codex/skills/). Reload your agent's
skills if the new entry is not visible.

## What happens

1. Your agent runs `ryni check . --output-format json` in the intended repository.
2. Rýni executes Python rules and prepares review tasks with exact targets,
   instructions, and pack provenance.
3. Your agent delegates **each** task to a sub-agent. It queues work when concurrency
   is limited and waits for every result.
4. Your agent combines deterministic findings, review findings, and coverage into
   a concise report.

No Rýni model provider, credentials, or agent service needs configuring. Reviews
use the host agent's capabilities and model budget.

## A useful result

```text
1 finding · deterministic checks complete · 1/1 agent reviews complete

Agent review — TEAM002 · team-harness
AGENTS.md:3 documents npm test, but package.json:4 only defines test:unit.
Update the instructions to match the available test command.
```

A review can pass, return findings, be not applicable with a reason, or remain
incomplete. Unsupported delegation, unavailable evidence, and failed sub-agents
must be reported as incomplete—not converted into a clean result.

The skill reviews files without changing them. It does not execute repository
scripts on a reviewer's behalf. Request fixes separately after reviewing findings.

## Scope and limitations

Pass paths or rule IDs in your request to narrow the check. Repository-scoped
rules still review the nearest repository root, even when given a single file.

The agent's report is the result of the review. Rýni does not store it or clear
pending tasks in subsequent CLI runs. Fresh runs prepare fresh reviews. Agent
findings are judgments backed by evidence, not deterministic guarantees.

If you use `uvx`, tell the agent the complete command prefix, including your pack's
`--with` argument. The skill preserves that environment rather than silently
falling back to a baseline-only installation.
