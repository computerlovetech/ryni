<picture>
  <source media="(prefers-color-scheme: dark)" srcset="website/assets/ryni-wordmark-dark.svg">
  <img src="website/assets/ryni-wordmark-light.svg" alt="Rýni" width="180" height="48">
</picture>

**A linter for your agent harness.**

[Documentation](https://computerlovetech.github.io/ryni/)

Harness engineering is hard. Keeping a team aligned on it is harder. Rýni checks
your `AGENTS.md`, instructions, skills, and Markdown docs against shared
conventions, so your agents get a consistent and coherent working environment.

- 🔍 **Lint your harness.** Catch structural issues with deterministic checks.
- 📝 **Review your markdown docs.** Structure non-deterministic checks that require judgment.
- 📦 **Share your conventions.** Turn your team’s standards into rule packs you can use across repositories.

## Get started

Requires Python 3.14 or later. Add Rýni and
[tidy-harness](examples/tidy-harness/README.md), an opinionated example rule pack, as development dependencies:

```bash
uv add --dev ryni tidy-harness
uv run ryni check .
```

Installed rules are active automatically. The CLI runs deterministic checks and
reports agent reviews as pending. Commit `pyproject.toml` and `uv.lock` to share
the same versions with your team.

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

Counts cover unique targets that completed deterministic checks; directory targets
are listed separately. Time includes rule loading, discovery, checks, and any
fix/recheck, excluding process startup and report rendering. Color adapts to the
terminal and respects `NO_COLOR`; redirected output is plain text. Use
`--output-format compact` for the original one-line diagnostics, or
`--output-format json` for structured output.

## Run with your agent

Install the bundled skill for your agent, then invoke it in the same repository:

| Agent | Install in your terminal | Send in your agent |
| --- | --- | --- |
| Claude Code | `uv run ryni skill install .claude/skills` | `/ryni-check` |
| Codex | `uv run ryni skill install .agents/skills` | `$ryni-check` |

The skill runs deterministic checks, delegates reviews to sub-agents, and combines
the findings. Your agent must support sub-agents to complete reviews. Rýni itself
runs no model and needs no API key.

## Make it your own

A rule pack can combine deterministic checks with instructions for agent reviews.
Write your team's conventions once and share them across repositories.

**[Build your first rule pack →](website/first-rule-pack.md)**

To build rules with an agent, install the bundled authoring skill:

```bash
uv run ryni skill install .agents/skills --name ryni-rule-author
```

Use `.claude/skills` for Claude Code. Invoke `ryni-rule-author` to build or extend
a pack with shared analysis, tests, and measured performance. To inspect the cost
of installed deterministic checks:

```bash
uv run ryni check . --deterministic --profile
```

- [Overview and rule examples](website/index.md)
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

See [our jobs to be done](JTBD.md) for the project's direction.

Maintainers: see [the release guide](docs/releasing.md) for Rýni's PyPI
releases, dry runs, and the `ryni-release` skill.

---

*[Rýni](https://en.wiktionary.org/wiki/r%C3%BDni#Etymology) — from Old Norse, “scrutiny” or “contemplation.”*
