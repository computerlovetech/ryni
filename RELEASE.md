# Releasing ryni

Releases are built and hosted on GitHub. No crates.io token or custom server is
required. GitHub Actions uses the repository's automatic `GITHUB_TOKEN`.

## Publish a version

1. Update the package version in `Cargo.toml` and run `cargo check` to update
   `Cargo.lock`. Add release notes to `CHANGELOG.md`.
2. Run `cargo test --locked`, `cargo clippy --all-targets --locked -- -D warnings`,
   and `cargo fmt --check`. Commit and push the changes to `main`.
3. Tag that commit with the matching version and push just that tag:

   ```sh
   git tag v0.2.0
   git push origin v0.2.0
   ```

Use a new version for subsequent releases; do not replace published tags.
The Release workflow tests, builds five platform archives, generates shell and
PowerShell installers with checksums, and smoke-tests installs/reinstalls on all
five platforms before creating the public GitHub Release. Failed builds or smoke
tests prevent publication. After correcting a transient CI failure, rerun the
failed jobs. For source fixes, create a new version and tag.

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
`download/v0.2.0`. Installers use `~/.local/bin` (the user's home directory on
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
