# Contributing

Changes should advance one of Rýni's jobs: adopt a trusted standard, express
repeatable conventions, publish a reusable pack, or catch drift before it lands.
Read [JTBD.md](https://github.com/computerlovetech/ryni/blob/main/JTBD.md) for the
product boundaries.

## Work locally

```bash
uv sync --group docs
uv run pytest tests
uv run ruff check .
uv run --group docs mkdocs build --strict
uv run --group docs mkdocs serve
```

The CLI is in `src/ryni/cli.py`, execution in `src/ryni/engine.py`, authoring types
in `src/ryni/models.py`, and discovery in `src/ryni/rules/__init__.py`. The canonical
agent skill lives in `src/ryni/skills/ryni-check/SKILL.md` and is included in wheels.

## Test outcomes

Test passing, failing, and incomplete behavior rather than matching prose. For
pack changes, verify installed entry-point discovery. For the skill, run a real
fixture through an existing agent and confirm that each pending review is delegated
and accounted for. Missing delegation must remain incomplete.

The documentation uses Material for MkDocs, taking inspiration from
[Ruff's documentation](https://docs.astral.sh/ruff/) in its compact navigation,
task-first guides, and separate reference pages. Build the docs with strict
validation before submitting changes.
