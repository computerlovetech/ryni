---
name: ryni-release
description: Prepare and verify releases of the Rýni Python package. Use when asked to bump Rýni's version, prepare or publish a release, or diagnose its release pipeline.
---

# Rýni release

Use this skill in the Rýni repository. Read [the maintainer release guide](../../docs/releasing.md)
for setup, exact validation commands, dry runs, and recovery.

This repository publishes only `ryni`. `tidy-harness` is independently versioned
and will have its own repository and release pipeline. Do not bump or publish
it as part of a Rýni release.

## Prepare

- Inspect the working tree, branch, remote, and release tags. Preserve unrelated
  changes. Prepare on an appropriate branch; the published tag must point to a
  commit on current `origin/main`. Fetch before checking that ancestry.
- Determine the requested version or bump. If unspecified, propose a version
  from the changes; settle it with the user before preparing the final release.
- Inspect commits and diffs since the last released tag, cross-checking
  `CHANGELOG.md`. Before the first tag-driven release, compare with `edf0e6b`,
  the 0.1.1 preparation commit. Check Rýni's PyPI versions before choosing
  an unused version. Do not assume a missing GitHub Release means a version is unused.
- Set the Rýni version in `pyproject.toml`. Run `uv lock` and include its changes.
  Runtime dependencies must not gain release tooling. Run the example pack's
  compatibility tests while its source remains in this repository.
- Update relevant docs and the bundled `src/ryni/skills/ryni-check/SKILL.md` when
  the released behavior affects them. This maintainer skill is not bundled.
- Write concise Rýni release notes under `## [VERSION] - YYYY-MM-DD`
  and leave a fresh `[Unreleased]` section. Run `scripts/release.py --tag vVERSION`
  through `uv run`, all CI checks, and the isolated wheel smoke test documented
  in the guide. Resolve failures before proceeding.

## Publish when authorized

Show the prepared version, changes, modified files, validation results, and exact
tag. Preparing or configuring a release does not itself authorize publishing.
If the user has already explicitly authorized this release, proceed; otherwise
obtain authorization before pushing the release tag.

Commit the intended release files as `release: vVERSION`, following the user's
branch/PR workflow. Once the release commit is on `main`, create an annotated
`vVERSION` tag for that exact commit and push that tag. Do not push unrelated tags.
Manual dispatch of `publish.yml` is always a dry run; only a tag push publishes.

## Verify and recover

Find the workflow run for the exact tag and commit, watch it to completion, and
inspect failed-job logs if needed. Success requires Rýni on PyPI and the
GitHub Release; share links to both.

For configuration or transient failures, rerun failed jobs on the same run so
the original tested artifacts are reused. Uploads resume only for identical
files. Report any partial publication clearly. If source must change, prepare a
new version; never automatically delete or move a release tag. If a retry fails
for the same reason, inspect the cause before retrying again.
