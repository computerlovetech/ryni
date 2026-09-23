"""Run with an isolated installation of both distributions, never the project env."""

from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


def main(expected: str) -> None:
    for package in ("ryni", "tidy-harness"):
        if version(package) != expected:
            raise RuntimeError(f"Expected {package} {expected}, installed {version(package)}")
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
        pack_rules = [rule for rule in rules if rule["source"]["name"] == "tidy-harness"]
        if not pack_rules or any(rule["source"]["version"] != expected for rule in pack_rules):
            raise RuntimeError("Installed tidy-harness rules were not discovered correctly")
        run("skill", "install", str(root / "skills"))
        skill = root / "skills/ryni-check/SKILL.md"
        if not skill.is_file():
            raise RuntimeError("Bundled ryni-check skill was not installed")
        run("check", str(skill), "--select", "SKILL001")
    print(f"Verified ryni and tidy-harness {expected}: CLI, rule pack, and bundled skill.")


if __name__ == "__main__":
    main(sys.argv[1])
