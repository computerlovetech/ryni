# Rýni

**An opinionated linter for agent harnesses, written in Python.**

[Getting started](#getting-started) · [Usage](#usage) · [Rules](#rules) · [Plugins](#plugins) · [Contributing](#contributing)

Agent instructions and skills are part of your codebase. Rýni helps you keep them
consistent as your project grows, enforcing conventions for how harnesses are
structured, shared, and maintained, with actionable diagnostics when they drift.

- **Validate skills.** Check `SKILL.md` frontmatter for required metadata.
- **Choose your rules.** Run the full catalog or select individual checks by ID.
- **Apply plugin fixes.** Use `--fix` to repair problems supported by custom rules.
- **Use it in automation.** Get structured JSON output and predictable exit codes.
- **Add your own conventions.** Distribute custom rules as Python packages.

Rýni's built-in checks run locally, without a model or API key. Checks do not modify
files unless you pass `--fix`. The project is in early development; the CLI and
plugin API may change.

## Getting started

Rýni requires **Python 3.14 or later**.

Install from PyPI with uv:

```bash
uv tool install ryni
```

Or with pip:

```bash
pip install ryni
```

Then run Rýni in the project you want to check:

```bash
ryni check .
```

## Usage

Check files, directories, or multiple paths:

```bash
ryni check .
ryni check skills/ other/SKILL.md
```

List available rules:

```bash
ryni rule
```

Apply available fixes from custom rules:

```bash
ryni check . --select CUSTOM001 --fix
```

`SKILL001` does not provide an automatic fix. The `--fix` option is available for
installed plugins that implement fixes.

Fixes run once per applicable target with findings, followed by a fresh check of
all selected rules. Output and exit codes describe the remaining findings; a fix
failure produces exit code `2`, and other rules continue. Rules without fixes
still report their findings. Successful fixes are not rolled back if another fix
fails. Repository rules retain their repository-wide scope when fixing.

Produce JSON for scripts and CI:

```bash
ryni check . --output-format json
```

The JSON report contains `checked_files`, `findings`, and `errors`. Each finding
includes a path, line number, rule ID, and message. For repository-wide checks,
`checked_files` also includes repository roots.

| Exit code | Meaning |
| --- | --- |
| `0` | Checks completed without findings. |
| `1` | Checks completed with findings. |
| `2` | Invalid invocation, execution error, or incomplete checks. |

Reports preserve findings when another check fails. Runs with no applicable targets
explicitly report zero checked targets.

### Configuration and discovery

All registered rules, including installed plugins, run by default. Use `--select`
to choose a comma-separated list of rule IDs. `SKILL001` requires no configuration.

File rules search the supplied paths recursively and select files by name.
Discovery skips `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.agents`,
`.claude`, `.codex`, and `.github`. You can check those locations by passing them
explicitly. Directory symlinks are not traversed, and repeated paths are deduplicated
without resolving symlinks. File discovery does not apply `.gitignore` patterns.

Plugin repository rules inspect the nearest enclosing Git checkout for each supplied
path, once per repository. Outside a Git checkout, they use the supplied directory
or the file's parent directory. **Selecting a single file does not narrow the scope
of repository rules.** Select only file rules when you want checks limited to those paths.

## Rules

Rýni includes one built-in rule:

| ID | Name | Checks |
| --- | --- | --- |
| `SKILL001` | `skill-frontmatter` | `SKILL.md` starts with valid YAML frontmatter containing non-empty string `name` and `description` fields. |

Additional frontmatter fields are allowed. The rule checks structure only; it does
not assess instruction quality or agent behavior. The check is deterministic.

## Plugins

Extend Rýni with rules for your team's conventions. A Python package can export a
`ryni.models.Rule` instance through the `ryni.rules` entry-point group.

In the plugin's `pyproject.toml`:

```toml
[project.entry-points."ryni.rules"]
example = "my_rules:EXAMPLE"
```

In `my_rules.py`:

```python
from pathlib import Path

from ryni.models import Finding, Rule


def check_readme(path: Path) -> list[Finding]:
    if not path.read_text(encoding="utf-8").strip():
        return [Finding(str(path), 1, "CUSTOM001", "README must not be empty.")]
    return []


EXAMPLE = Rule(
    id="CUSTOM001",
    name="nonempty-readme",
    description="README.md must contain text.",
    filename="README.md",
    evaluate=check_readme,
)
```

Install the plugin in the same Python environment as Rýni. Both `check` and `rule`
load installed plugins; duplicate rule IDs are rejected. Plugins execute Python
code, so only install packages you trust.

Rules must be deterministic. Evaluators receive a path and return a list of findings.
They must not print or modify files. An evaluator exception produces an execution
error and exit code `2`, while other checks continue.

To support `--fix`, pass a `fix` callback when constructing a rule:

```python
def fix_readme(path: Path) -> None:
    if not path.read_text(encoding="utf-8").strip():
        path.write_text("# Project\n", encoding="utf-8")


EXAMPLE = Rule(
    id="CUSTOM001",
    name="nonempty-readme",
    description="README.md must contain text.",
    filename="README.md",
    evaluate=check_readme,
    fix=fix_readme,
)
```

The callback receives the same path as the evaluator (a repository root for
repository rules) and returns `None`. It runs only with `--fix` and only when that
rule reports findings. Omit it for rules without an automatic fix. Fixers must be
deterministic, safe to run repeatedly, and preserve unrelated content. Leave cases
requiring a human decision unchanged and raise exceptions for execution failures.
Do not print from a fixer; the CLI reports the results of the final check.

## Contributing

Bug reports, rule proposals, documentation improvements, and pull requests are
welcome. For a bug report, include the command you ran, a minimal example, and the
expected and actual output. For a new rule, describe the convention it checks and
show examples that should pass and fail.

From the repository root:

```bash
uv run ryni --help
uv run pytest tests
uv run ruff check .
```

The [CLI](src/ryni/cli.py) handles commands and output, the
[engine](src/ryni/engine.py) discovers targets and runs checks, and the
[rule catalog](src/ryni/rules/__init__.py) registers built-in rules and loads plugins.
Add built-in rules under `src/ryni/rules/`, register them in `BUILTINS`, and include
tests under `tests/`.
