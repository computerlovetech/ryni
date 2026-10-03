<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/ryni-wordmark-dark.svg">
    <img src="assets/ryni-wordmark-light.svg" alt="Rýni" width="270" height="72">
  </picture>
</h1>

<p align="center"><strong>A harness linter, written in Rust.</strong></p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="https://computerlovetech.github.io/ryni/">Documentation</a> ·
  <a href="#built-in-rules">Built-in rules</a> ·
  <a href="https://github.com/computerlovetech/ryni/releases">Releases</a>
</p>

Harness engineering is hard. Keeping a team aligned on it is harder. Your coding
agents depend on instructions, skills, and Markdown docs that stay consistent as
projects change. Ryni catches broken local links and invalid Agent Skills
metadata before they get in the way.

- **Check your harness.** Built-in checks for Markdown links and Agent Skills.
- **Run anywhere.** Written in Rust, distributed as a standalone binary.
- **Start immediately.** Run `ryni check .`. No configuration required.

**Team rule packs are coming soon:** define your team's conventions once and
share them across repositories. Today, ryni runs its built-in rules.

## Install

macOS and Linux:

```sh
curl -LsSf https://github.com/computerlovetech/ryni/releases/latest/download/ryni-installer.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://github.com/computerlovetech/ryni/releases/latest/download/ryni-installer.ps1 | iex"
```

No Rust installation is needed. Follow the installer's PATH instructions, then
run `ryni --version`. Rerun the installer to update. Prebuilt archives are also
available on [GitHub Releases](https://github.com/computerlovetech/ryni/releases).

For development, install from this repository with Rust and Cargo:

```sh
cargo install --path . --locked
```

See [RELEASE.md](RELEASE.md) for version pinning, custom install locations, and
the release process.

## Check

```sh
ryni check .              # Current directory
ryni check ./my-project   # A project directory
ryni check ./skills/review # A single skill directory
```

No configuration is needed. Ryni recursively checks `.md` and `.markdown` files
(case-insensitive extensions) for broken local links. Files named exactly
`SKILL.md` also receive all five Agent Skills metadata checks. Hidden directories such as `.agents/skills` are
included unless ignored. Nested symlinks are skipped.

Ryni respects `.gitignore`, `.ignore`, `.git/info/exclude`, and global Git
excludes, including applicable parent and nested ignore files. Git ignore rules
apply inside Git repositories; `.ignore` also works outside them. Matching files
are skipped even if tracked by Git. Global excludes can make scan coverage differ
between your machine and CI.

```sh
ryni check . --no-ignore                  # Disable ignore-file filtering
ryni check . --exclude 'vendor/**' --exclude 'third_party/**'
```

`--exclude` accepts repeatable gitignore-style globs relative to the scan root
and still applies with `--no-ignore`. Patterns containing a slash are relative
to that root; patterns such as `*.md` match at any depth. Quote globs to prevent
shell expansion. Filtering only controls which files are scanned: links to
existing targets inside excluded directories remain valid.

Example output:

```text
markdown-local-link: Target "docs/testing.md" does not exist
 --> README.md:3:1
  |
3 | [Testing](docs/testing.md)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^

Found 1 error.
```

Diagnostics show the rule, file location, and source context. Broken links are
underlined; skill metadata findings show a preview of the file without guessing
an individual field location. Terminal output uses color; redirected output is
plain text. Set `NO_COLOR` to disable color.

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

## Development

```sh
cargo run -- check .
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
cargo fmt --check
```

Checking this repository discovers the valid skill fixture in
`tests/fixtures/skills`. Rule implementations live in `src/rules/mod.rs`.

## Documentation development

The MkDocs source lives in `website/`, with MkDocs Material and the shared
Computerlove styling used by Umbod. Use [uv](https://docs.astral.sh/uv/) to preview or build it:

```sh
uv run --locked --only-group docs mkdocs serve
uv run --locked --only-group docs mkdocs build --strict
```

Python is only used for documentation tooling; the CLI is written in Rust.
Documentation pull requests are built in CI. Changes merged to `main` deploy to
[GitHub Pages](https://computerlovetech.github.io/ryni/).
