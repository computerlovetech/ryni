# Adopt a pack

A pack is an ordinary Python package with a point of view. Its author documents
what the rules require and why. Installing the package activates its rules.

## Recommended: project development dependencies

For a shared repository, add both Rýni and your team's rule pack as development
dependencies. Replace `your-team-rules` with the published package name:

```bash
uv add --dev ryni your-team-rules
uv run ryni check .
```

Commit `pyproject.toml` and `uv.lock`. The development dependencies declare which
packages the team uses; the lockfile records their resolved versions. These tools
are development dependencies, not application runtime dependencies.

Rýni discovers packs installed in the environment that runs it. It does not read
`pyproject.toml` itself. Use `uv run ryni` locally and in your agent so it runs in
the project environment. In CI, install from the committed lockfile:

```bash
uv sync --locked --group dev
uv run --no-sync ryni check .
```

This command prepares agent reviews as well as running deterministic checks.
See [CI](ci.md) for a deterministic-only gate and agent review completion.

Add more packs with `uv add --dev another-team-rules`. Review dependency and
lockfile changes when updating the team's conventions. No Rýni-specific
configuration file is needed.

Packages execute Python when loaded. Adopt packages from authors you trust.

## See what you adopted

```bash
uv run ryni rule
uv run ryni rule TEAM002
uv run ryni rule --output-format json
```

Each rule identifies its execution type, pack, and installed version. Individual
rule explanations include review instructions where applicable. JSON also includes
the distribution name and pack description.

All packs run alongside the [built-in skill checks](rules.md). Duplicate rule IDs fail clearly;
they never silently replace one another. Authors should choose a distinct prefix.

## Try the included pack from source

The repository contains `examples/team-pack`, with a Python check for project
instructions and an agent review of test commands. From a Rýni checkout:

```bash
uv run --with-editable . --with ./examples/team-pack ryni rule
uv run --with-editable . --with ./examples/team-pack ryni check .
```

`--with-editable .` ensures the example uses this checkout rather than an older
published Rýni dependency. The example is not a published community pack.

## Alternative: standalone installation

For use outside a project environment, install Rýni and the pack together:

```bash
uv tool install --with your-team-rules ryni
ryni check .
```

Or try a pack without a persistent installation:

```bash
uvx --with your-team-rules ryni check .
```

These environments are separate from the project's development dependencies.
Bare `uvx ryni` does not include the team's project pack. Supply the same `--with`
packages each time you use `uvx`; repeat `--with` for multiple packs.

Pin both Rýni and pack versions when sharing standalone commands, for example:

```bash
uvx --with your-team-rules==1.2.0 ryni==0.1.0 check .
```

The names and versions above are illustrative. Use published versions that
support your pack. To replace a persistent tool installation's policy, reinstall
with the desired packages, for example
`uv tool install --force --with other-team-rules ryni`.
