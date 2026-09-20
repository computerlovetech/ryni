# Rýni

**Share conventions. Catch harness drift.**

Rýni helps teams adopt a trusted standard, express their own harness conventions,
and share those conventions as installable Python rule packs.

- **Adopt a pack.** One uv installation activates its rules. No `ryni.toml`.
- **Express your conventions.** Use Python checks or focused agent review instructions.
- **Check with your agent.** The `ryni-check` skill runs checks and delegates every
  pending review to a sub-agent, then combines the findings.
- **Catch drift in CI.** Structured diagnostics and explicit incomplete/pending states.

Rýni runs locally and does not launch a model or require an API key. Agent reviews
use your existing agent. The built-in baseline is `SKILL001`, which validates skill
frontmatter. Python 3.14 or later is required.

## Get started

For a shared repository, add Rýni as a development dependency:

```bash
uv add --dev ryni
uv run ryni check .
```

Add your team's published rule pack as a development dependency too. Replace
`your-team-rules` with its package name:

```bash
uv add --dev your-team-rules
uv run ryni rule
```

Commit `pyproject.toml` and `uv.lock`. Use `uv run ryni` locally and in your agent;
in CI, run `uv sync --locked --group dev` before `uv run --no-sync ryni check .`.
Installed rules are active immediately. See [adopting packs](docs/adopting-packs.md)
for details and standalone alternatives.

## Check with your agent

Install the bundled skill into your agent's skills directory:

```bash
uv run ryni skill install .claude/skills
```

Invoke `/ryni-check` in Claude Code. For Codex, install into `.agents/skills` and
invoke `$ryni-check`. An agent with sub-agent support is required for review rules;
missing review capability is reported as incomplete.

## Documentation

- [Getting started](docs/getting-started.md)
- [Adopt a pack](docs/adopting-packs.md)
- [Write and share a pack](docs/writing-packs.md)
- [Check with your agent](docs/agent-checks.md)
- [Continuous integration](docs/ci.md)
- [CLI reference](docs/cli.md) and [Python API](docs/api.md)
- [Working example pack](examples/team-pack/README.md)

The pack/review API is in early development in this checkout and must be released
before it is available through registry installs. To try this source version:

```bash
uv run --with-editable . --with ./examples/team-pack ryni check .
```

## Contributing

```bash
uv run pytest tests
uv run ruff check .
uv run --group docs mkdocs build --strict
uv run --group docs mkdocs serve
```

See [the contributing guide](docs/contributing.md) and [our jobs to be done](JTBD.md).
