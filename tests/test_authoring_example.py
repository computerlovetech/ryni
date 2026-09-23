from importlib.resources import files
import runpy

import pytest

from ryni.engine import check
from ryni.profiling import CheckProfile


@pytest.fixture
def pack():
    path = files("ryni").joinpath("skills/ryni-rule-author/assets/example_pack.py")
    return runpy.run_path(str(path))["PACK"]


@pytest.mark.parametrize(
    "content,codes",
    [
        ('[service]\nname="api"\nport=8080\n', []),
        ('[service]\nname=""\nport=0\n', ["SERVICE002", "SERVICE003"]),
        ('[service]\nname=[]\nport=true\n', ["SERVICE002", "SERVICE003"]),
        ("[service", ["SERVICE001"]),
        ('name="api"', ["SERVICE001"]),
    ],
)
def test_example_pack_contract(tmp_path, pack, content, codes):
    path = tmp_path / "service.toml"
    path.write_text(content)
    result = check([tmp_path], pack.rules)
    assert result.errors == []
    assert [finding.rule_id for finding in result.findings] == codes
    assert all(finding.path == str(path) for finding in result.findings)


def test_example_shares_content_analysis_without_losing_target_paths(tmp_path, pack):
    paths = [tmp_path / name / "service.toml" for name in ("one", "two")]
    for path in paths:
        path.parent.mkdir()
        path.write_text('[service]\nname="api"\nport=0\n')
    profile = CheckProfile()
    result = check([tmp_path], pack.rules, profile=profile)
    assert [finding.path for finding in result.findings] == [str(path) for path in paths]
    helpers = {
        row["name"].rsplit(".", 1)[-1]: row
        for row in profile.to_dict()["timings"] if row["kind"] == "helper"
    }
    assert helpers["read_config"]["cache_misses"] == 2
    assert helpers["parse_config"]["cache_misses"] == 1
    assert helpers["parse_config"]["cache_hits"] == 5
    paths[0].write_text('[service]\nname="api"\nport=8080\n')
    assert [f.path for f in check([tmp_path], pack.rules).findings] == [str(paths[1])]


def test_example_keeps_read_errors(tmp_path, pack):
    (tmp_path / "service.toml").mkdir()
    result = check([tmp_path], pack.rules)
    assert result.exit_code == 2
    assert len(result.errors) == 3
