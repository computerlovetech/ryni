"""Repeatable real-checkout benchmark: profiles, unprofiled engine and end-to-end CLI."""

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

from ryni.engine import check
from ryni.profiling import CheckProfile
from ryni.rules.skill_frontmatter import RULE
from ryni.rules.skill_constraints import NAME_RULE, DIRECTORY_RULE, DESCRIPTION_RULE
from team_harness import PACK


def digest(result):
    return hashlib.sha256(json.dumps(asdict(result), sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repos", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()
    rules = (*PACK.rules, RULE, NAME_RULE, DIRECTORY_RULE, DESCRIPTION_RULE)
    rows = []
    for root in sorted(args.repos.resolve().iterdir()):
        if not (root / ".git").exists():
            continue
        profile = CheckProfile()
        result = check([root], rules, profile=profile)
        expected = digest(result)
        engine, cli = [], []
        for _ in range(args.repeat):
            start = time.perf_counter()
            rerun = check([root], rules)
            engine.append(time.perf_counter() - start)
            assert digest(rerun) == expected, root
        for _ in range(args.repeat):
            start = time.perf_counter()
            process = subprocess.run(
                [
                    str(Path(sys.executable).parent / "ryni"),
                    "check",
                    str(root),
                    "--select",
                    ",".join(rule.id for rule in rules),
                    "--deterministic",
                    "--output-format",
                    "json",
                ],
                capture_output=True,
                text=True,
            )
            if not process.stdout:
                raise RuntimeError(f"CLI produced no JSON: {process.stderr}")
            cli.append(time.perf_counter() - start)
            cli_result = json.loads(process.stdout)
            assert process.returncode == result.exit_code
            assert cli_result == asdict(result), root
        row = dict(
            repository=root.name,
            result=asdict(result),
            digest=expected,
            findings_by_rule=dict(Counter(f.rule_id for f in result.findings)),
            profile=profile.to_dict(),
            engine_seconds=engine,
            cli_seconds=cli,
            engine_median=statistics.median(engine),
            cli_median=statistics.median(cli),
        )
        rows.append(row)
        print(
            root.name,
            f"{row['engine_median']:.3f}s engine",
            f"{row['cli_median']:.3f}s CLI",
            len(result.findings),
            "findings",
            len(result.errors),
            "errors",
            flush=True,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                dict(
                    python=sys.version,
                    platform=platform.platform(),
                    repetitions=args.repeat,
                    cache="warm OS cache; fresh per-check cache",
                    rows=rows,
                ),
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
