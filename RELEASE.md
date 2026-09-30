# Releasing ryni

Releases are built and hosted on GitHub. No crates.io token or custom server is
required. GitHub Actions uses the repository's automatic `GITHUB_TOKEN`.

## Publish a version

Run the repository skill with `$ryni-release` or `$ryni-release 0.3.0`.
It follows the steps below through publication and verification. Ask for
"prepare only" to update and validate the release files without publishing.

1. Inspect the working tree, branch, and remote. Fetch `origin` and its tags.
   Release from `main`, including the current `origin/main`; never force-push.
   Preserve unrelated work. If uncommitted changes affect the release and their
   intended inclusion is unclear, stop and explain rather than silently include
   or discard them. Confirm GitHub authentication and repository access.
2. Review the changes since the latest **published** GitHub release, together
   with `CHANGELOG.md`. Failed release tags are reserved versions, not published
   history. If there is nothing to release, report that and stop.
3. Use the supplied version (an optional `v` prefix is accepted). Otherwise,
   choose the next patch for fixes or maintenance, or the next minor for new
   features. Before 1.0, incompatible changes also require a minor bump; never
   infer a 1.0 release. Choose a valid SemVer version newer than the current
   package and published releases, skipping existing local and remote tags.
   An explicit version must meet those constraints; report conflicts instead of
   substituting another version. State the chosen version and proceed.
4. Update `Cargo.toml` and run `cargo check` to update `Cargo.lock`. Prepare the
   changelog as described below. Check that both manifests and the changelog
   agree on the version, and inspect the diff for unintended changes.
5. Run `cargo fmt --check`, `cargo test --locked`,
   `cargo clippy --all-targets --locked -- -D warnings`, and
   `cargo run --locked -- check .`. If distribution settings changed, regenerate
   and validate the workflow as described below. Stop on failing checks.
6. Commit only the intended release files with `Release vVERSION`, push `main`,
   then create an annotated tag on that exact commit and push just that tag
   (replace `VERSION` with the chosen version):

   ```sh
   git tag -a vVERSION -m "Release vVERSION"
   git push origin vVERSION
   ```

7. Watch the Release workflow for that tag **and commit**, using `gh run list`,
   `gh run watch`, and `gh run view`. Verify the public GitHub release contains
   the correct changelog notes, five platform archives, checksums, and both
   installers. A successful tag push alone is not completion.
8. Download the published, version-pinned installer for the current supported
   platform. Run it with `RYNI_UNMANAGED_INSTALL` pointing to a temporary
   directory, then invoke that binary's `--version` and `check` on the existing
   valid fixture at `tests/fixtures/skills/demo-skill`. Check the version matches
   and the check succeeds. Clean up temporary downloads and installs. Report
   the release URL and install command; use the pinned URL for prereleases.

Use a new version for subsequent releases; do not replace published tags.
The Release workflow tests, builds five platform archives, generates shell and
PowerShell installers with checksums, and smoke-tests installs/reinstalls on all
five platforms before creating the public GitHub Release. Failed builds or smoke
tests prevent publication. Retry failed jobs once for a clearly transient
failure. Otherwise stop and report the failure and publication state. Source
fixes require a new version and tag; do not move/delete tags or start a chain of
automatic version bumps.

## Maintain the changelog

Follow [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
Keep one `## [Unreleased]` section at the top and add notable changes there as
work lands. During a release, reconcile it with the actual changes since the
last published release: summarize changes for people, not individual commits.

Move those notes into `## [VERSION] - YYYY-MM-DD` using the current release date,
and leave a fresh `Unreleased` section. Use only nonempty `Added`, `Changed`,
`Deprecated`, `Removed`, `Fixed`, and `Security` categories. Explain incompatible
changes explicitly. Preserve earlier entries and dates; keep newest releases
first. Update the comparison links at the bottom: `Unreleased` compares the new
tag to `HEAD`, and the new version compares the previous published tag to it.

cargo-dist reads the changelog to include the version's notes in the GitHub
release, alongside its generated installation and download information.

## Install and update

macOS and Linux:

```sh
curl -LsSf https://github.com/computerlovetech/ryni/releases/latest/download/ryni-installer.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://github.com/computerlovetech/ryni/releases/latest/download/ryni-installer.ps1 | iex"
```

Rerun the command to update. To pin a release, replace `latest/download` with
`download/v0.2.1`. Installers use `~/.local/bin` (the user's home directory on
Windows too) and configure PATH. Follow their instructions to restart your
terminal or activate PATH in the current shell. Rust is not needed.

For CI or a custom destination, set `RYNI_UNMANAGED_INSTALL` to the destination
directory. This avoids changing shell profiles or PATH. Add that directory to
PATH yourself or run the installed executable by its absolute path.

The installer warns if another `ryni` appears earlier on PATH. If migrating from
`cargo install`, check `command -v ryni` (PowerShell: `Get-Command ryni`) so you know
which copy runs. The binary archives and `.sha256` files are also available for
manual installation. Builds are not code-signed or notarized.

## Maintain the workflow

`dist-workspace.toml` configures cargo-dist 0.33.0. Install that version using
[the upstream release](https://github.com/axodotdev/cargo-dist/releases/tag/v0.33.0).
Run `dist generate` after changing the distribution settings; do not hand-edit
`.github/workflows/release.yml`. `dist plan` validates the generated workflow.

To build and test the installer for your current supported platform:

```sh
dist build
python3 scripts/smoke_install.py target/distrib
```

The smoke script requires Python 3.11+ and serves artifacts on localhost. It
installs into a temporary directory and cleans up without modifying your PATH.
Python is only a test dependency; end users need neither Python nor Rust.
