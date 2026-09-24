# team-harness

An opinionated, research-informed Rýni example pack organized around team jobs.
18 deterministic rules; **no reviews, model calls, or automatic edits**.
See [the research and disagreements](../../docs/research/team-harness.md).

```sh
uv pip install -e . -e examples/team-harness
uv run --no-sync ryni check /path/to/repository --deterministic --profile
```

Installation enables this pack alongside built-ins and other installed packs.
For isolation use `--select TEAM001,TEAM002,...,TEAM018` (expand the list).

| Job | Rules | Exact convention |
| --- | --- | --- |
| Give everyone a shared starting point | TEAM001–002 | Root AGENTS.md, CLAUDE.md or GEMINI.md exists; discovered guidance is nonempty. |
| Keep recurring context small | TEAM003–004 | Always-loaded named instructions ≤250 lines AND ≤16 KiB UTF-8; SKILL.md ≤500 lines. |
| Keep the map usable after changes | TEAM005–008 | No Git start/end/base conflict markers outside code examples; local Markdown links and standalone @imports exist; no @import cycles. |
| Make guidance work on teammates' machines | TEAM009 | No literal user-specific home paths in ordinary prose. |
| Maintain one source of truth | TEAM010–011 | No identical adjacent AGENTS/CLAUDE/GEMINI copies ≥200 characters; no verbatim inherited prose paragraph ≥160 characters. |
| Make skills identifiable and discoverable | TEAM012–015 | YAML name/description required; ASCII kebab-case name ≤64 chars matches folder; description ≤1024 chars; names unique per skills-directory namespace. |
| Finish the shared workflow | TEAM016–017 | No TODO/FIXME followed by fill/write/add/replace in prose; skill has body prose, link, or fenced procedure. |
| Share dependencies | TEAM018 | No standalone @imports from ~/ or another user's home directory. |

Numbers are **pack policy**, not proven optimal model limits. The ASCII name rule
is intentionally stricter than Rýni's Unicode-capable built-in. Select rules to
adopt individual conventions. Findings indicate policy deviations, not project
quality scores or guaranteed improvements in agent task success.

Discovery uses Git tracked plus nonignored untracked files (including tracked
files that match ignore patterns), or a filesystem walk outside Git. Seeds are
AGENTS.md, AGENTS.override.md, CLAUDE.md, GEMINI.md, SKILL.md,
copilot-instructions.md, .cursorrules and Markdown/MDC under .claude/rules,
.cursor/rules, .github/instructions, .agents/skills and .claude/skills.
Exclude .git, .venv, venv, node_modules, __pycache__, .worktrees, test-repos,
vendor and third_party. Follow local Markdown links from seeds transitively.
Symlink targets outside the repository, unreadable files and invalid UTF-8 are
execution errors, never clean results. No network link checks or shell execution.

References use CommonMark inline/reference links and images, not code examples.
@imports are recognized only when the whole prose line is `@relative/file.md`
or uses an explicit `@./path`, `@../path`, `@~/path`, `@/path` prefix. Use `./`
for extensionless paths; bare GitHub organization/team mentions are ignored.
Remote URLs, website-root paths, fragments, query semantics, bare code paths,
dynamic documentation routes, MDX, and semantic contradictions are outside scope.
TEAM009 ignores inline/fenced code to avoid flagging examples. TEAM010 catches
exact copies, not drift between independently authored vendor guidance. Skill
collision checks separate vendor namespaces; package-specific scoping may still
need selective adoption. TEAM001 is an opt-in team convention, not a claim every
open-source repository ought to support agents.

Run tests from the Rýni checkout:

```sh
uv run --with-editable . --with-editable examples/team-harness pytest examples/team-harness/tests
```
