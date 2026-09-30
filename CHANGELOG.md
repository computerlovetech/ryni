# Changelog

Notable changes to ryni are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.2] - 2026-09-30

### Added

- Restore the MkDocs documentation site with the original styling, current Rust
  CLI guides, uv-managed dependencies, and GitHub Pages deployment.
- A repository release skill that prepares the version and changelog, publishes
  the release, and verifies the published installer.

### Changed

- Show diagnostics with source snippets, underlined Markdown links, terminal
  colors, and a concise error count.
- Introduce ryni as a harness linter written in Rust, with built-in rule
  documentation and a preview of upcoming team rule packs in the README.
- Maintain dated, categorized release notes and version comparison links.

## [0.2.1] - 2026-09-30

### Added

- Built-in validation of Agent Skills metadata and local Markdown links.
- Prebuilt binaries for macOS (Apple Silicon and Intel), Linux (ARM64 and
  x86-64, static musl), and Windows (x86-64).
- Shell and PowerShell installers. No runtime or compiler is required.

### Changed

- Replace the Python implementation with a standalone Rust CLI. Built-in checks
  run automatically without a ryni configuration file.

### Removed

- The Python rule-pack API. Custom Python packs are not supported by the Rust CLI.

## [0.1.11] - 2026-09-23

### Added

- Rýni's `cached_per_check` helper lets rule packs share discovery, file reads,
  and parsing within a check run. Cached data is cleared after attempted fixes
  and discarded between runs.
- Tag-driven Rýni releases to PyPI and GitHub, with branch dry runs and checks
  of the installed CLI, baseline rules, and bundled skill.
- A repository-local `ryni-release` skill and maintainer release guide.

### Changed

- Rýni dispatches file rules by filename and skips file discovery when only
  repository rules are active.
- Release Rýni independently of tidy-harness, which will have its own repository
  and publishing pipeline.

- Publish the documentation site, refresh the README and branding, and document
  shared caching for rule-pack authors.

### Fixed

- Test tidy-harness directly from the working tree so a cached build cannot hide
  changes to its rules.

[Unreleased]: https://github.com/computerlovetech/ryni/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/computerlovetech/ryni/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/computerlovetech/ryni/compare/v0.1.11...v0.2.1
[0.1.11]: https://github.com/computerlovetech/ryni/releases/tag/v0.1.11
