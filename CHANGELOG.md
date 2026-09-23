# Changelog

Rýni and tidy-harness are released together with matching versions. Entries name
the affected package when a change applies to only one of them.

Release notes are maintained here starting after 0.1.1. Earlier changes are
recorded in Git history.

## [Unreleased]

### Added

- Coordinated, tag-driven releases to PyPI and GitHub, with branch dry runs and
  checks of the installed CLI, rule pack, and bundled skill.
- A repository-local `ryni-release` skill and maintainer release guide.

### Changed

- Reuse discovery and parsed documents across tidy-harness checks to reduce
  repeated work.

### Fixed

- Test tidy-harness directly from the working tree so a cached build cannot hide
  changes to its rules.
