# Architecture and contributing

Ryni is a single Rust package with a library and a CLI. The public CLI and JSON
contracts are documented; the Rust API is currently internal-facing and may
change as the engine evolves.

## Analysis boundaries

- `source.rs` owns immutable source snapshots, line indexes and byte-range validation.
- `document.rs` extracts Markdown links/headings and skill frontmatter once per
  document. It preserves the original YAML slice and offsets, including BOM/CRLF.
- `registry.rs` defines rule identities, scope, stability, defaults, explanations
  and fix availability. Documentation tables are generated from this registry.
- `settings.rs` validates configuration and packs, then resolves effective settings.
- `discovery.rs` finds supported files and reports discovery failures.
- `rules/` contains document checks and a small project index for skill names.
- `filesystem.rs` supplies target observations, allowing tests or editors to provide
  their own filesystem view. Its cache lives for one scan only.
- `lib.rs` orchestrates checking and offers `analyze` for supplied source snapshots.
- `diagnostic.rs` and `report.rs` contain structured findings and scan results.
- `output.rs` renders those findings for humans; `main.rs` owns CLI behavior.
- `fix.rs` validates and applies proposed edits; rules never write files.

Metadata semantic findings remain file-level when the YAML parser does not provide
an exact field range. Syntax errors use parser offsets when valid. Ryni never
underlines a guessed field position. Every source range is a half-open UTF-8 byte
range; displayed and JSON positions use one-based Unicode scalar columns, not
terminal cell widths or LSP UTF-16 offsets.

The project index retains only skill names and source snapshots needed for
cross-file findings. Document rules receive a `ProjectContext` with settings and
filesystem access. They do not discover files or load configuration.

## Adding or changing a rule

Add its stable ID and metadata to `registry.rs`, implement the check under
`rules/`, and connect it to the document or project phase. New conventions begin
in preview and require explicit selection. Add positive, negative, boundary and
false-positive examples to the fixture or integration tests. Keep prerequisite
parse failures separate from dependent semantic findings.

Rule IDs are configuration and JSON interfaces: do not silently rename or reuse
them. Promote preview behavior only after reviewing fixtures and corpus results.
Changes to stable defaults or findings require a changelog entry and an explicit
compatibility decision. The first local pack schema is version 1; incompatible
format changes require a new schema version. Preview behavior may change between
releases, so pin the Ryni binary as well as pack contents in CI.

Regenerate rule tables after registry changes:

```sh
cargo build --locked
python3 scripts/generate_rules.py
python3 scripts/generate_rules.py --check
```

## Regression checks

```sh
cargo fmt --check
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
python3 -m unittest discover -s benchmarks -p 'test_*.py'
```

Tests combine rule fixtures, CLI integration, a terminal snapshot, and generated
Unicode/malformed-input cases. Properties cover valid ranges, deterministic
findings and rendering without panics. File-system tests compare cached,
uncached, sequential and parallel runs, including target creation and deletion
between scans. Fix tests cover opt-in, stale sources, overlap rejection and
idempotence.

To deliberately refresh the terminal snapshot, build the debug binary, run
`python3 scripts/update_snapshots.py`, then review the diff. Never accept a changed
snapshot or corpus baseline solely to make tests pass.

The optional repository benchmark lives under `benchmarks/` and checks pinned
real projects. Schema 2 baselines compare structured diagnostics independently of
terminal presentation. A baseline describes observed behavior, not proof of
correctness; minimize confirmed bugs into focused regression cases.

CI runs Rust checks on Linux, macOS and Windows, checks the declared Rust 1.88
minimum, tests benchmark helpers, verifies generated rule tables and checks
Rust documentation. The full corpus remains opt-in to keep ordinary CI bounded.

## Performance

Use `ryni check . --timings` to print discovery, reading, parsing, rule and project
phase times plus target lookup/cache counts to stderr. With `--threads N`, file
phase totals represent summed work across threads, not elapsed wall time. Rendering
is outside these phase totals; corpus wall times include startup and output.

Sequential checking is the default; `--threads N` opts into a local thread pool.
Findings are sorted by path, source offset, rule ID and message after aggregation.
`--no-cache` disables the target cache for comparison. No cache survives a scan:
creating or deleting a target is observed by the next invocation, even when the
linking document is unchanged. Files changing during a scan do not provide an
atomic repository snapshot.

Profile representative workloads before changing defaults. A persistent result
cache would need to track external target dependencies, including missing targets;
source-file modification time alone is insufficient.
