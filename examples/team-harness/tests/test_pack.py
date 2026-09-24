from dataclasses import replace
from pathlib import Path
import subprocess

import pytest
from ryni.engine import check
from ryni.models import Rule, ReviewRule
from team_harness import PACK
from team_harness import analysis


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def run(root, code=None):
    return check([root], [r for r in PACK.rules if code is None or r.id == code])


def skill(name="demo", description="Use when demonstrating a task.", body="Run the checks."):
    return f"---\nname: {name}\ndescription: {description}\n---\n{body}\n"


def test_clean_pack_and_no_reviews(tmp_path):
    put(tmp_path, "AGENTS.md", "# Project\nRun `pytest`. See [guide](guide.md).\n")
    put(tmp_path, "guide.md", "# Guide\nUse the existing build tools.\n")
    put(tmp_path, ".agents/skills/demo/SKILL.md", skill())
    result = run(tmp_path)
    assert result.exit_code == 0
    assert result.pending_reviews == []
    assert all(not isinstance(r, ReviewRule) for r in PACK.rules)


@pytest.mark.parametrize(
    ("code", "files"),
    [
        ("TEAM001", {}),
        ("TEAM002", {"CLAUDE.md": ""}),
        ("TEAM003", {"AGENTS.md": "x\n" * 251}),
        ("TEAM004", {"SKILL.md": "x\n" * 501}),
        ("TEAM005", {"AGENTS.md": "<<<<<<< main\n"}),
        ("TEAM006", {"AGENTS.md": "[missing](missing.md)"}),
        ("TEAM007", {"CLAUDE.md": "@missing.md"}),
        ("TEAM008", {"AGENTS.md": "@other.md", "other.md": "@AGENTS.md"}),
        ("TEAM009", {"AGENTS.md": "Use /Users/alice/project/ to build."}),
        ("TEAM010", {"AGENTS.md": "long " * 50, "CLAUDE.md": "long " * 50}),
        ("TEAM011", {"AGENTS.md": "Inherited " * 25, "sub/AGENTS.md": "Inherited " * 25}),
        ("TEAM012", {".agents/skills/demo/SKILL.md": "No frontmatter"}),
        ("TEAM013", {".agents/skills/demo/SKILL.md": skill(name="wrong")}),
        ("TEAM014", {".agents/skills/demo/SKILL.md": skill(description="x" * 1025)}),
        (
            "TEAM015",
            {".agents/skills/a/demo/SKILL.md": skill(), ".agents/skills/b/demo/SKILL.md": skill()},
        ),
        ("TEAM016", {"AGENTS.md": "TODO: add testing instructions"}),
        ("TEAM017", {".agents/skills/demo/SKILL.md": skill(body="")}),
        ("TEAM018", {"AGENTS.md": "@~/private.md"}),
    ],
)
def test_each_rule_has_a_witness(tmp_path, code, files):
    for name, text in files.items():
        put(tmp_path, name, text)
    result = run(tmp_path, code)
    assert not result.errors
    assert result.findings and all(f.rule_id == code for f in result.findings)


def test_commonmark_references_and_examples(tmp_path):
    put(
        tmp_path,
        "AGENTS.md",
        """# Guide
[reference][dest]

[dest]: a%20b.md

```
[example](missing.md)
@not-an-import.md
```
`[inline](missing.md)`
[remote](https://example.com/missing)
[route](/route)
[anchor](#guide)
""",
    )
    put(tmp_path, "a b.md", "Use this guide.")
    assert run(tmp_path, "TEAM006").exit_code == 0
    assert run(tmp_path, "TEAM007").exit_code == 0
    (tmp_path / "a b.md").unlink()
    assert len(run(tmp_path, "TEAM006").findings) == 1


def test_links_followed_and_cycle_terminates(tmp_path):
    put(tmp_path, "AGENTS.md", "[guide](docs/a.md)")
    put(tmp_path, "docs/a.md", "[root](../AGENTS.md)\n[broken](missing.md)")
    result = run(tmp_path, "TEAM006")
    assert len(result.findings) == 1
    assert result.findings[0].path.endswith("docs/a.md")


def test_symlinks_and_freshness(tmp_path):
    put(tmp_path, "AGENTS.md", "# Guide\n")
    (tmp_path / "CLAUDE.md").symlink_to("AGENTS.md")
    assert run(tmp_path, "TEAM010").exit_code == 0
    (tmp_path / "AGENTS.md").write_text("[bad](gone.md)")
    assert run(tmp_path, "TEAM006").exit_code == 1
    (tmp_path / "CLAUDE.md").unlink()
    (tmp_path / "CLAUDE.md").symlink_to("gone.md")
    assert run(tmp_path, "TEAM002").exit_code == 2


def test_external_symlink_is_error(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = put(tmp_path, "outside.md", "do not read")
    (root / "AGENTS.md").symlink_to(outside)
    assert run(root, "TEAM002").exit_code == 2


def test_cache_shared_across_rules_but_not_runs(tmp_path, monkeypatch):
    put(tmp_path, "AGENTS.md", "# Project\n")
    original = Path.read_text
    calls = []

    def read(self, *args, **kwargs):
        calls.append(self)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    rules = [r for r in PACK.rules if r.id in {"TEAM002", "TEAM003", "TEAM005", "TEAM006"}]
    check([tmp_path], rules)
    assert calls == [tmp_path / "AGENTS.md"]
    check([tmp_path], rules)
    assert len(calls) == 2


def test_fix_invalidates_shared_graph(tmp_path):
    path = put(tmp_path, "AGENTS.md", "[bad](gone.md)")
    rule = next(r for r in PACK.rules if r.id == "TEAM006")
    fixer = replace(rule, fix=lambda root: path.write_text("# Fixed\n"))
    assert check([tmp_path], [fixer], fix=True).exit_code == 0


def test_git_includes_tracked_ignored_but_not_untracked_ignored(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    put(tmp_path, "AGENTS.md", "# Project")
    put(tmp_path, ".gitignore", "ignored/\ntracked/\n")
    put(tmp_path, "ignored/AGENTS.md", "not scanned")
    tracked = put(tmp_path, "tracked/AGENTS.md", "scanned")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", str(tracked)], check=True)
    assert set(analysis.inventory(tmp_path)) == {tmp_path / "AGENTS.md", tracked}


def test_budgets_include_bytes_and_boundaries(tmp_path):
    p = put(tmp_path, "AGENTS.md", "x\n" * 250)
    assert not run(tmp_path, "TEAM003").findings
    p.write_text("é" * 8193)
    assert run(tmp_path, "TEAM003").findings


def test_vendor_skill_namespaces_are_separate(tmp_path):
    for vendor in (".agents", ".claude"):
        put(tmp_path, f"{vendor}/skills/demo/SKILL.md", skill())
    assert not run(tmp_path, "TEAM015").findings


def test_rule_failure_preserves_other_findings(tmp_path):
    put(tmp_path, "AGENTS.md", "\udcff".encode("utf-8", errors="backslashreplace").decode())
    (tmp_path / "AGENTS.md").write_bytes(b"\xff")
    extra = Rule("PASS", "pass", "pass", "", lambda p: [], PACK.rules[0].scope)
    result = check([tmp_path], [PACK.rules[1], extra])
    assert result.exit_code == 2
    assert "TEAM002" in result.errors[0]


def test_inventory_prefilter_keeps_extensionless_and_unicode_paths(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    expected = {
        put(tmp_path, ".cursorrules", "rules"),
        put(tmp_path, "é space/AGENTS.md", "rules"),
        put(tmp_path, ".cursor/rules/demo.mdc", "rules"),
    }
    put(tmp_path, "ordinary.py", "pass")
    put(tmp_path, "docs/ordinary.md", "not a seed")
    assert set(analysis.inventory(tmp_path)) == expected


def test_conflict_demonstrations_are_not_conflicts(tmp_path):
    put(
        tmp_path,
        "AGENTS.md",
        "# Resolve conflicts\n```console\n"
        "<<<<<<< HEAD\nexample\n=======\nother example\n>>>>>>> commit\n"
        "```\n\n<<<<<<< actual-branch\n",
    )
    findings = run(tmp_path, "TEAM005").findings
    assert len(findings) == 1
    assert findings[0].line == 10


def test_github_mentions_are_not_imports(tmp_path):
    put(tmp_path, "AGENTS.md", "@nodejs/tsc.\n\n@nodejs/tsc\n\n@./missing\n")
    findings = run(tmp_path, "TEAM007").findings
    assert len(findings) == 1
    assert "missing" in findings[0].message
