# Built-in rules

Rýni includes one baseline rule. Other conventions come from installed packs.

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
ryni rule SKILL001
ryni check . --select SKILL001
```
