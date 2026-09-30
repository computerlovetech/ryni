# ryni

A Rust CLI for checking repository conventions used by coding agents.

Ryni checks local Markdown links and
[Agent Skills metadata](https://agentskills.io/specification).

## Install

With Rust and Cargo installed, run from this repository:

```sh
cargo install --path . --locked
```

This installs `ryni` into Cargo's binary directory (normally `~/.cargo/bin`), which
must be on your PATH. Rerun this command after source changes to update your
installed executable. Prebuilt releases and a curl installer are not available yet.

## Check

```sh
ryni check                # Current directory
ryni check ./my-project   # A project directory
ryni check ./skills/review # A single skill directory
```

No configuration is needed. Ryni recursively checks `.md` and `.markdown` files
(case-insensitive extensions) for broken local links. Files named exactly
`SKILL.md` also receive all five Agent Skills metadata checks. Hidden directories such as `.agents/skills` are
included. Nested symlinks are skipped. No ignore-file filtering is applied.
Existing `ryni.toml` files are ignored and can be deleted.

Example output:

```text
skills/review/SKILL.md: skill-description Field 'description' must be a nonempty string of at most 1024 characters

Found 1 violation(s).
```

A clean scan prints `All checks passed!`. When no supported files are found,
ryni prints `No supported files found.` and exits successfully.

Exit codes: `0` passed or no supported files, `1` violations, `2` execution error.
Use the same command in CI. Checks never modify project files.

## Built-in rules

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
directories, or reject additional frontmatter fields. The earlier generic
`path-exists` and `required-headings` rules are no longer supported.

## Local Markdown links

Links resolve relative to the Markdown file containing them, including `../`
paths. Images and reference-style links are checked too. Diagnostics point to the
link's start (or its reference use), with one-based line and character column:

```text
README.md:12:1: markdown-local-link Target "docs/testing.md" does not exist
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
intentional broken links are reported too. There are no suppressions yet.

## Development

```sh
cargo run -- check .
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
cargo fmt --check
```

Checking this repository discovers the valid skill fixture in
`tests/fixtures/skills`. Rule implementations live in `src/rules/mod.rs`.
Team rule authoring and binary distribution remain deferred.
