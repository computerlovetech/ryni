# Example team pack

A working pack with two opinions: repositories need an explicit starting point,
and documented test commands should agree with the repository's tooling.

- **TEAM001** checks for a nonempty root `AGENTS.md` using Python.
- **TEAM002** asks an agent to verify documented test commands against manifests.

From the Rýni checkout, run:

```bash
uv run --with-editable . --with ./examples/team-pack ryni rule
uv run --with-editable . --with ./examples/team-pack ryni check .
```

The package is a local example, not a published product. Copy it, choose a unique
package name and rule prefix, and replace these conventions with your own.

Read [the pack authoring guide](../../docs/writing-packs.md) before publishing.
