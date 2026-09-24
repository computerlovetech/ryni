# Rýni

Rýni is a command-line linter for agent instructions and skills. It runs Python
checks and prepares review tasks for your coding agent.

Built-in rules check `SKILL.md` frontmatter, names, directory matching, and
description length. Checks for other files and conventions come from installed
rule packs. Rýni itself runs no model and needs no API key.

## Get started

Requires Python 3.14 or later. From your project directory:

```bash
uv add --dev ryni
uv run ryni check .
```

To add more checks, install a rule pack such as
[tidy-harness](https://github.com/computerlovetech/ryni/tree/main/examples/tidy-harness):

```bash
uv add --dev tidy-harness
```

Installed rules are active automatically. Commit `pyproject.toml` and `uv.lock`
to record the same dependencies for your team.

## Inspect rules

```bash
uv run ryni rule
uv run ryni rule SKILL004
```

The first command lists active rules and their source packs. The second explains
one rule. Use `--output-format json` on either command for structured output.

## Check options

`ryni check` accepts files or directories and defaults to the current directory.

```bash
uv run ryni check .agents/skills
uv run ryni check . --select SKILL001,SKILL004
uv run ryni check . --deterministic --output-format json
```

| Option | Behavior |
| --- | --- |
| `--select ID,ID` | Run only the specified rule IDs. |
| `--fix` | Apply available deterministic fixes, then recheck. Modifies files. |
| `--deterministic` | Exclude agent reviews; run only Python checks. |
| `--output-format text` | Group findings by file; show counts and elapsed time. The default. |
| `--output-format compact` | Print one-line `path:line: rule message` diagnostics. |
| `--output-format json` | Report checked targets, findings, errors, and pending reviews as JSON. |
| `--profile` | Add rule timings and shared-helper cache statistics. |

### Report

Example text output:

```text
Rýni  check

.agents/skills/example/SKILL.md
  1  SKILL004  Shorten the skill description to at most 1024 characters
               (currently 1461).

Changes needed
1 finding
142 files checked · 0.28s
```

Counts cover unique targets that completed deterministic checks. Directory
targets are listed separately; the count is not every file encountered during
traversal. Elapsed time includes rule loading, discovery, checks, and any
fix/recheck, excluding process startup and report rendering.

Color respects `NO_COLOR`. Redirected output is plain text. Execution errors go
to stderr in text and compact output; JSON includes them in `errors`.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No findings, errors, or pending reviews. |
| `1` | Findings remain. |
| `2` | An execution, configuration, or usage error occurred. |
| `3` | No findings or errors, but agent reviews remain pending. |

Errors take precedence over findings; findings take precedence over pending
reviews. A clean result only covers the selected checks. An empty scan can also
exit `0`; check the reported file count.

## Run agent reviews

The CLI prepares review tasks but does not execute them. Install the bundled
skill, then invoke it in your coding agent from the same repository:

| Agent | Install in your terminal | Send in your agent |
| --- | --- | --- |
| Claude Code | `uv run ryni skill install .claude/skills` | `/ryni-check` |
| Codex | `uv run ryni skill install .agents/skills` | `$ryni-check` |

The skill runs deterministic checks, delegates pending reviews to sub-agents,
and combines the findings. Your agent must support sub-agents. Use
`--deterministic` when you only want Python checks, such as in CI.

## Write rules

- [Your first rule pack](first-rule-pack.md): create a Python check, package it,
  and add an agent review.
- [Efficient rule packs](efficient-rule-packs.md): share parsing work between
  checks and profile execution.
