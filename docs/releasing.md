# Releasing Rýni

`ryni` and `tidy-harness` use matching versions and one `vX.Y.Z` tag. A tag pushed
from a commit on `main` runs validation and the existing CI checks, builds and
tests both distributions, publishes `ryni` followed by `tidy-harness`, verifies
a fresh installation from PyPI, and creates a GitHub Release from `CHANGELOG.md`.
The GitHub Release also includes both wheels and source distributions.

## One-time publisher setup

Create a GitHub environment named `pypi` in the repository's Settings →
Environments. Under deployment branches and tags, select specific branches and
tags and add a **tag** rule for `v*`.

Register a GitHub Trusted Publisher on **each** existing PyPI project:

- [ryni publishing settings](https://pypi.org/manage/project/ryni/settings/publishing/)
- [tidy-harness publishing settings](https://pypi.org/manage/project/tidy-harness/settings/publishing/)

Use these values for both:

| Field | Value |
| --- | --- |
| Owner | `computerlovetech` |
| Repository | `ryni` |
| Workflow filename | `publish.yml` |
| Environment | `pypi` |

The workflow uses `uv publish` with OIDC. No PyPI token or GitHub secret is needed.
See [PyPI's setup instructions](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

## Prepare a release

The maintainer skill lives in [skills/ryni-release/SKILL.md](../skills/ryni-release/SKILL.md).
It is separate from the `ryni-check` skill shipped to users. To make the release
skill discoverable locally, run these from the repository root (only if the
destination does not already exist):

```bash
mkdir -p .agents/skills .claude/skills
ln -s ../../skills/ryni-release .agents/skills/ryni-release
ln -s ../../skills/ryni-release .claude/skills/ryni-release
```

Then ask your agent to use `ryni-release` to prepare a release, specifying the
version or patch/minor/major/beta bump. You can also follow these steps manually:

1. Start from a clean, current `main`. Fetch tags and inspect changes since the
   previous release. Before the first tag-driven release, use the 0.1.1 release
   preparation commit `edf0e6b` as the comparison baseline.
2. Set the same new version in `pyproject.toml` and
   `examples/tidy-harness/pyproject.toml`. Review the pack's `ryni` dependency
   bounds against the API it uses. A new minor series may need new bounds;
   prereleases need bounds that admit that prerelease. Run `uv lock` afterward.
3. Update affected documentation and the bundled `ryni-check` skill if behavior
   changed. Move the completed changelog entries into a section such as
   `## [0.1.2] - YYYY-MM-DD` with the actual release date, leaving a fresh
   `## [Unreleased]` section above it. Include changes to both packages.
4. Run the local checks below and inspect the diff. Merge the preparation into
   `main` before pushing its release tag.

Stable tags use `vX.Y.Z`. Alpha, beta, and release candidates use `vX.Y.Za1`,
`vX.Y.Zb1`, and `vX.Y.Zrc1` and are marked as prereleases on GitHub. PyPI versions
already published cannot be replaced; choose a new version for changed contents.

## Local validation

Use the prepared version in place of `v0.1.2`. Omit `--tag` to validate a branch
without a release changelog entry; this uses `[Unreleased]` instead.

```bash
uv sync --locked --group docs
uv run --no-sync python scripts/release.py --tag v0.1.2
uv run --no-sync ruff check .
uv run --no-sync pytest tests
uv run --with-editable . --with-editable ./examples/tidy-harness pytest examples/tidy-harness/tests
uv run --no-sync ryni check .
uv run --no-sync mkdocs build --strict
```

Build in a fresh directory so older distributions cannot enter a release:

```bash
release_dir=$(mktemp -d)
uv build --no-sources --out-dir "$release_dir/ryni"
uv build examples/tidy-harness --no-sources --out-dir "$release_dir/tidy-harness"
version=$(uv run --no-sync python scripts/release.py)
uv run --isolated --no-project \
  --with "$release_dir"/ryni/*.whl --with "$release_dir"/tidy-harness/*.whl \
  python scripts/smoke_release.py "$version"
rm -r "$release_dir"
```

## GitHub dry run

Once `publish.yml` is on the default branch, open Actions → Publish → Run workflow
and select the branch to test, or run:

```bash
gh workflow run publish.yml --ref YOUR_BRANCH
```

**Every manual run is a dry run**, even if a tag is selected. It validates package
versions and compatibility, runs CI, tests the built wheels, and saves
`release-dist` and `release-notes` artifacts. It never publishes to PyPI or creates
a GitHub Release. A tag pushed to GitHub is the only publishing trigger.

## Publish and verify

After reviewing the prepared release on `main`:

```bash
git tag -a v0.1.2 -m "Release v0.1.2"
git push origin v0.1.2
gh run list --workflow publish.yml --branch v0.1.2
gh run watch RUN_ID --exit-status
gh release view v0.1.2
```

Choose the run matching the exact tag and commit. The workflow verifies both
versions from PyPI, the CLI entry point, installed rule-pack discovery, and the
bundled skill before creating the GitHub Release.

## Recover from a failure

Publishing two projects is sequential, not atomic. If `ryni` uploads successfully
and `tidy-harness` fails, the core version remains live. Fix external configuration
or a transient failure, then **rerun failed jobs in the same workflow run** to
reuse its tested artifacts. `uv publish --check-url` skips files only when they
are identical to those already on PyPI; differing contents fail.

The same rerun approach applies if verification or GitHub Release creation fails
after both uploads. Verification retries briefly for PyPI propagation. An
existing GitHub Release is preserved on a rerun.

If source or release metadata must change, prepare a new version and tag. Do not
move or delete a published tag, overwrite a PyPI release, or assume rebuilding
will reproduce the original artifacts. Release artifacts are subject to the
repository's Actions retention period; keep the successful run available while
recovering a partial release.
