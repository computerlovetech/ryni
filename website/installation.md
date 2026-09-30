# Installation

Ryni is written in Rust and distributed as a standalone binary. End users need
neither Rust nor Python.

## Standalone installer

=== "macOS and Linux"

    ```sh
    curl -LsSf https://github.com/computerlovetech/ryni/releases/latest/download/ryni-installer.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy Bypass -c "irm https://github.com/computerlovetech/ryni/releases/latest/download/ryni-installer.ps1 | iex"
    ```

The installer chooses the appropriate build, installs into `~/.local/bin`
(under your user home on Windows too), and configures PATH. Follow its
instructions to restart your terminal or activate PATH, then run:

```sh
ryni --version
ryni check .
```

Prebuilt binaries support macOS on Apple Silicon and Intel, Linux on ARM64 and
x86-64, and Windows on x86-64. Linux builds use static musl. Archives and checksums
are available on [GitHub Releases](https://github.com/computerlovetech/ryni/releases).
Builds are not code-signed or notarized.

## Update or pin a version

Rerun the installer to update. To install a specific release, replace
`latest/download` in its URL with `download/vVERSION`, using an existing release
such as `download/v0.2.1`. Prereleases require their version-specific URL.

## Custom locations and CI

Set `RYNI_UNMANAGED_INSTALL` to your chosen installation directory. This skips
shell profile and PATH changes. Add that directory to PATH yourself or invoke
its binary by absolute path. For example, in a Unix shell:

```sh
curl -LsSf https://github.com/computerlovetech/ryni/releases/download/v0.2.1/ryni-installer.sh | RYNI_UNMANAGED_INSTALL="$PWD/.tools" sh
./.tools/ryni check .
```

If another installation takes precedence, check `command -v ryni` on macOS/Linux
or `Get-Command ryni` in PowerShell.

## Build from source

With Rust and Cargo installed, run from a checkout of the repository:

```sh
cargo install --path . --locked
```

The current CLI replaces the earlier Python implementation. Python rule packs
are not supported. Team rule packs for the Rust tool are coming soon.
