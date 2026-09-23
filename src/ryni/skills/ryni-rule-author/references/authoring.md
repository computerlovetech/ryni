# Rýni rule authoring API

## Execution contract

Import `Rule`, `RulePack`, `RuleScope`, and `Finding` from `ryni.models`.
`Rule(id, name, description, filename, evaluate, scope=RuleScope.FILE, fix=...)`
defines a deterministic check. Its `evaluate(Path)` returns a list of `Finding`
objects. A finding contains string `path`, positive integer `line`, matching
`rule_id`, and string `message`. Return `[]` for a completed check with no findings.
Raise an exception for failures that prevent checking; do not turn an unreadable
target into a clean result. Other rules continue after an execution error.

File rules declare one basename. Rýni discovers matching paths and evaluates
rules in declared order for each target, with targets sorted by path. A matching
directory or symlink is still a target, so report failures rather than assuming
every target is a readable regular file. Repository rules set `filename=""` and
`scope=RuleScope.REPOSITORY`. They receive the nearest Git root (including Git
worktrees), or the supplied directory when no Git root exists. Repository rules
run before file rules and own their domain-specific discovery and exclusions.

`fix(Path)` is optional. Rýni invokes it only with `--fix` when that rule reports
findings. Every attempted fix clears shared cached data, even after failure.
After all fixes, all selected rules run again with fresh cached data. Evaluations
must therefore be read-only, and fixes should be safe to repeat.

## Shared analysis

Decorate read-only helpers with `ryni.cache.cached_per_check`. Compose them:

```python
@cached_per_check
def inventory(root): ...          # pack-defined target discovery

@cached_per_check
def read_document(path): ...      # read and decode once per path

@cached_per_check
def parse_document(text): ...     # parse once per distinct content
```

The cache belongs to one `ryni.engine.check` call. It is not retained between
runs; direct helper calls outside a check are uncached. Exceptions are not cached.
Nested checks have separate caches. A nested fixing check also invalidates its
caller's cache. Cache keys include the function, positional arguments, and sorted
keyword arguments. Arguments must be hashable. Omitted defaults, explicit
defaults, and positional versus keyword calls can form different keys; use a
consistent call convention. Do not resolve symlinks merely to increase cache hits
when the rule's meaning depends on the discovery path.

Keep shared results read-only; immutable records, tuples, and frozensets are
useful. Include all semantic inputs in helper arguments. Put target paths into
findings at evaluation time, not in a parser cached only by content. Separate
common parsing from rule-specific filters so differing options do not repeat
the expensive parser. For external tools, consider one batch query instead of
one subprocess per file, preserving output mapping and failure handling.

No global filesystem cache, parallel scheduler, dependency declarations, or
special Git/Markdown service is required. Use ordinary Python helpers and keep
policy in the pack.

## Profiling

Use the installed environment so the intended pack is loaded:

```sh
uv run ryni check . --deterministic --profile
uv run ryni check . --deterministic --profile --output-format json
```

The opt-in JSON `profile.timings` array contains `kind`, `name`, `calls`,
`seconds`, `failures`, `cache_hits`, and `cache_misses`. Without `--profile`, the
existing report shape is unchanged. Exit codes remain 0 (clean), 1 (findings),
2 (execution errors), or 3 (agent reviews pending).

- `stage`: catalog loading, engine check, repository-root lookup, file discovery,
  and, with fixes, the final recheck. Discovery inside a pack belongs to that
  pack's rule/helper timing.
- `rule`: evaluation and result validation, aggregated by rule ID across targets
  and the final recheck. Agent reviews are not executed or timed as rules.
- `fix`: attempted fixer calls, separately from evaluation.
- `helper`: decorated helpers, identified by module and qualified function name,
  with cache hits and misses. Failed calls count as misses and are retried.

All times are inclusive wall time. Nested rows overlap; do not add them together.
A rule's time includes shared work it first requests. A subsequent rule may be
fast because it gets a cache hit. Nested helpers overlap in the same way.
Failures count exceptions escaping the timed operation; a completed check stage
can contain reported rule errors. Helper arguments and file contents are not
included. CLI timings exclude Python imports, command setup, and output rendering.
Profiling adds overhead; use it to locate costs and use repeated unprofiled runs
to compare speed. State the workload, cache conditions, and whether startup is
included. Avoid fixed millisecond test limits.

For Python callers:

```python
from pathlib import Path
from ryni.engine import check
from ryni.profiling import CheckProfile

profile = CheckProfile()
result = check([Path(".")], PACK.rules, profile=profile)
print(profile.to_dict())
```

Use a new profile for each run. Python callers do not get a catalog-loading row
because they supply the rules. A nested `check()` does not inherit profiling;
its time is included in the calling rule, without leaking its helper statistics
into the outer run.

## Package and validate

Copy `assets/example_pack.py` from this skill into `src/service_rules/__init__.py`
when using the example. Give the package a `pyproject.toml` such as:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "service-rules"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["ryni>=0.1.11"]

[project.entry-points."ryni.rules"]
service = "service_rules:PACK"

[tool.hatch.build.targets.wheel]
packages = ["src/service_rules"]
```

Choose a dependency floor matching APIs actually used. The example's cache API
is available from 0.1.11; profiling requires a Rýni build with `check --profile`
(verify `ryni check --help`). Installation activates the pack. Register a
`RulePack` with a nonempty tuple of rules and unique IDs; avoid expensive work
at import time. Use an editable installation when measuring working-tree changes.

Test through `check([root], PACK.rules)` as well as individual rules. Include
mixed valid/invalid inputs, relevant I/O failures, shared-helper reuse, changes
between runs, and cache invalidation after fixes if the pack supplies them.
For performance regressions, assert meaningful work counts (for example, one
parse shared by three rules) rather than noisy elapsed-time thresholds. Compare
the entire result before and after optimizations, including ordering and errors.
