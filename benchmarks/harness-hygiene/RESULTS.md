# Results and remaining bottlenecks

Measured 12 repositories, 344,933 tracked files.
The corpus is pinned in repositories.json; all clones were clean after scanning.

## Performance with identical results

Shuffled, seven-repetition comparison: sum of per-repository medians **4.317 s → 3.776 s (12.5% less engine time)**.
Inventory filtering alone: 4.317 → 3.952 s (8.4%).
Directory-entry discovery then: 3.952 → 3.776 s (4.5%).
All full CheckResult digests matched for every paired run. No timing assertions were added to tests.
Sequential end-to-end CLI totals before/after the performance changes: 4.822 → 4.487 s (6.9% less).
CLI totals are less controlled than the shuffled engine comparison (3 versus 5 repetitions).
This is one macOS ARM machine with warm filesystem caches, not a portable latency guarantee.

| Repository | Files | Baseline engine ms | Optimized engine ms | Change | Final findings |
| --- | ---: | ---: | ---: | ---: | ---: |
| django/django | 7,091 | 126.6 | 111.4 | -12.0% | 1 |
| facebook/react | 7,252 | 65.9 | 57.5 | -12.8% | 1 |
| fastapi/fastapi | 3,139 | 38.2 | 35.6 | -6.8% | 1 |
| golang/go | 15,951 | 102.8 | 79.6 | -22.5% | 1 |
| grafana/grafana | 23,465 | 257.2 | 216.5 | -15.8% | 3 |
| kubernetes/kubernetes | 31,392 | 307.8 | 253.6 | -17.6% | 0 |
| microsoft/TypeScript | 66,671 | 208.1 | 125.3 | -39.8% | 1 |
| microsoft/vscode | 19,194 | 397.7 | 362.1 | -9.0% | 11 |
| nodejs/node | 51,849 | 1237.7 | 1180.8 | -4.6% | 0 |
| pytorch/pytorch | 22,669 | 262.1 | 201.4 | -23.2% | 9 |
| rust-lang/rust | 63,122 | 565.7 | 500.6 | -11.5% | 2 |
| vercel/next.js | 33,138 | 746.8 | 651.1 | -12.8% | 1 |

## Correctness follow-up

Manual inspection found two false-positive classes. A GitHub team mention in Node.js
was parsed as an import; Rust documentation deliberately demonstrated conflict markers.
The final pack requires explicit path notation or a filename extension for standalone
@imports and skips conflict examples inside code blocks. Three diagnostics disappear.
This semantic change is a separate commit, excluded from the identical-output speedup claim.
Final scan: 31 diagnostics, zero execution errors, zero pending reviews.
Two diagnostics duplicate TEAM014/SKILL004 checks; they are not separate defects.
Four missing-entry-point findings express pack policy, not a defect in a project that
has not opted into an agent harness. Budget findings likewise reflect chosen limits.
Missing links include generated PyTorch documentation targets absent from a clean
checkout. A build may create them; the checker reports filesystem state, not intent.
The apparent reference example in PyTorch skill-writer is exposed by its Markdown
fence structure; this pack follows CommonMark rather than guessing intended nesting.

## Remaining costs and why iteration stopped

Baseline cProfile identifies Markdown block/inline parsing, Git inventory filtering
and directory walking. The first optimization rejects irrelevant filenames before
pathlib allocation. The second removes redundant lstat work from Rýni discovery.
Both preserve scope, error handling and ordering; no persistent caches or concurrency
were introduced. See profile-hotspots.txt and the per-run profile arrays.
Node.js remains dominated by parsing its reachable Markdown graph. Caching parsing
within a check is already active. Skipping reachable docs, using a regex-only parser
or keeping stale cross-run results would alter coverage/correctness. A faster
CommonMark backend is a possible future experiment, with a larger compatibility cost.
Small inputs are increasingly dominated by CLI startup; threaded scheduling would
add complexity without evidence of benefit on this workload.

## Validation

- 191 core tests in an isolated environment without external rule packs.
- 32 new pack tests, including every rule, Git exclusions, cache lifetime, fixes,
  Markdown examples, symlinks, Unicode paths, and both real-corpus false positives.
- 30 existing tidy-harness tests; Ruff passes on changed code and core tests.
- 12 CLI and engine result comparisons per repetition; final scans have no errors.

Performance commits can be reverted separately. Corpus clones are retained as
requested; no upstream repository files were edited. Tests are local and do not run
the cloned projects. Findings and timings are recorded, not model-performance claims.
