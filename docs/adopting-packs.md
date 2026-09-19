# Adopt a pack

A pack is an ordinary Python package with a point of view. Its author documents
what the rules require and why. Installing the package activates its rules.

## Install once

Replace `your-team-rules` with the published package you want to adopt:

```bash
uv tool install --with your-team-rules ryni
ryni check .
```

Try the same policy without a persistent install:

```bash
uvx --with your-team-rules ryni check .
```

Use the same `--with` packages on every `uvx` invocation. Bare `uvx ryni` may run
without the pack installed in your persistent tool environment.

Packages execute Python when loaded. Adopt packages from authors you trust.

## See what you adopted

```bash
ryni rule
ryni rule TEAM002
ryni rule --output-format json
```

Each rule identifies its execution type, pack, and installed version. Individual
rule explanations include review instructions where applicable. JSON also includes
the distribution name and pack description.

All packs run alongside the built-in `SKILL001`. Duplicate rule IDs fail clearly;
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

## Keep adoption repeatable

Pin both packages when sharing installation commands or configuring CI:

```bash
uv tool install --with your-team-rules==1.2.0 ryni==0.1.0
```

These are illustrative versions; use versions published by your pack author.
Install multiple packs by repeating `--with`. A team can also publish an umbrella
package depending on its chosen packs. No Rýni-specific configuration is needed.

To replace the policy in an existing tool installation, reinstall with the desired
packages, for example `uv tool install --force --with other-team-rules ryni`.
Removing a dependency from a running Python environment is not an activation API.
Use uv to manage the tool environment.
