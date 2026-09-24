"""Alternate pinned historical engine/pack combinations on unchanged checkouts."""

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

from ryni.rules.skill_frontmatter import RULE
from ryni.rules.skill_constraints import NAME_RULE, DIRECTORY_RULE, DESCRIPTION_RULE


def historical_file(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"])


def load_engine(revision, name):
    module = types.ModuleType(name)
    exec(compile(historical_file(revision, "src/ryni/engine.py"), name, "exec"), module.__dict__)
    return module.check


def load_pack(revision, package, module_name):
    package.mkdir()
    for name in ("__init__.py", "analysis.py"):
        (package / name).write_bytes(
            historical_file(revision, f"examples/team-harness/src/team_harness/{name}")
        )
    spec = importlib.util.spec_from_file_location(
        module_name, package / "__init__.py", submodule_search_locations=[str(package)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PACK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repos", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline", default="62fa1a6")
    parser.add_argument("--optimized", default="47afeb6")
    parser.add_argument("--repeat", type=int, default=7)
    args = parser.parse_args()
    old_check = load_engine(args.baseline, "baseline_engine")
    new_check = load_engine(args.optimized, "optimized_engine")
    with tempfile.TemporaryDirectory(prefix="ryni-comparison-") as directory:
        old_pack = load_pack(args.baseline, Path(directory) / "old", "baseline_pack")
        new_pack = load_pack(args.optimized, Path(directory) / "new", "optimized_pack")
        builtin = (RULE, NAME_RULE, DIRECTORY_RULE, DESCRIPTION_RULE)
        variants = {
            "baseline": (old_check, (*old_pack.rules, *builtin)),
            "inventory_only": (old_check, (*new_pack.rules, *builtin)),
            "final": (new_check, (*new_pack.rules, *builtin)),
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
                        optimized=args.optimized,
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
