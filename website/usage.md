# CLI usage

```sh
ryni check .              # Current directory
ryni check ./my-project   # A project directory
ryni check ./skills/review # A single skill directory
```

No configuration is needed. Ryni recursively checks `.md` and `.markdown` files
(case-insensitive extensions) for broken local links. Files named exactly
`SKILL.md` also receive all five Agent Skills metadata checks. Hidden directories such as `.agents/skills` are
included. Nested symlinks are skipped. No ignore-file filtering is applied.

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
Use the same command in CI. Checks modify files only when `--fix` is explicitly enabled.

## CI

Install a pinned version using the [installer](installation.md#custom-locations-and-ci),
then run `ryni check .` in your checkout. A finding fails the command with exit
code `1`, so CI can use the same checks as local development.

The six stable rules run by default. [Configuration and team packs](configuration.md)
can select rules, enable preview conventions and control discovery. There are no
inline suppressions yet.

```sh
ryni check README.md --select markdown-local-link
ryni check . --output-format json
ryni check . --exclude vendor --respect-ignore
ryni check . --threads 4 --timings
```

See [structured output and fixes](output.md) for machine integration and opt-in
fix application. Recoverable execution errors retain other findings and exit with
code `2`.

See the [rule reference](rules.md) for the standards checked and edge cases.
