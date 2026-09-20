# Share conventions. Catch harness drift.

Rýni helps teams turn their harness conventions into repeatable checks. Adopt a
pack you trust, express your own rules in Python, and catch deviations before they
land.

**Python checks run in the CLI. Judgment-based reviews run in your existing agent.**
Both belong in the same shareable rule pack. No Rýni configuration file or
activation step is required.

```bash
uv add --dev ryni
uv run ryni check .
```

For a shared repository, add Rýni and your team's pack as development dependencies
and commit `pyproject.toml` and `uv.lock`. See [adopting packs](adopting-packs.md).

Rýni ships with one baseline check: valid skill frontmatter. Install a pack to
adopt a team's broader conventions.

## Start with the job

| I want to… | Start here |
| --- | --- |
| Try Rýni on a repository | [Getting started](getting-started.md) |
| Adopt another team's conventions | [Adopt a pack](adopting-packs.md) |
| Express and publish our conventions | [Write and share a pack](writing-packs.md) |
| Run the complete policy with an agent | [Check with your agent](agent-checks.md) |
| Catch drift on every change | [Continuous integration](ci.md) |

## One policy, two kinds of check

A **deterministic rule** uses Python to return a finding: a skill lacks metadata,
an instruction file is missing, or a required path is misplaced.

A **review rule** gives an agent a specific convention to investigate: instructions
contradict one another, or a documented test command disagrees with the build
configuration. The `ryni-check` skill runs the CLI and delegates each pending
review to a sub-agent, then combines the evidence into a concise report.

Rýni does not run a model, require an API key, or assign a codebase readiness score.
Your agent supplies the judgment; your installed packs supply the conventions.

!!! note "Early development"
    The Python API and JSON report format may change. Commit the lockfile and use its resolved versions
    in CI. This repository contains an executable example pack;
    it does not yet provide a public pack catalog.
