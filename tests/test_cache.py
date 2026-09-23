import pytest

from ryni.cache import cached_per_check
from ryni.engine import check
from ryni.models import Finding, Rule


def test_cache_is_scoped_to_each_check_and_direct_calls_stay_fresh(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("first")
    reads = []

    @cached_per_check
    def read(path):
        reads.append(path)
        return path.read_text()

    def evaluate(path):
        assert read(path) == read(path)
        return [Finding(str(path), 1, "TEST", read(path))]

    rule = Rule("TEST", "test", "Test", path.name, evaluate)
    assert check([path], [rule]).findings[0].message == "first"
    assert reads == [path]
    path.write_text("second")
    assert check([path], [rule]).findings[0].message == "second"
    assert reads == [path, path]
    assert read(path) == "second"
    path.write_text("third")
    assert read(path) == "third"


@pytest.mark.parametrize("fail_fix", [False, True])
def test_fixes_invalidate_reads_before_later_rules_and_recheck(tmp_path, fail_fix):
    path = tmp_path / "file.txt"
    other = tmp_path / "other.txt"
    path.touch()
    other.write_text("old")

    @cached_per_check
    def read(path):
        return path.read_text()

    def evaluate(path):
        return [Finding(str(path), 1, "FIX", "Repair")] if read(other) == "old" else []

    def fix(path):
        other.write_text("new")
        if fail_fix:
            raise OSError("Partial fix")

    observed = []

    def observe(path):
        observed.append(read(other))
        return []

    result = check(
        [path],
        [
            Rule("FIX", "fix", "Fix", path.name, evaluate, fix=fix),
            Rule("OBSERVE", "observe", "Observe", path.name, observe),
        ],
        fix=True,
    )
    assert observed == ["new", "new"]
    assert result.findings == []
    assert result.exit_code == (2 if fail_fix else 0)


def test_nested_fix_invalidates_parent_cache(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("old")

    @cached_per_check
    def read(path):
        return path.read_text()

    inner = Rule(
        "INNER",
        "inner",
        "Inner",
        path.name,
        lambda path: [Finding(str(path), 1, "INNER", "Repair")] if read(path) == "old" else [],
        fix=lambda path: path.write_text("new"),
    )

    def evaluate(path):
        assert read(path) == "old"
        assert check([path], [inner], fix=True).exit_code == 0
        assert read(path) == "new"
        return []

    assert check([path], [Rule("OUTER", "outer", "Outer", path.name, evaluate)]).exit_code == 0


def test_cache_is_released_after_interruption(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("old")

    @cached_per_check
    def read(path):
        return path.read_text()

    def evaluate(path):
        read(path)
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        check([path], [Rule("TEST", "test", "Test", path.name, evaluate)])
    path.write_text("new")
    assert read(path) == "new"


def test_cached_callable_without_function_metadata(tmp_path):
    from functools import partial

    from ryni.profiling import CheckProfile

    path = tmp_path / "config.ini"
    path.write_text("value")
    read = cached_per_check(partial(path.read_text, encoding="utf-8"))

    def evaluate(path):
        assert read() == read() == "value"
        return []

    profile = CheckProfile()
    result = check([path], [Rule("TEST", "test", "Test", path.name, evaluate)], profile=profile)
    assert result.exit_code == 0
    helper = next(row for row in profile.to_dict()["timings"] if row["kind"] == "helper")
    assert helper["cache_hits"] == helper["cache_misses"] == 1
