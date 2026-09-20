# Built-in rules

Rýni includes four deterministic checks for files named `SKILL.md`, based on the
[Agent Skills specification](https://agentskills.io/specification). They check
frontmatter structure, skill names, directory matches, and description length.
These are portable-format requirements; individual hosts may accept looser formats.
Other conventions come from installed packs. No AGENTS.md checks are built in.

## SKILL001: skill-frontmatter

**Kind:** deterministic · **Scope:** files named `SKILL.md`

A skill must start with YAML frontmatter containing nonempty string `name` and
`description` fields. Additional fields are allowed.

```markdown
---
name: review-migrations
description: Review database migrations for compatibility and rollback risks.
---

# Review migrations
```

Rýni reports missing or unclosed delimiters, invalid YAML, a non-mapping frontmatter
value, or missing/empty/non-string required fields. UTF-8 BOMs and multiline
strings are accepted. This rule checks structure, not instruction quality or
naming conventions. It has no automatic fix.

```bash
uv run ryni rule SKILL001
uv run ryni check . --select SKILL001
```

## SKILL002: skill-name

The `name` must contain 1–64 lowercase alphanumeric characters or hyphens.
Leading, trailing, and consecutive hyphens are not allowed. Spaces and underscores
are not allowed. Unicode names are supported, using NFKC normalization before
validation, consistent with the specification's reference validator.

Examples: `review-migrations` and `rýni` are valid; `Review`, `review_skill`,
`-review`, and `review--skill` are invalid.

## SKILL003: skill-directory-match

The `name` must match the directory containing `SKILL.md`. For example,
`skills/review-migrations/SKILL.md` must declare `name: review-migrations`.
Both names use Unicode NFKC normalization for comparison. The check uses the
discovered path without resolving symbolic links.

## SKILL004: skill-description-length

The `description` must contain at most 1,024 characters. The check counts the
parsed YAML string, including its whitespace and newlines. It does not count
bytes, YAML quotes, or indentation used to write multiline strings.

## Run the baseline

All four rules run by default. To select only these checks:

```bash
uv run ryni check . --select SKILL001,SKILL002,SKILL003,SKILL004
```

Structural failures and missing, empty, or non-string required fields are reported
by `SKILL001`. The other rules skip fields they cannot validate, rather than repeat
those findings. Keep `SKILL001` selected when you need structural validation.
All checks are read-only; none has an automatic fix. Additional metadata fields
remain allowed and are not validated by these checks.
