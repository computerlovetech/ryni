# Changelog

Release history for the `ryni` package. Rule packs such as `tidy-harness` have
independent releases.

Release notes are maintained here starting after 0.1.1. Earlier changes are
recorded in Git history.

## [Unreleased]

### Added

- Opt-in `ryni check --profile` reports engine stages, rule and fix timings, and
  shared-helper cache hits and misses. Python callers can pass a `CheckProfile`.
- A bundled `ryni-rule-author` skill with a runnable shared-analysis example and
  API reference. Install it with `ryni skill install --name ryni-rule-author`.
- Guidance for composing shared analysis and measuring complete rule packs.

### Changed

- File discovery retains only filenames used by active rules before constructing
  and sorting target paths.

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

### Docs

- Publish the documentation site, refresh the README and branding, and document
  shared caching for rule-pack authors.

### Fixed

- Test tidy-harness directly from the working tree so a cached build cannot hide
  changes to its rules.
