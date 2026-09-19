# Rýni

**An opinionated linter for agent harnesses, written in Python.**

[Getting started](#getting-started) · [Usage](#usage) · [Rules](#rules) · [Plugins](#plugins) · [Contributing](#contributing)

Agent instructions and skills are part of your codebase. Rýni helps you keep them
consistent as your project grows, enforcing conventions for how harnesses are
structured, shared, and maintained, with actionable diagnostics when they drift.

- **Validate skills.** Check `SKILL.md` frontmatter for required metadata.
- **Keep instructions in sync.** Check that `CLAUDE.md` links to its sibling `AGENTS.md`.
- **Check skill organization.** Find misplaced skill sources, tracked installations,
  and missing or inconsistent local installations.
- **Choose your rules.** Run the full catalog or select individual checks by ID.
- **Apply available fixes.** Use `--fix` to repair supported problems and report what remains.
- **Use it in automation.** Get structured JSON output and predictable exit codes.
- **Add your own conventions.** Distribute custom rules as Python packages.

Rýni's built-in checks run locally, without a model or API key. Checks do not modify
files unless you pass `--fix`. The project is in early development; the CLI and
plugin API may change.

## Getting started

Rýni requires **Python 3.14 or later**. Git is required for the installed-skills
ignore check (`SKILL002`).

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
ryni check skills/ AGENTS.md CLAUDE.md
```

List available rules:

```bash
ryni rule
```

Apply available fixes for selected rules:

```bash
ryni check . --select AGENT001 --fix
```

Currently, `AGENT001` provides a built-in fix. When the sibling `AGENTS.md` is an
existing file, it repairs incorrect or broken `CLAUDE.md` symlinks and converts
regular files whose contents match `AGENTS.md` exactly. Different contents,
directories, missing targets, and targets pointing back to `CLAUDE.md` are left
unchanged. It does not create `CLAUDE.md` where none exists.

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
to choose a comma-separated list of rule IDs. Markdown placement exceptions are
configured in repository-root `ryni.toml`; see [Markdown placement](#markdown-placement).

File rules search the supplied paths recursively and select files by name.
Discovery skips `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.agents`,
`.claude`, `.codex`, and `.github`. You can check those locations by passing them
explicitly. Directory symlinks are not traversed, and repeated paths are deduplicated
without resolving symlinks. File discovery does not apply `.gitignore` patterns.

Repository rules inspect the nearest enclosing Git checkout for each supplied
path, once per repository. Outside a Git checkout, they use the supplied directory
or the file's parent directory. **Selecting a single file does not narrow the scope
of repository rules.** Select only file rules when you want checks limited to those paths.

## Rules

Rýni includes six rules:

| ID | Name | Checks |
| --- | --- | --- |
| `SKILL001` | `skill-frontmatter` | `SKILL.md` starts with valid YAML frontmatter containing non-empty string `name` and `description` fields. |
| `AGENT001` | `claude-agents-symlink` | Each existing `CLAUDE.md` is a symlink resolving to an existing sibling `AGENTS.md`. |
| `SKILL002` | `installed-skills-gitignored` | Installed skill directories for configured agents are covered by repository `.gitignore` rules and are not tracked. |
| `SKILL003` | `local-skills-source-location` | Locally owned skills live under a directory named `skills/`, with nested categories allowed. |
| `SKILL004` | `local-skills-installed` | Local skills have a matching local-source `skills-lock.json` entry and matching installed `SKILL.md` files for agents configured in their source scope. |
| `DOC001` | `markdown-location` | Markdown belongs under `docs/` or root `temp/`, with conventional filenames, skill directories, GitHub paths, and configured exceptions allowed. |

`SKILL001` allows additional frontmatter fields and checks structure only.
`AGENT001` allows `AGENTS.md` without a corresponding `CLAUDE.md`. `SKILL004`
accepts copies and symlinks and checks installation evidence, not command history.

These rules express Rýni’s opinions about maintaining agent harnesses. They do not assess
instruction quality or agent behavior. All rules are deterministic checks.

### Markdown placement

Run `ryni check . --select DOC001` to check placement. This repository-wide rule
examines `.md` and `.markdown` files, including uppercase extensions. It reports
misplaced files without moving them, including when `--fix` is passed.

Allowed locations are any directory named `docs/` or `skills/`, at any depth,
and repository-root `temp/`. These conventional filenames are allowed anywhere
(spelling and case are exact):

```text
README.md              AGENTS.md          CLAUDE.md
SKILL.md               CONTRIBUTING.md    CHANGELOG.md
LICENSE.md             LICENCE.md         NOTICE.md
SECURITY.md            CODE_OF_CONDUCT.md SUPPORT.md
GOVERNANCE.md          MAINTAINERS.md     AUTHORS.md
CONTRIBUTORS.md
```

These repository-relative GitHub paths are also allowed:

```text
.github/ISSUE_TEMPLATE/*.md
.github/PULL_REQUEST_TEMPLATE.md
.github/PULL_REQUEST_TEMPLATE/*.md
.github/copilot-instructions.md
.github/instructions/**/*.instructions.md
```

Extend the defaults with `ryni.toml` at the Git repository root:

```toml
[rules.markdown-location]
additional_allowed_names = ["OWNERS.md", "ARCHITECTURE.md"]
additional_allowed_paths = [
    ".changeset/*.md",
    "content/**/*.md",
    "apps/api/DECISIONS.md",
]
```

Names are literal basenames allowed anywhere. Path globs match the complete path
relative to the repository root, case-sensitively: `*` matches within one path
segment, `**` matches zero or more segments, and `?` and character classes are
supported. Use `/` separators; absolute paths and `..` segments are rejected.
Exceptions affect only `DOC001`, and extend rather than replace its defaults.
Unknown configuration keys and invalid values produce exit code `2` when this
rule runs. Without `ryni.toml`, defaults apply.

Each Git checkout uses its own root configuration; nested configuration files are
not merged. Outside Git, the supplied directory (or a supplied file's parent)
serves as the root. Even when a single file is selected, the rule scans that root.

Discovery skips Git metadata, virtual environments, `node_modules`, Python caches,
installed agent `skills/` directories, and nested Git repositories. Directory
symlinks are not traversed. Unlike file-rule discovery, it inspects `.github/`
and other agent configuration directories. It does not apply `.gitignore` or
infer generated/vendored content; add path exceptions for those and for product
content such as workshop material.

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
