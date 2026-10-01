# Built-in rules

These rules run automatically. The five `skill-*` rules apply only to files
named exactly `SKILL.md` and follow the
[Agent Skills specification](https://agentskills.io/specification).
`markdown-local-link` applies to all scanned Markdown files.

| Rule | Check |
| --- | --- |
| `markdown-local-link` | Relative Markdown links and images must point to existing files or directories. |
| `skill-frontmatter` | Opening and closing `---` delimiters, valid YAML, and a mapping with string keys. Duplicate YAML keys are rejected. |
| `skill-name` | Required string of 1–64 characters, lowercase Unicode letters/numbers and hyphens, with no leading, trailing, or consecutive hyphens. |
| `skill-directory-name` | The name exactly matches the directory containing `SKILL.md`. |
| `skill-description` | Required nonblank string, at most 1,024 characters. |
| `skill-optional-fields` | `license` and `allowed-tools` must be strings; `compatibility` must be a nonblank string of at most 500 characters; `metadata` must map strings to strings. |

Malformed frontmatter produces one `skill-frontmatter` finding. Dependent checks
are skipped for that file. Character limits count Unicode
characters, not UTF-8 bytes. Names are not trimmed or Unicode-normalized.

These checks cover the requirements above, not full semantic compliance. They do
not judge description quality, validate instruction bodies, require optional
directories, or reject additional frontmatter fields.

## Local Markdown links

Links resolve relative to the Markdown file containing them, including `../`
paths. Images and reference-style links are checked too. Diagnostics point to the
link's start (or its reference use), with one-based line and character column:

```text
markdown-local-link: Target "docs/testing.md" does not exist
 --> README.md:12:1
```

`[Guide](guide.md#installation)` checks that `guide.md` exists; it does not check
whether the heading exists. Queries are also removed before checking. URL-encoded
paths such as `my%20guide.md` are decoded. Existing directories and links to files
outside the scanned directory are accepted. Linked symlinks are resolved.

The rule skips URL schemes (including web and email links), root-relative links
such as `/docs/guide`, network URLs, and same-document anchors. Code examples,
frontmatter, raw HTML attributes, and plain-text paths are not checked. Undefined
Markdown reference labels are not filesystem targets and are not checked.

Paths are checked literally: no automatic `.md` extension, website routing, or
build-template expansion. Generated targets must already exist when checking;
intentional broken links are reported too. Invalid filenames and paths that are
too long produce findings without stopping the scan. Other inspection failures,
such as permission errors, remain execution errors. There are no suppressions yet.

