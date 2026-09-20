# Write and share a pack

A good pack turns a small set of opinions into conventions another team can adopt.
Start with a concrete violation you want to catch. Use Python when it can decide;
use a review rule when the decision needs interpretation.

## Create a package

```text
team-rules/
├── pyproject.toml
└── src/
    └── team_rules/
        └── __init__.py
```

In `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.18"]
build-backend = "hatchling.build"

[project]
name = "your-team-rules"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["ryni>=0.1.0"]

[project.entry-points."ryni.rules"]
team = "team_rules:PACK"

[tool.hatch.build.targets.wheel]
packages = ["src/team_rules"]
```

Choose a package name you own and a minimum Rýni version containing the APIs you
use. The current pack/review API is under development in this checkout; it must
be released before a registry install can use it.

## Express a deterministic convention

In `src/team_rules/__init__.py`:

```python
from pathlib import Path

from ryni.models import Finding, ReviewRule, Rule, RulePack, RuleScope


def require_instructions(root: Path) -> list[Finding]:
    path = root / "AGENTS.md"
    if path.is_file() and path.read_text(encoding="utf-8").strip():
        return []
    return [Finding(str(path), 1, "TEAM001", "Add nonempty project instructions in AGENTS.md.")]


INSTRUCTIONS = Rule(
    id="TEAM001",
    name="project-instructions",
    description="Every repository must provide a starting point for agents.",
    filename="",
    scope=RuleScope.REPOSITORY,
    evaluate=require_instructions,
)
```

A file rule instead supplies a basename such as `filename="SKILL.md"` and uses the
default file scope. Put conditions and exceptions directly in your Python logic.
Evaluators return findings without printing or modifying files. Exceptions become
execution errors; unrelated checks continue.

## Express a review convention

In the same module:

```python
TEST_COMMANDS = ReviewRule(
    id="TEAM002",
    name="accurate-test-instructions",
    description="Test instructions must agree with repository tooling.",
    instructions="""
Read the root AGENTS.md and the manifests referenced by its testing instructions.
Report only direct contradictions, such as an npm script that does not exist.
Cite the instruction and the conflicting manifest entry. Do not execute commands.
If no test commands are documented, return not_applicable with that reason.
If the required evidence is unavailable, return incomplete and explain why.
""",
)
```

Review rules default to repository scope. To review individual files, specify
`scope=RuleScope.FILE` and a `filename`. Keep the convention narrow, define what
counts as evidence, and say when it does not apply. Avoid requests such as
"find anything that could be improved."

Long prompts can live in Markdown resources inside your Python package. Read them
with `importlib.resources` so installed wheels work outside the source checkout.

## Export the pack

```python
PACK = RulePack(
    name="team-harness",
    description="Explicit project instructions and accurate testing guidance.",
    rules=(INSTRUCTIONS, TEST_COMMANDS),
)
```

The `ryni.rules` entry point exports this object. Existing plugins exporting a
single `Rule` still work; a single `ReviewRule` is also supported.

## Test the promise

Use passing and failing fixture repositories. For Python checks, assert the
actual findings. For review rules, have an agent apply the instructions to known
examples and check its evidence, false positives, and incomplete cases.

A minimal Python test can call the engine directly:

```python
from ryni.engine import check
from team_rules import PACK


def test_missing_instructions(tmp_path):
    (tmp_path / ".git").mkdir()
    result = check([tmp_path], PACK.rules)
    assert [finding.rule_id for finding in result.findings] == ["TEAM001"]
    assert [task.rule_id for task in result.pending_reviews] == ["TEAM002"]
```

See the [working example pack](https://github.com/computerlovetech/ryni/tree/main/examples/team-pack)
for a complete package. The checkout also includes tests of pack discovery and
mixed deterministic/review execution.

## Publish and let others adopt it

Document the pack's opinions, each rule's passing and failing cases, and an
installation command. Build and publish to your Python package index with uv:

```bash
uv build
uv publish
```

Publishing requires credentials and a package name you control. Rýni does not
publish anything automatically. After publication, another team adopts the pack:

```bash
uv add --dev ryni your-team-rules
```

Adopting teams should commit `pyproject.toml` and `uv.lock` and run checks with
`uv run ryni`. See [adopting packs](adopting-packs.md) for the complete setup.
The pack itself keeps Rýni as a runtime dependency because its rules import the
Rýni API; both packages are development dependencies in a consuming repository.

Release a new pack version when its conventions change. Teams update their
dependencies and lockfile deliberately to adopt it.
