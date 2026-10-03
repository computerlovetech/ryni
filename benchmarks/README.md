# Repository benchmark

A small corpus test: one pinned manifest, one Python standard-library script,
and a reviewed baseline. Requires Python 3.10+, Git, and a built ryni binary.

```sh
cargo build --release --locked
python3 benchmarks/bench.py fetch
python3 benchmarks/bench.py run --baseline benchmarks/baseline.json
```

`fetch` creates shallow checkouts at the exact commits in `repos.json`, using
three concurrent downloads. Re-running it reuses the checkouts. Local changes,
including ignored/untracked files, are rejected. No upstream build scripts are
executed; submodules and Git LFS assets are not downloaded.

Checkouts live in `~/.cache/ryni-benchmark` (or under `XDG_CACHE_HOME`). Use
`--cache /absolute/path` to change this for both commands. Keep the corpus
outside ryni's checkout: ryni scans hidden directories, and `--no-ignore` disables ignore-file
filtering, so nesting it could change ordinary scans.

The 15 projects cover Python (Django), Rust (rust-analyzer), Go (Kubernetes),
TypeScript (VS Code), JavaScript (webpack), Java (Spring Boot), C (curl),
C++ (fmt), Ruby (Rails), PHP (Laravel), Elixir, Swift (SwiftNIO), Kotlin (Ktor),
C# (ASP.NET Core), and Dart (Flutter). Source URLs and commits are in the manifest.
Language variety exercises different documentation layouts; ryni itself checks
Markdown and skill metadata, not source-language semantics.

## Running and reviewing

```sh
python3 benchmarks/bench.py run --repo vscode --repeat 5
python3 benchmarks/bench.py run --binary /path/to/ryni --output benchmarks/results/candidate.json
python3 benchmarks/bench.py run --baseline benchmarks/results/candidate.json
python3 -m unittest discover -s benchmarks -p 'test_*.py'
```

Scans run sequentially, three times each by default, with a 60-second timeout
per invocation. JSON reports include every duration, median wall time, Markdown
and skill file counts, per-rule finding counts, exit status, revision, platform,
and binary hash. Full stdout
and stderr for each invocation are saved beside the report in a directory named
after its stem. Timing includes process startup and output capture; there is no
explicit warmup or cache flushing. Compare timing on the same machine and treat
it as informational, especially for tiny scans.

Exit code 1 from ryni means findings and is an expected scan outcome. The runner
fails on execution errors, crashes, timeouts, dirty/missing checkouts, or differing
output between repetitions. With `--baseline`, it also fails on changed commits,
repository membership, exit status, or output hashes. `--repo` can be repeated;
baseline comparison then covers only those repositories. Output hashes cover
plain-text diagnostics, including their formatting, with CRLF normalized to LF.

The baseline records observed behavior, not proof that every finding is correct.
Generated documentation, website routes, test fixtures, absent submodules, and
unfetched LFS assets can all produce expected findings. Review interesting
examples and turn confirmed bugs into small Rust regression fixtures. This
corpus complements the existing unit tests; it does not measure precision/recall.

After reviewing intentional changes, update the baseline explicitly:

```sh
python3 benchmarks/bench.py run
cp benchmarks/results/latest.json benchmarks/baseline.json
```

Only accept a completed successful run. To refresh a repository, edit its pinned
commit in `repos.json`, fetch again, inspect the output, and update the baseline.
Keep the full corpus opt-in locally; add scheduled CI only when it earns its cost.

## Stats and shareable plots

```sh
uv run benchmarks/report.py
```

This reads `results/latest.json` and generates `results/share/index.html`, an
offline report with a per-repository table for Markdown files, included skills,
findings, every rule (including zeros), median scan time, and linked commit IDs.
It also exports three 1600-pixel-wide PNGs and editable SVGs:

- `overview`: a 16:9 summary card for sharing.
- `repositories`: Markdown/skill coverage and findings for every repository.
- `timings`: median scan times with the observed minimum–maximum range.

The report includes methodology, a suggested sharing caption, and `data.json`
with the source run and manifest. Share the PNGs individually or host the whole
output directory as a static site. Nothing is published automatically.

The renderer uses Matplotlib, installed in an isolated environment by `uv` using
the script's pinned dependency. The benchmark runner still needs only Python's
standard library. To render another run or the checked-in baseline:

```sh
uv run benchmarks/report.py benchmarks/baseline.json --output benchmarks/results/baseline-share
```

Rendering requires successful, complete scans and a matching manifest. Skills
are included in Markdown counts; findings are counted per scan, not multiplied
by repetitions. The figures describe observed findings, not confirmed defects
or a quality ranking. Timing reflects this host/run, not a comparison to other tools.
