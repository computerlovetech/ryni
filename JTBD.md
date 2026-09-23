# Rýni: Jobs to Be Done

Rýni is a linter for your agent harness.

Harness engineering is hard. Keeping a team aligned on it is harder. Instructions,
skills, and markdown docs can become inconsistent, difficult to navigate, or stale
as a repository changes. Teams need a consistent and coherent working environment
for their agents without relying on someone to manually review every detail.

These jobs describe the outcomes we work toward, rather than prescribing features
or implementation details.

Rýni provides the rules and deterministic checks. An existing agent uses Rýni to
conduct reviews that require judgment; Rýni does not run its own reviewing agent.

## Core jobs

| Job | When… | I want to… | So I can… |
| --- | --- | --- | --- |
| **Keep the harness coherent** | Instructions, skills, and docs accumulate or change | Find structural problems, conflicting guidance, and information that no longer matches the code | Give agents a working environment they can navigate and rely on. |
| **Align the team** | People organize and maintain agent environments differently | Agree on conventions and apply them consistently across repositories | Keep each repository from becoming a separate setup to understand and maintain. |
| **Make our conventions checkable** | My team agrees on how our harness should work | Express explicit requirements as checks and judgment-based expectations as focused reviews | Make our standards practical to verify during everyday work. |
| **Adopt and share practices** | We find useful harness conventions or develop our own | Reuse and share those conventions as documented rule packs | Apply experience across teams without copying guidance or recreating checks. |
| **Catch drift before it lands** | Someone changes the codebase or harness | Check that the harness still follows our conventions | Fix regressions before they mislead an agent or spread to other repositories. |

## Role of tidy-harness

`tidy-harness` is an opinionated example pack: one source of truth, discoverable
docs, and focused instructions. It demonstrates how a team can express its own
standards. Rýni supplies the checking mechanism; packs supply the conventions.

## Success criterion for agent reviews

Agent review instructions must define the scope, evidence, and conditions for a
finding clearly enough that different agents can apply them consistently. Reviews
remain non-deterministic; findings must cite concrete evidence and suggest an
actionable correction, accounting for scope and explicit exceptions.

Deterministic results and agent judgments must remain distinguishable. Missing
evidence or unfinished reviews must be reported as incomplete, not as a pass.
