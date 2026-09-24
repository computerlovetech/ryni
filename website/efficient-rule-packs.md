# Efficient rule packs

Use `cached_per_check` to share reads and parsing between rules. Use `--profile`
to measure where a check run spends time.

## Share reads and parsing

File rules declare the basename they need. Rýni filters names during discovery,
keeps deterministic ordering, and skips the file walk when only repository rules
are active. Repository rules own their discovery and exclusions.

Within a pack, compose small helpers for expensive discovery, reads, and parsing.
Decorate reusable read-only work with `cached_per_check`:

```python
from pathlib import Path
import tomllib

from ryni.cache import cached_per_check


@cached_per_check
def read_config(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@cached_per_check
def parse_config(text: str) -> dict:
    return tomllib.loads(text)
```

Each rule calls `parse_config(read_config(path))` and evaluates the returned data
without changing it. The read is shared per path; parsing is shared per distinct content. Apply
rule-specific filters after parsing so different filters do not repeat the
parser. Construct findings in evaluations so a shared analysis never carries
another target's path. Packs can use the same pattern for inventories, graphs,
or results from external tools. Batch external commands where semantics permit.

Arguments must be hashable. Calls are keyed by function, positional arguments,
and sorted keyword arguments; use a consistent calling convention. Prefer
immutable results and do not mutate cached objects. Exceptions are not cached.
The example above lets parsing failures become execution errors; a rule that
owns syntax validation can instead return shared parse-error data and translate
it into a finding, as the authoring skill's runnable example does.

Each check has its own cache. Rýni clears it after every attempted fix, including
failed fixes, and starts the final recheck with fresh data. Separate runs and
direct helper calls outside the engine see fresh data. Keep evaluations read-only
and put edits in `fix`; do not cache evaluations or mutations. Avoid global
filesystem caches that can become stale.

## Profile a check run

```bash
uv run ryni check . --deterministic --profile
uv run ryni check . --deterministic --profile --output-format json
```

The default text report includes total elapsed time. `--profile` adds detailed
timings and cache counts; JSON reports add a `profile.timings` field. Profiling
does not change findings or exit codes.
Every timing contains a `kind`, `name`, call count, `seconds`, failure count, and
cache hit/miss counts (the latter apply to helpers).

| Kind | What it measures |
| --- | --- |
| `stage` | Catalog loading, engine check, root lookup, file discovery, final recheck |
| `rule` | Evaluation and output validation, grouped by rule ID across all targets |
| `fix` | Attempted fixes, grouped by rule ID |
| `helper` | `cached_per_check` helpers, with cache hits and misses |

Times are **inclusive wall time**. A helper's time is included in its calling
rule, and that rule's time is included in the check stage. Do not sum nested rows.
The first rule to request shared work pays for it; later rules can hit the cache.
Nested helpers overlap too. Failed helper calls are misses and will be retried.
With `--fix`, rule totals include the initial evaluation and final recheck, while
fix calls have separate rows. Agent reviews are not executed or timed as rules.

The CLI's profile excludes Python startup/imports, command setup, and report
rendering. Measure the whole command separately when those costs matter. Profiled
runs incur instrumentation overhead: use them to identify costs, then compare
repeated unprofiled runs on the same workload. Verify equal findings, errors, and
ordering. Use work-count assertions in tests instead of fixed timing thresholds.

To profile a `RulePack` named `PACK` from Python:

```python
from pathlib import Path
from ryni.engine import check
from ryni.profiling import CheckProfile

profile = CheckProfile()
result = check([Path(".")], PACK.rules, profile=profile)
print(profile.to_dict())
```

Create a new collector for each run. Nested checks have separate caches and do
not inherit the outer collector; their wall time remains part of the calling
rule. Profiling retains helper names and counts, not arguments or file contents.

## Build with an agent

```bash
uv run ryni skill install .agents/skills --name ryni-rule-author
```

For Claude Code, use `.claude/skills`. Invoke `$ryni-rule-author` in Codex or
`/ryni-rule-author` in Claude Code with the conventions you want implemented.
The installer includes an API reference and a runnable TOML example with three
rules sharing analysis. It preserves existing customized skill files.

The skill covers rule scope, shared analysis, packaging, tests, and performance
measurements.

For packaging and rule registration, start with
[Your first rule pack](first-rule-pack.md).
