<picture>
  <source media="(prefers-color-scheme: dark)" srcset="website/assets/ryni-wordmark-dark.svg">
  <img src="website/assets/ryni-wordmark-light.svg" alt="Rýni" width="180" height="48">
</picture>

Rýni is a command-line linter for agent instructions and skills. It includes
checks for `SKILL.md` frontmatter, names, directory matching, and description
length. Install rule packs to check additional files and conventions.

[Documentation](https://computerlovetech.github.io/ryni/) · [Rule pack tutorial](website/first-rule-pack.md)

## Get started

Requires Python 3.14 or later. From your project directory:

```bash
uv add --dev ryni
uv run ryni check .
```

Run `uv run ryni rule` to list active rules, or `uv run ryni rule SKILL004`
to explain one. For additional checks, install a rule pack such as
[tidy-harness](examples/tidy-harness/README.md) with `uv add --dev tidy-harness`.
Installed rules are active automatically.

The terminal report groups findings by file and shows checked file counts and
elapsed time:

```text
Rýni  check

.agents/skills/example/SKILL.md
  1  SKILL004  Shorten the skill description to at most 1024 characters
               (currently 1461).

Changes needed
1 finding
142 files checked · 0.28s
```

Use `--output-format json` for structured output or `--output-format compact`
for one-line diagnostics. Use `--deterministic` to exclude agent reviews.
See the [command reference](https://computerlovetech.github.io/ryni/#check-options)
for options, exit codes, and report details.

## Run with your agent

Install the bundled skill for your agent, then invoke it in the same repository:

| Agent | Install in your terminal | Send in your agent |
| --- | --- | --- |
| Claude Code | `uv run ryni skill install .claude/skills` | `/ryni-check` |
| Codex | `uv run ryni skill install .agents/skills` | `$ryni-check` |

The skill runs deterministic checks, delegates reviews to sub-agents, and combines
the findings. Your agent must support sub-agents to complete reviews. Rýni itself
runs no model and needs no API key.

## Write a rule pack

A rule pack is a Python package containing checks and optional review instructions.
Follow the [rule pack tutorial](website/first-rule-pack.md) to create and install one.

To write rules with an agent, install the bundled authoring skill:

```bash
uv run ryni skill install .agents/skills --name ryni-rule-author
```

Use `.claude/skills` for Claude Code. Invoke `ryni-rule-author` to build or extend
a pack with shared analysis, tests, and measured performance. To inspect the cost
of installed deterministic checks:

```bash
uv run ryni check . --deterministic --profile
```

- [Usage and command reference](website/index.md)
- [Efficient rule packs and profiling](website/efficient-rule-packs.md)
- [tidy-harness rules](examples/tidy-harness/README.md)
- [Research-informed team-harness rules](examples/team-harness/README.md)
- [Twelve-repository performance study](benchmarks/harness-hygiene/RESULTS.md)

## Contributing

```bash
uv run pytest tests
uv run --with-editable . --with-editable ./examples/tidy-harness pytest examples/tidy-harness/tests
uv run ruff check .
uv run --group docs mkdocs build --strict
uv run --group docs mkdocs serve
```

Maintainers: see [the release guide](docs/releasing.md) for Rýni's PyPI
releases, dry runs, and the `ryni-release` skill.
