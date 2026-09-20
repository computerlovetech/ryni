# CLI reference

## `ryni check [PATHS]...`

Run deterministic rules and prepare applicable agent reviews. Paths default to `.`.

```bash
ryni check
ryni check skills/ another/SKILL.md
ryni check . --select SKILL001
ryni check . --output-format json
```

| Option | Effect |
| --- | --- |
| `--select IDS` | Run a comma-separated set of rule IDs. Unknown IDs are errors. |
| `--deterministic` | Explicitly exclude agent review rules. |
| `--fix` | Apply available Python fixes and recheck all selected rules. |
| `--output-format text\|json` | Choose human-readable diagnostics or structured output. |

`SKILL001` has no automatic fix. Pack authors may provide fix callbacks. Fixes run
once per applicable target with findings, and successful fixes are not rolled back
if another rule fails. Review rules are never executed or fixed by the CLI.

### JSON report

```json
{
  "checked_files": ["skills/review/SKILL.md"],
  "findings": [],
  "errors": [],
  "pending_reviews": []
}
```

`checked_files` lists completed deterministic targets, including repository roots
for repository rules. Findings contain `path`, `line`, `rule_id`, and `message`.

Each pending review contains `rule_id`, `name`, `description`, `path`,
`instructions`, `scope`, and `source`. Source contains pack `name`, `description`, package
name, and installed `version`. These are instructions for the existing agent, not
completed findings. Review-only targets do not appear in `checked_files`.

See [CI](ci.md) for exit codes and completion semantics.

### Discovery and scope

File rules recursively match a literal basename. Discovery skips `.git`, `.venv`,
`venv`, `node_modules`, and `__pycache__`.
Harness directories such as `.agents`, `.claude`, `.codex`, and `.github` are included.
You can check an excluded location by passing it explicitly. Directory symlinks
are not traversed. Repeated paths are deduplicated without resolving symlinks.
File discovery does not apply `.gitignore` patterns.

Repository rules inspect the nearest Git checkout for each path, once per root.
Outside Git, the supplied directory or a supplied file's parent is the root.
**Selecting a single file does not narrow repository-scoped rules.** A rule's Python
logic or review instructions determine which content within that root matters.

## `ryni rule [ID]`

List active rules with their kind and source, or explain one rule:

```bash
ryni rule
ryni rule SKILL001
ryni rule TEAM002 --output-format json
```

JSON always returns an array, including when one ID is requested. Each item has
identity, description, kind, scope, filename, and source. Review rules also include
instructions. Python callables are not serialized.

## `ryni skill install [DIRECTORY]`

Copy the bundled `ryni-check/SKILL.md` into an agent's skills directory. Defaults
to `.agents/skills` in the current directory.

```bash
ryni skill install
ryni skill install .claude/skills
```

Existing identical content is left alone. Different content or an unwritable
destination produces exit `2`. The installer does not overwrite custom skill
instructions or install packages. See [agent checks](agent-checks.md).
