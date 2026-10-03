# Built-in rules

The six stable rules run automatically. The five stable `skill-*` rules apply only to files
named exactly `SKILL.md` and follow the
[Agent Skills specification](https://agentskills.io/specification).
`markdown-local-link` applies to all scanned Markdown files.

<!-- rules:start -->
| Rule | Status | Check |
| --- | --- | --- |
| `skill-frontmatter` | stable | SKILL.md must start with delimited YAML containing a mapping with unique string keys. |
| `skill-name` | stable | The name must contain 1–64 lowercase Unicode letters, numbers or hyphens, without leading, trailing or consecutive hyphens. |
| `skill-directory-name` | stable | The skill name must exactly match its containing directory. |
| `skill-description` | stable | The description must be a nonblank string of at most 1,024 Unicode characters. |
| `skill-optional-fields` | stable | Validate license, allowed-tools, compatibility and metadata against the Agent Skills field requirements. |
| `markdown-local-link` | stable | Relative Markdown links and images must point to existing files or directories. URL schemes and document anchors are skipped. |
| `skill-required-metadata` | preview | Skills must contain each configured metadata field with a nonblank string value. |
| `markdown-required-sections` | preview | Markdown documents must contain each configured heading, matched exactly as rendered text. |
| `project-required-files` | preview | Each configured project-relative file must exist. |
| `skill-duplicate-name` | preview | Skill names must be unique among successfully parsed skills in the scan. |
<!-- rules:end -->

Preview conventions require both preview mode and explicit selection. Configure
their requirements in [configuration and team packs](configuration.md). The
`skill-duplicate-name` rule runs across included skill files; `project-required-files`
checks the scan root even if no Markdown files were discovered.

Malformed frontmatter produces one `skill-frontmatter` finding. Dependent checks
are skipped for that file. Character limits count Unicode
characters, not UTF-8 bytes. Names are not trimmed or Unicode-normalized.

The stable checks cover the requirements above, not full semantic compliance. They do
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

