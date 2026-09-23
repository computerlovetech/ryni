---
name: ryni-rule-author
description: Create, extend, or optimize Rýni rule packs with shared analysis, correctness tests, and measured performance. Use when implementing deterministic rules or their automatic fixes, not when running a repository convention review.
---

# Build a Rýni rule pack

Implement the user's conventions in their pack. Keep domain-specific discovery,
parsers, Git queries, and policy in the pack; use Rýni for execution, shared-cache
lifetime, findings, and profiling. Preserve the existing package and rule IDs
when extending a pack.

## Establish the contract

Inspect the installed Rýni version, the pack's rules, shared helpers, packaging,
and tests. Read [the API and performance guide](references/authoring.md) for
scope, cache semantics, profiling, and registration. That guide describes the
Rýni version bundled with this skill; verify newer APIs against the user's
installation before relying on them.

Define what passes, what produces a finding, and what is an execution error.
Specify targets, exclusions, and any related files the rule reads. Choose file
scope when a basename identifies each target; use repository scope for checks
that require the repository as a whole. Do not turn a judgment-based convention
into an unreliable deterministic check.

## Build shared analysis

Reuse the pack's existing discovery, reads, and parsers. Compose
`cached_per_check` helpers for expensive read-only work that multiple rules use.
Return immutable data where practical and treat all cached values as read-only.
Cache common parsing before applying rule-specific filters. Batch external
commands when their semantics allow it.

Keep `evaluate(path)` read-only. Put edits in `fix(path)` so Rýni invalidates
cached data. Do not cache evaluations, findings with target-specific paths in a
content-only parser, failed reads, or mutations. Avoid process-global caches of
filesystem state.

For a new pack, adapt [the runnable example](assets/example_pack.py) if useful.
It shares reads and TOML parsing across three independent file rules; its
service settings are an example, not a required policy or pack architecture.
The reference contains packaging instructions.

## Verify behavior and cost

Test clean inputs, violations, and the boundary cases relevant to the rule.
Exercise rules together through `ryni.engine.check`, not only by calling their
functions directly. Verify shared work is reused, changes between runs are
visible, and any attempted fixes leave later rules and the final recheck fresh.
Preserve errors and findings from other rules when one check fails.

Use the user's existing environment and invocation prefix. Run the complete
deterministic pack with `--profile` on a representative repository and, when
scale matters, a temporary larger fixture. Read JSON even for nonzero exit codes.
Profile before choosing an optimization; compare unprofiled repeated runs before
and after it and verify equal results. Include command startup separately when
reporting CLI latency. Do not enforce machine-specific timing thresholds in tests.

Report the implemented conventions, validation, measured workload and timings,
and remaining limitations. Do not claim a speedup from code inspection alone.
Remove temporary fixtures. Publishing packages is separate from authoring them.
