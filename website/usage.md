# CLI usage

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

## CI

Install a pinned version using the [installer](installation.md#custom-locations-and-ci),
then run `ryni check .` in your checkout. A finding fails the command with exit
code `1`, so CI can use the same checks as local development.

All built-in rules are always active. There are no rule-selection settings,
configuration files, suppressions, or automatic fixes yet.

See the [rule reference](rules.md) for the standards checked and edge cases.
