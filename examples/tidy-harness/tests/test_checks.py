import subprocess

import pytest

from tidy_harness import PACK
from tidy_harness.checks import (
    brief_instructions,
    canonical_instructions,
    documentation_indexes,
    reachable_documentation,
    untracked_installations,
    valid_links,
)


def write(root, name, content=""):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.mark.parametrize("count, expected", [(0, 0), (250, 0), (251, 1)])
def test_line_limit(tmp_path, count, expected):
    write(tmp_path, "app/AGENTS.md", "line\n" * count)
    findings = brief_instructions(tmp_path)
    assert len(findings) == expected
    if findings:
        assert findings[0].path == "app/AGENTS.md"
        assert findings[0].line == 251


def test_instruction_links(tmp_path):
    write(tmp_path, "AGENTS.md")
    assert canonical_instructions(tmp_path) == []
    link = write(tmp_path, "CLAUDE.md", "copy")
    assert len(canonical_instructions(tmp_path)) == 1
    link.unlink()
    link.symlink_to("AGENTS.md")
    assert canonical_instructions(tmp_path) == []
    (tmp_path / "AGENTS.md").unlink()
    assert len(canonical_instructions(tmp_path)) == 1


def test_link_to_wrong_instructions(tmp_path):
    write(tmp_path, "AGENTS.md")
    write(tmp_path, "app/AGENTS.md")
    (tmp_path / "app/CLAUDE.md").symlink_to("../AGENTS.md")
    assert canonical_instructions(tmp_path)[0].path == "app/CLAUDE.md"


def test_docs_indexes_and_scoping(tmp_path):
    write(tmp_path, "docs/a.md")
    write(tmp_path, "app/docs/guide/a.md")
    write(tmp_path, "website/page.md")
    write(tmp_path, "tests/fixtures/docs/a.md")
    assert {f.path for f in documentation_indexes(tmp_path)} == {
        "docs/README.md",
        "app/docs/README.md",
        "app/docs/guide/README.md",
    }
    for path in ("docs/README.md", "app/docs/README.md", "app/docs/guide/README.md"):
        write(tmp_path, path)
    assert documentation_indexes(tmp_path) == []


def test_links_and_fragments(tmp_path):
    write(
        tmp_path,
        "AGENTS.md",
        """# Start
[guide](docs/guide.md#hello-world)
[duplicate](docs/guide.md#hello-world-1)
[setext](docs/guide.md#setext)
[explicit](docs/guide.md#custom)
[html](docs/guide.md#legacy)
[space](<docs/with space.md>)
[encoded](docs/with%20space.md)
[self](#start)
[reference][guide]

[guide]: docs/guide.md "Title"

`[not a link](missing.md)`

```md
[also not a link](missing.md)
```
[web](https://example.invalid/a#missing)
[email](mailto:a@example.invalid)
[route](/web/route)
[outside](../external.md)
""",
    )
    write(
        tmp_path,
        "docs/guide.md",
        '# Hello *world*\n# Hello world\nSetext\n---\n# Named {#custom}\n<a id="legacy"></a>\n',
    )
    write(tmp_path, "docs/with space.md")
    assert valid_links(tmp_path) == []
    write(tmp_path, "docs/broken.md", "[missing](gone.md)\n\n[heading](guide.md#gone)\n")
    findings = valid_links(tmp_path)
    assert [(f.path, f.line) for f in findings] == [("docs/broken.md", 1), ("docs/broken.md", 3)]


def test_source_skills_are_checked_but_installed_copies_are_not(tmp_path):
    write(tmp_path, "skills/foo/SKILL.md", "[missing](missing.md)")
    write(tmp_path, ".agents/skills/foo/SKILL.md", "[missing](missing.md)")
    assert [f.path for f in valid_links(tmp_path)] == ["skills/foo/SKILL.md"]


def test_images_checked(tmp_path):
    write(tmp_path, "docs/a.md", "![diagram](missing.png)")
    assert len(valid_links(tmp_path)) == 1


def test_reachability_and_cycles(tmp_path):
    write(tmp_path, "AGENTS.md", "[docs](docs/)")
    write(tmp_path, "docs/README.md", "[chapter](chapter.md)")
    write(tmp_path, "docs/chapter.md", "[back](README.md)\n[app](../app/AGENTS.md)")
    write(tmp_path, "app/AGENTS.md", "[local](docs/local.md)")
    write(tmp_path, "app/docs/local.md")
    write(tmp_path, "docs/orphan.md")
    assert [f.path for f in reachable_documentation(tmp_path)] == ["docs/orphan.md"]
    (tmp_path / "docs/orphan.md").unlink()
    assert reachable_documentation(tmp_path) == []


def test_reachability_needs_entry_only_when_docs_exist(tmp_path):
    assert reachable_documentation(tmp_path) == []
    write(tmp_path, "docs/a.md")
    assert reachable_documentation(tmp_path)[0].path == "AGENTS.md"


def test_ignored_and_generated_content(tmp_path):
    git(tmp_path, "init")
    write(tmp_path, ".gitignore", "private/\n")
    for prefix in ("private", "node_modules", "tests/fixtures", "testdata", "generated", "dist"):
        write(tmp_path, f"{prefix}/docs/a.md", "[bad](missing.md)")
        write(tmp_path, f"{prefix}/AGENTS.md", "line\n" * 251)
    assert brief_instructions(tmp_path) == []
    assert valid_links(tmp_path) == []
    assert documentation_indexes(tmp_path) == []
    assert reachable_documentation(tmp_path) == []


def test_symlinked_directories_are_not_followed(tmp_path):
    outside = tmp_path / "generated"
    write(outside, "docs/a.md", "[bad](missing.md)")
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    assert valid_links(tmp_path) == []


def test_external_symlink_is_not_read(tmp_path):
    # No outside content needs to exist: resolution is checked before reading.
    (tmp_path / "AGENTS.md").symlink_to(tmp_path.parent / "external-instructions.md")
    with pytest.raises(ValueError, match="outside the repository"):
        brief_instructions(tmp_path)


def test_installed_skills_require_ignore_and_no_tracking(tmp_path):
    git(tmp_path, "init")
    target = ".agents/skills/foo/SKILL.md"
    write(tmp_path, target)
    assert len(untracked_installations(tmp_path)) == 1
    write(tmp_path, ".gitignore", ".agents/skills/\n")
    assert untracked_installations(tmp_path) == []
    git(tmp_path, "add", "-f", target)
    findings = untracked_installations(tmp_path)
    assert len(findings) == 1
    assert findings[0].path == target
    assert "Untrack" in findings[0].message


def test_nested_installs_and_non_git(tmp_path):
    write(tmp_path, "app/.claude/skills/foo/SKILL.md")
    assert untracked_installations(tmp_path) == []
    git(tmp_path, "init")
    assert untracked_installations(tmp_path)[0].path == "app/.claude/skills"
    write(tmp_path, ".gitignore", ".claude/\n")
    assert untracked_installations(tmp_path) == []


def test_pack_engine_integration(tmp_path):
    from ryni.engine import check
    from ryni.models import ReviewRule, Rule

    assert len([r for r in PACK.rules if isinstance(r, Rule)]) == 6
    assert len([r for r in PACK.rules if isinstance(r, ReviewRule)]) == 7
    assert {r.id for r in PACK.rules} == {f"TIDY{i:03}" for i in range(1, 14)}
    write(tmp_path, "AGENTS.md", "line\n" * 251)
    result = check([tmp_path], PACK.rules)
    assert not result.errors
    assert [f.rule_id for f in result.findings] == ["TIDY001"]
    assert len(result.pending_reviews) == 7
    assert result.exit_code == 1


def test_asset_directories_do_not_need_indexes(tmp_path):
    write(tmp_path, "docs/README.md")
    write(tmp_path, "docs/images/diagram.svg")
    assert documentation_indexes(tmp_path) == []


def test_directory_named_claude_is_invalid(tmp_path):
    (tmp_path / "CLAUDE.md").mkdir()
    assert len(canonical_instructions(tmp_path)) == 1


def test_ignore_exceptions_do_not_hide_installed_files(tmp_path):
    git(tmp_path, "init")
    write(tmp_path, ".agents/skills/foo/SKILL.md")
    write(tmp_path, ".gitignore", ".agents/skills/*\n!.agents/skills/foo/\n")
    assert len(untracked_installations(tmp_path)) == 1


def test_images_do_not_establish_document_reachability(tmp_path):
    write(tmp_path, "AGENTS.md", "![not navigation](docs/README.md)")
    write(tmp_path, "docs/README.md")
    assert reachable_documentation(tmp_path)[0].path == "docs/README.md"


def test_explicit_link_to_external_symlink_is_not_followed(tmp_path):
    write(tmp_path, "AGENTS.md", "[outside](outside.md)")
    (tmp_path / "outside.md").symlink_to(tmp_path.parent / "absent.md")
    assert valid_links(tmp_path) == []


def test_review_only_run_stays_pending(tmp_path):
    from ryni.engine import check
    from tidy_harness.reviews import RULES

    result = check([tmp_path], RULES)
    assert result.exit_code == 3
    assert not result.findings
    assert len(result.pending_reviews) == 7


def test_git_failure_is_an_error_not_a_clean_run(tmp_path):
    from ryni.engine import check
    from tidy_harness.checks import RULES

    (tmp_path / ".git").mkdir()
    result = check([tmp_path], [RULES[-1]])
    assert result.exit_code == 2
    assert result.errors
