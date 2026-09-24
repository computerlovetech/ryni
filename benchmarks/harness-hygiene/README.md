# Real-repository harness benchmark

12 shallow Git clones with full working trees (submodules not initialized), about
3.9 GiB on this machine. [repositories.json](repositories.json) pins URLs, commit
SHAs and tracked-file counts. Clones remain in the main checkout's `test-repos/`
and are ignored by Git. No project dependencies were installed or project code run.

The corpus spans large language/toolchain, framework, UI/editor, observability and
infrastructure repositories. It is a scale sample, not a random sample of agent
users. All 18 TEAM rules and the four built-in SKILL rules ran on every repository;
there were no agent reviews. The overlapping description checks intentionally
exercise the default installed-pack behavior and must not be counted as distinct
underlying defects.

Reproduce in an environment with editable Rýni and this pack:

```sh
uv pip install -e . -e examples/team-harness
.venv/bin/python scripts/clone_harness_benchmarks.py test-repos benchmarks/harness-hygiene/repositories-new.json
.venv/bin/python scripts/benchmark_harness.py test-repos benchmarks/harness-hygiene/new.json --repeat 5
.venv/bin/python scripts/compare_harness_iterations.py test-repos benchmarks/harness-hygiene/paired-new.json
```

The clone script records the tip it actually clones; for an exact historical run,
fetch and checkout each recorded SHA. Reusing an existing directory records its
current HEAD instead of modifying it. The benchmark accepts result exit codes 0
and 1 (or records errors as 2), parses complete JSON, and asserts CLI/engine output
equality. Discovery and rule evaluation are read-only. Dirty/untracked files can
change results; use clean pinned checkouts.

`baseline.json` has a diagnostic profile followed by three unprofiled engine and
CLI repetitions. `iteration-1.json` and `iteration-2.json` have five repetitions.
Profiles are inclusive and overlap. They identify costs; they are not used as
speedup measurements. CLI samples include imports, catalog discovery and JSON
serialization; engine samples exclude them. Runs use warm OS filesystem caches,
but each check has a fresh Rýni cache; no persistent result cache is introduced.

`paired.json` is the stronger comparison: seven repetitions per repository and
variant, seeded shuffled order within each round, one excluded warmup round.
Variants isolate the baseline, inventory-only improvement, and both performance
improvements. Entire CheckResult digests must match on every run. Historical
Python source is pinned to baseline `62fa1a6` and optimized `47afeb6`, never from the test repositories.

Changes:

- `62fa1a6`: rules, research, corpus manifest and baseline.
- `2f7ee77`: [inventory optimization](iteration-1.md).
- `47afeb6`: [Rýni discovery optimization](iteration-2.md).

Keep correctness changes separate from those equal-output performance comparisons.
The final report explains any changed diagnostics and remaining limitations.

See [the results and interpretation](RESULTS.md) for timings, findings and limits.
