# tidy-harness

Opinionated agent harness conventions for [Rýni](https://github.com/computerlovetech/ryni):
one source of truth, discoverable docs, and focused instructions.

## Rules

| ID | Kind | Convention |
| --- | --- | --- |
| TIDY001 | Check | Keep every `AGENTS.md` at or below 250 lines. |
| TIDY002 | Check | Make each `CLAUDE.md` a symlink to its adjacent `AGENTS.md`. |
| TIDY003 | Check | Give documentation directories a `README.md` index. |
| TIDY004 | Check | Keep local Markdown links and heading references valid. |
| TIDY005 | Check | Make documentation reachable from the root `AGENTS.md`. |
| TIDY006 | Check | Keep installed skills untracked and Git-ignored. |
| TIDY007 | Review | Resolve contradictory instructions. |
| TIDY008 | Review | Keep one authoritative source for guidance. |
| TIDY009 | Review | Keep documentation aligned with implementation. |
| TIDY010 | Review | Give skills task-specific triggers. |
| TIDY011 | Review | Keep skills focused, or route to supporting workflows. |
| TIDY012 | Review | Explain when references are relevant. |
| TIDY013 | Review | Keep instructions necessary and actionable. |

Reviews require cited evidence and specific corrections. They account for scope,
exceptions, and contextual examples; they do not edit files or execute documented
commands. Missing evidence or unfinished coverage is reported as incomplete.

## Scope

All rules target the repository. Nested `AGENTS.md` and `CLAUDE.md` files are included.
A `CLAUDE.md` is optional, but must point to the adjacent existing `AGENTS.md` if present.

Documentation means Markdown under any `docs/` directory. Each `docs/` root and
subdirectory containing Markdown, directly or below it, needs an index. Asset-only
subdirectories do not. Standalone website content is outside this scope.

Link validation also covers `AGENTS.md` and Markdown under locally owned `skills/`
directories. It parses CommonMark inline links, reference links and images, ignoring
code examples. Markdown fragments use GitHub-style heading IDs, including duplicate
heading suffixes, explicit `{#id}` headings, and HTML `id`/anchor `name` attributes.
Custom renderer-generated IDs and raw HTML links are not validated. Absolute web
routes, external URLs and links outside the repository are not checked.

Reachability starts at the root `AGENTS.md`, follows Markdown links (including links
through other repository Markdown files), and treats directory links as links to
`README.md`. Images do not establish reachability. Every in-scope documentation file
must be reachable. A repository with no documentation needs no entry point for this rule.

Scans skip Git-ignored files; installed `.agents/skills/`, `.claude/skills/`, and
`.github/skills/`; and directories named `.git`, `.venv`, `venv`, `node_modules`,
`__pycache__`, `.pytest_cache`, `.ruff_cache`, `dist`, `build`, `_build`, `site`,
`fixtures`, `testdata`, or `generated`. Directory symlinks are not traversed.
Reading a document symlink outside the repository reports an error rather than
silently claiming a completed check.

TIDY006 checks existing installation directories, including nested scopes. It checks
both Git's index and ignore behavior, so adding an ignore pattern alone does not
hide already tracked files. Without Git metadata, this rule is skipped. The other
checks still work outside Git repositories.

## Install and run

Version 0.1.1 adds the rules above and requires Rýni 0.1.1 or later in the 0.1 series.
The original tidy-harness 0.1.0 release contained no rules.

```bash
uv add --dev 'ryni>=0.1.1,<0.2' 'tidy-harness>=0.1.1,<0.2'
uv run ryni check .
```

The CLI runs the six deterministic checks and prepares seven agent reviews.
Use the `ryni-check` skill in an agent with sub-agent support to complete reviews,
asking it to use `uv run ryni`. To run only deterministic checks, add
`--deterministic` explicitly.

## Development

This package is versioned independently under `packages/tidy-harness/`.
From the repository root:

```bash
uv run --with-editable . --with ./packages/tidy-harness pytest packages/tidy-harness/tests
uv build packages/tidy-harness --out-dir packages/tidy-harness/dist
```
