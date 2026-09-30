---
name: ryni-release
description: Release ryni with an optional version number. Use when asked to publish or prepare a ryni release, including updating its changelog, version, tag, and verifying distribution.
---

# Release ryni

Follow [RELEASE.md](../../../RELEASE.md) as the single source of truth.

- Accept an optional version: `$ryni-release 0.3.0`. With no version, choose it
  using the guide's version policy and proceed without a version confirmation.
- A request to run this release skill authorizes the release commit, pushes,
  tag, and publication. Honor explicit prepare-only requests by stopping before
  committing or publishing. Creating or editing this skill does not run it.
- Curate the changelog from actual changes; preserve existing release history.
- Complete verification and report the version, release URL, and install command.
  If blocked, report the exact failed step and any already-published state.
