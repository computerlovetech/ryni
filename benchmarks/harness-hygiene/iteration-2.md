# Iteration 2: use directory-entry metadata during Rýni discovery

Profiles show a second full filesystem walk for file-scoped rules. os.walk checks
symlinks again during descent, adding directory lstat calls. Discover targets
with scandir and retain DirEntry type information until children are queued.
Keep sorted descent, explicit input behavior, excluded directory pruning,
non-following directory symlinks, matching invalid directories, and I/O errors.

Sum of repository median engine times: 3.8981 → 3.7240 seconds
(4.5% reduction), five unprofiled repetitions each. All 12 full
result digests are unchanged. CLI startup/output is measured separately in JSON.
191 core tests pass; regressions cover symlinks, exclusions, unreadable inputs,
unfiltered discovery, and avoiding per-directory lstat calls.
See paired.json for the stronger shuffled old/new comparison.
