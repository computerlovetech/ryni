# Python API

Import authoring types from `ryni.models`. See [write and share a pack](writing-packs.md)
for a complete example.

## `Rule`

| Field | Meaning |
| --- | --- |
| `id` | Unique rule ID. Use a team-specific prefix. |
| `name` | Short descriptive name. |
| `description` | What the convention requires and why. |
| `filename` | File basename, or an empty string for repository rules. |
| `evaluate` | Callable accepting `Path` and returning `list[Finding]`. |
| `scope` | `RuleScope.FILE` by default, or `RuleScope.REPOSITORY`. |
| `fix` | Optional callable accepting `Path`, returning `None`. Defaults to no action. |

Evaluators must be deterministic, must not print, and must not modify files.
Fixers run only under `--fix`, when their rule reports findings. Preserve unrelated
content and leave ambiguous fixes for a human. Exceptions are reported as execution
errors while unrelated checks continue.

## `ReviewRule`

| Field | Meaning |
| --- | --- |
| `id`, `name`, `description` | Same identity fields as `Rule`. |
| `instructions` | Nonempty review prompt, including evidence and applicability criteria. |
| `filename` | Empty by default; a basename for file-scoped reviews. |
| `scope` | `RuleScope.REPOSITORY` by default. |

There is no evaluator or fixer. Rýni prepares a `ReviewTask` for each applicable
target. Your agent delegates it using the `ryni-check` skill.

## `RulePack`

| Field | Meaning |
| --- | --- |
| `name` | Human-readable pack identity. |
| `description` | The pack's purpose or point of view. |
| `rules` | Nonempty tuple of `Rule` and/or `ReviewRule` objects. |

Register a pack through the `ryni.rules` Python entry-point group. Single-rule
exports remain supported. Package name and version come from installed distribution
metadata, not a second manually maintained version field.

Duplicate rule IDs, malformed rules, and failed imports fail catalog loading
atomically. Rýni never quietly runs only part of an invalid pack.

## `Finding`

```python
Finding(path="skills/review/SKILL.md", line=2, rule_id="TEAM001", message="Add an owner.")
```

Paths, IDs, and messages are strings. Line numbers are positive integers. The ID
must match the producing rule. A finding may point to a related file. Include the
specific deviation and practical resolution in its message.

## `check(paths, rules, *, fix=False)`

`ryni.engine.check` accepts a list of paths and a sequence of rules. It returns a
`CheckResult` with completed deterministic targets, findings, errors, pending review
tasks, and an `exit_code` property. It neither loads installed packs nor launches
agents; the CLI adds installed pack provenance to prepared review tasks.
