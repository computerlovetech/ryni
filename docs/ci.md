# Continuous integration

Run Python checks on every change. They need no model credentials and return stable
exit codes. Add Rýni and your team's pack as development dependencies and commit
`pyproject.toml` and `uv.lock`, as described in [adopting packs](adopting-packs.md).
Install those locked dependencies in CI so it uses the same policy as local checks.

## A deterministic gate

From the checked-out repository, after installing uv:

```bash
uv sync --locked --group dev
uv run --no-sync ryni check . --deterministic
```

`--deterministic` explicitly excludes agent reviews. It does not establish that the
full policy passed. If your policy consists only of Python rules, omit the flag.

## A complete policy check

```bash
uv run --no-sync ryni check . --output-format json
```

Without `--deterministic`, applicable review rules remain in `pending_reviews`.
A clean deterministic run with pending reviews exits `3`, preventing a CI job from
silently treating an unreviewed policy as passing.

| Exit code | Meaning |
| --- | --- |
| `0` | No findings, errors, or pending reviews in the selected scope. |
| `1` | Deterministic findings; reviews may also be pending. |
| `2` | Invalid invocation, execution error, or incomplete deterministic checks. |
| `3` | No deterministic findings or errors, but agent reviews remain pending. |

Precedence is errors, then findings, then pending reviews. Always read the full
JSON report rather than inferring review coverage from the exit code alone.

## Agent reviews in CI

After syncing the development dependencies, have your CI agent use
`uv run --no-sync ryni` in the project environment. Invoke the `ryni-check` skill. That agent runs the
checks, delegates review tasks, and produces the combined result. Your CI agent
integration must translate an incomplete or findings result into a failing status
if you want reviews to block merging.

Rýni does not launch an agent, persist review approvals, or provide a built-in
agent CI runner. Running the CLI alone cannot complete prompt-based reviews.
Start by reviewing their signal quality before making judgment-based findings
blocking. Never count unavailable delegation or missing evidence as a pass.
