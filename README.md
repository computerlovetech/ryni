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

```bash
uv tool install ryni
ryni check .
```

To adopt a published pack, replace `your-team-rules` with its package name:

```bash
uv tool install --with your-team-rules ryni
```

Or run without a persistent installation:

```bash
uvx --with your-team-rules ryni check .
```

Installed rules are active immediately. Inspect them with `ryni rule`.

## Check with your agent

Install the bundled skill into your agent's skills directory:

```bash
ryni skill install .claude/skills
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
