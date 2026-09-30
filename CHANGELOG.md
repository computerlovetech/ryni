# Changelog

## 0.2.1

- Replace the earlier Python implementation with a standalone Rust CLI.
- Automatically validate Agent Skills metadata and local Markdown links.
- Distribute prebuilt binaries for macOS (Apple Silicon and Intel), Linux
  (ARM64 and x86-64, static musl), and Windows (x86-64).
- Add shell and PowerShell installers. No runtime, compiler, or ryni
  configuration file is required.

This release replaces the Python rule-pack API; those custom packs are not
supported by the Rust CLI.
