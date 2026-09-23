from pathlib import Path
import runpy
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/release.py"
release_metadata = runpy.run_path(str(SCRIPT))["release_metadata"]


@pytest.fixture
def release_repo(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.2.0"\n')
    pack = tmp_path / "examples/tidy-harness/pyproject.toml"
    pack.parent.mkdir(parents=True)
    pack.write_text('[project]\nversion = "0.2.0"\ndependencies = ["ryni>=0.2,<0.3"]\n')
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Future change.\n\n"
        "## [0.2.0] - 2026-09-23\n\n### Added\n\n- New rule API.\n\n"
        "## [0.1.1] - 2026-09-20\n\n- Older change.\n"
    )
    return tmp_path


def test_extracts_only_the_tagged_release_notes(release_repo):
    assert release_metadata(release_repo, "v0.2.0") == ("0.2.0", "### Added\n\n- New rule API.")


def test_branch_dry_run_uses_unreleased_notes(release_repo):
    assert release_metadata(release_repo) == ("0.2.0", "### Added\n\n- Future change.")


@pytest.mark.parametrize("tag", ["main", "v0.1.1", "0.2.0", "v0.2.0+local"])
def test_wrong_tag_fails_before_publishing(release_repo, tag):
    with pytest.raises(ValueError, match="Tag must be"):
        release_metadata(release_repo, tag)


def test_packages_must_have_matching_versions(release_repo):
    (release_repo / "pyproject.toml").write_text('[project]\nversion = "0.2.1"\n')
    with pytest.raises(ValueError, match="versions must match"):
        release_metadata(release_repo)


@pytest.mark.parametrize(
    "requirement",
    [
        "ryni>=0.1.1,<0.2",
        "ryni",
        "ryni>=0.2; python_version < '3.14'",
        "ryni @ https://example.com/ryni.whl",
        "unrelated>=1",
    ],
)
def test_pack_must_require_the_released_core(release_repo, requirement):
    pack = release_repo / "examples/tidy-harness/pyproject.toml"
    pack.write_text(f'[project]\nversion = "0.2.0"\ndependencies = ["{requirement}"]\n')
    with pytest.raises(ValueError):
        release_metadata(release_repo)


@pytest.mark.parametrize(
    "section",
    [
        "",
        "## [0.2.0]\n- Missing date.",
        "## [0.2.0] - 2026-02-30\n- Invalid date.",
        "## [0.2.0] - 2026-09-23\n\n### Added\n",
        "## [0.2.0] - 2026-09-23\n- First.\n## [0.2.0] - 2026-09-23\n- Duplicate.",
    ],
)
def test_missing_malformed_or_empty_release_notes_fail(release_repo, section):
    (release_repo / "CHANGELOG.md").write_text(f"# Changelog\n\n{section}\n")
    with pytest.raises(ValueError):
        release_metadata(release_repo, "v0.2.0")


@pytest.mark.parametrize("version", ["0.2.0a1", "0.2.0b2", "0.2.0rc1"])
def test_prerelease_versions_and_compatible_dependencies(release_repo, version):
    (release_repo / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    (release_repo / "examples/tidy-harness/pyproject.toml").write_text(
        f'[project]\nversion = "{version}"\ndependencies = ["ryni>={version},<0.3"]\n'
    )
    (release_repo / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{version}] - 2026-09-23\n\n- Preview.\n"
    )
    assert release_metadata(release_repo, f"v{version}") == (version, "- Preview.")


def test_cli_writes_notes_and_reports_errors_without_a_success_output(release_repo, tmp_path):
    notes = tmp_path / "notes.md"
    command = [
        sys.executable,
        str(SCRIPT),
        "--root",
        str(release_repo),
        "--notes-file",
        str(notes),
        "--tag",
    ]
    result = subprocess.run([*command, "v0.2.0"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "0.2.0"
    assert notes.read_text() == "### Added\n\n- New rule API.\n"

    notes.unlink()
    result = subprocess.run([*command, "v0.1.1"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Release validation failed" in result.stderr
    assert not result.stdout
    assert not notes.exists()
