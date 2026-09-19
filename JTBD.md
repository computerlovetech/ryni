# Rýni: Jobs to Be Done

Rýni helps teams adopt, express, and maintain their harness engineering conventions.
These jobs describe the outcomes we work toward, rather than prescribing features
or implementation details.

Rýni provides the rules and deterministic checks. An existing agent uses Rýni to
conduct reviews that require judgment; Rýni does not run its own reviewing agent.

## Core jobs

| Job | When… | I want to… | So I can… |
| --- | --- | --- | --- |
| **Adopt a trusted standard** | I discover a team's harness practices that I like | Adopt their shared rules with minimal setup | Apply their experience without creating my own standard. |
| **Make our conventions repeatable** | My team agrees on how our harness should work | Express our conventions as executable checks or agent review instructions | Have developers and agents apply the same expectations consistently. |
| **Publish a reusable rule pack** | We have conventions worth sharing | Package and document them as an installable rule pack | Let other teams adopt our approach in one installation without copying rules or recreating our setup. |
| **Catch drift before it lands** | Someone changes the codebase or harness | Check the change against our conventions, using deterministic checks and an existing agent's review | Catch meaningful regressions before merging. |

## Success criterion for agent reviews

Agent review instructions must be clear enough that different agents can apply
them and return comparable, traceable findings. Deterministic results and agent
judgments should remain distinguishable.
