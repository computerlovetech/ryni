# Iteration 1: filter Git paths before pathlib allocation

The baseline profiles identify inventory construction as a repeated cost across
large repositories. Reject non-harness basenames/extensions before constructing
Path objects, preserving tracked/nonignored discovery and exclusions.

Sum of repository median engine times: 4.1866 → 3.8981 seconds
(6.9% reduction). Baseline has 3 repetitions; iteration has 5.
Warm OS cache; fresh per-check cache; engine excludes startup/output.
All 12 complete result digests match, including errors and checked targets.
The TypeScript case benefits most; Markdown-heavy Node.js remains similar.
30 pack tests pass, including extensionless, Unicode and ignored/tracked paths.
These sequential measurements are indicative; final comparisons use alternating
old/new runs to reduce temporal bias.
