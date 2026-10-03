# Configuration and team packs

`ryni check .` needs no configuration. To customize it, add `ryni.toml` at the
scan root. For a file input, the scan root is that file's parent. Ryni does not
search ancestor directories or merge nested configuration files.

```toml
schema-version = 1

[lint]
select = ["all"]
ignore = ["skill-directory-name"]

[discovery]
exclude = ["vendor", "target", "**/generated/**"]
respect-ignore = true
```

Unknown keys, rule IDs, malformed globs and unsupported schema versions are
execution errors. `--config path/to/ryni.toml` selects a configuration explicitly;
its path is relative to the working directory. `--isolated` ignores all
configuration and packs. These two options cannot be combined.

## Selection and precedence

Settings resolve in this order, from lowest to highest priority:

1. Built-in defaults: all six stable rules.
2. Local packs, in their listed order.
3. The repository configuration.
4. Explicit CLI overrides.

Each provided option replaces the earlier value. Arrays replace rather than
append; an empty array clears the earlier value. Unspecified options retain the
earlier value. `select` sets enabled rules; `ignore` is applied afterward, even
when selection came from a later layer. Use a repository `ignore = []` to clear
a pack's ignore list.

Rule selectors are exact IDs or `all`. `all` includes stable rules and, when
preview is enabled, preview rules. Without explicit selection, enabling preview
does not change the default set. Selecting a preview rule without enabling
preview is an error. Ignoring a preview rule does not require preview.

If a selected skill rule needs metadata, malformed frontmatter produces a
`skill-frontmatter` prerequisite finding even if that rule was not selected or
was ignored. Dependent checks are skipped. Selecting only Markdown rules does
not report skill metadata problems.

Inspect the effective settings with:

```sh
ryni settings .
ryni settings . --config config/ryni.toml --select skill-name
ryni rule
ryni rule markdown-local-link
ryni rule --output-format json
```

## A local team pack

A pack contains versioned rule selections and declarative requirements. Commit
or vendor it with the repositories that use it. For example, `config/team.toml`:

```toml
schema-version = 1
name = "example/team"
version = "1.0.0"
requires-ryni = ">=0.2.2, <1"

[lint]
preview = true
select = ["all"]
required-metadata = ["owner"]
required-sections = ["Usage"]
required-files = ["AGENTS.md"]
```

Then reference it from `ryni.toml`:

```toml
schema-version = 1
packs = [{ path = "config/team.toml", version = "1.0.0" }]
```

Pack paths resolve relative to the configuration file. Versions must be exact
SemVer versions, not ranges, and must match the pack's declared version.
`requires-ryni` is a SemVer compatibility requirement. Pack names must be nonblank
and unique within a configuration. Packs cannot import other packs.

The version pin validates the declared version; it is not a content-integrity
lock. Reproducibility also requires keeping the pack contents pinned in version
control. There is no remote pack fetching or executable plugin loading.

Requirements are parameters of the corresponding preview rules. They have no
effect unless those rules are selected:

| Option | Rule | Meaning |
| --- | --- | --- |
| `required-metadata` | `skill-required-metadata` | Top-level YAML fields that must contain nonblank strings. |
| `required-sections` | `markdown-required-sections` | Exact, case-sensitive heading text required in every scanned Markdown file. Inline emphasis and code are read as text; fenced examples do not count. |
| `required-files` | `project-required-files` | Regular files required relative to the scan root, independent of exclusions. Existing directories do not satisfy this requirement. |

Lists must contain unique, nonblank entries. Required file paths must be portable
relative paths without `.` or `..` components, colons, backslashes or null bytes.
The duplicate-name rule compares parsed skill names across the files included in
the scan. A file-only scan cannot detect duplicates elsewhere in the repository.

## Discovery

By default, hidden directories are included, nested symlinks are skipped, and
ignore-file filtering is enabled. Linked Markdown targets may still resolve
through symlinks, point outside the project, or refer to excluded files.

Exclusions match paths relative to the scan root and their ancestors. Excluding
`vendor` excludes its descendants. Exclusions apply even to explicitly supplied
files. A file-only scan uses the parent as root, so excluding that file uses its
basename. Patterns use gitignore syntax: patterns containing a slash are relative
to the scan root; patterns such as `*.md` match at any depth.

Ryni respects `.gitignore`, `.ignore`, `.git/info/exclude`, and global Git
excludes, including applicable parent and nested ignore files. Git ignore rules
apply inside Git repositories; `.ignore` also works outside them. Matching files
are skipped even if tracked by Git. Global excludes can make coverage differ
between machines. Explicit file inputs bypass ignore-file filtering but still
honor Ryni exclusions. `respect-ignore = false` or `--no-ignore` disables
ignore-file filtering; `--respect-ignore` enables it again when configuration
has disabled it. `--exclude` replaces the configuration's exclusion list and
may be repeated; it also applies with `--no-ignore`.

A scan continues after recoverable read, discovery or target-inspection errors.
Its available findings are still reported, but an incomplete scan exits with code
`2`, even if it also has lint findings.
