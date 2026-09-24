"""Alternate historical and current engine/pack combinations on unchanged checkouts."""

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import tempfile
import time
import types
import sys

from ryni.engine import check
from ryni.rules.skill_frontmatter import RULE
from ryni.rules.skill_constraints import NAME_RULE, DIRECTORY_RULE, DESCRIPTION_RULE
from team_harness import PACK


def historical_file(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repos", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline", default="62fa1a6")
    parser.add_argument("--repeat", type=int, default=7)
    args = parser.parse_args()
    old_engine = types.ModuleType("baseline_engine")
    exec(
        compile(historical_file(args.baseline, "src/ryni/engine.py"), "<baseline engine>", "exec"),
        old_engine.__dict__,
    )
    with tempfile.TemporaryDirectory(prefix="ryni-comparison-") as directory:
        package = Path(directory)
        for name in ("__init__.py", "analysis.py"):
            (package / name).write_bytes(
                historical_file(args.baseline, f"examples/team-harness/src/team_harness/{name}")
            )
        spec = importlib.util.spec_from_file_location(
            "baseline_pack", package / "__init__.py", submodule_search_locations=[directory]
        )
        old_pack = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = old_pack
        spec.loader.exec_module(old_pack)
        builtin = (RULE, NAME_RULE, DIRECTORY_RULE, DESCRIPTION_RULE)
        variants = {
            "baseline": (old_engine.check, (*old_pack.PACK.rules, *builtin)),
            "inventory_only": (old_engine.check, (*PACK.rules, *builtin)),
            "final": (check, (*PACK.rules, *builtin)),
        }
        rng = random.Random(42)
        rows = []
        for root in sorted(args.repos.resolve().iterdir()):
            if not (root / ".git").exists():
                continue
            expected = None
            samples = {name: [] for name in variants}
            for iteration in range(args.repeat + 1):
                order = list(variants)
                rng.shuffle(order)
                for name in order:
                    run, rules = variants[name]
                    start = time.perf_counter()
                    result = run([root], rules)
                    elapsed = time.perf_counter() - start
                    digest = hashlib.sha256(
                        json.dumps(asdict(result), sort_keys=True).encode()
                    ).hexdigest()
                    if expected is None:
                        expected = digest
                    assert expected == digest, (root, name)
                    if iteration:
                        samples[name].append(elapsed)
            row = dict(
                repository=root.name,
                digest=expected,
                seconds=samples,
                medians={k: statistics.median(v) for k, v in samples.items()},
            )
            rows.append(row)
            print(root.name, row["medians"], flush=True)
            args.output.write_text(
                json.dumps(
                    dict(
                        baseline=args.baseline,
                        python=sys.version,
                        platform=platform.platform(),
                        repetitions=args.repeat,
                        order="seeded shuffled per round; one warmup round excluded",
                        rows=rows,
                    ),
                    indent=2,
                )
                + "\n"
            )


if __name__ == "__main__":
    main()
