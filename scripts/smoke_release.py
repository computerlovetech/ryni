"""Run with an isolated installation of Rýni, never the project environment."""

from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def main(expected: str) -> None:
    if version("ryni") != expected:
        raise RuntimeError(f"Expected ryni {expected}, installed {version('ryni')}")
    cli = shutil.which("ryni")
    if cli is None:
        raise RuntimeError("ryni console script was not installed")

    with TemporaryDirectory(prefix="ryni-smoke-") as directory:
        root = Path(directory)

        def run(*args: str) -> str:
            return subprocess.run(
                [cli, *args], cwd=root, text=True, capture_output=True, check=True
            ).stdout

        run("--help")
        rules = json.loads(run("rule", "--output-format", "json"))
        core_rules = [rule for rule in rules if rule["source"]["package"] == "ryni"]
        if not core_rules or any(rule["source"]["version"] != expected for rule in core_rules):
            raise RuntimeError("Installed Rýni rules were not discovered correctly")
        run("skill", "install", str(root / "skills"))
        skill = root / "skills/ryni-check/SKILL.md"
        if not skill.is_file():
            raise RuntimeError("Bundled ryni-check skill was not installed")
        run("check", str(skill), "--select", "SKILL001")
        report = json.loads(run("check", str(skill), "--profile", "--output-format", "json"))
        if not report["profile"]["timings"]:
            raise RuntimeError("Check profiling did not report timings")
        run("skill", "install", str(root / "skills"), "--name", "ryni-rule-author")
        author = root / "skills/ryni-rule-author"
        for name in ("SKILL.md", "references/authoring.md", "assets/example_pack.py"):
            if not (author / name).is_file():
                raise RuntimeError(f"Bundled authoring resource was not installed: {name}")
        run("check", str(author), "--deterministic")
    print(f"Verified ryni {expected}: CLI, baseline rules, profiling, and bundled skills.")


if __name__ == "__main__":
    main(sys.argv[1])
