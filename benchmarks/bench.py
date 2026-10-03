"""Fetch a pinned corpus and compare ryni's CLI behavior using only the stdlib."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ryni-benchmark"


def git(directory, *arguments):
    return subprocess.check_output(
        ["git", "-C", str(directory), *arguments], stderr=subprocess.STDOUT,
        text=True, timeout=300, env={**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"},
    ).strip()


def verify(repo, directory):
    if git(directory, "rev-parse", "HEAD") != repo["revision"]:
        raise ValueError(f"{repo['name']}: revision differs; run fetch")
    if git(directory, "status", "--porcelain", "--untracked-files=all", "--ignored"):
        raise ValueError(f"{repo['name']}: checkout has local changes or extra files")


def fetch(repo, cache):
    directory = cache / repo["name"]
    directory.mkdir(parents=True, exist_ok=True)
    if not (directory / ".git").exists():
        if any(directory.iterdir()):
            raise ValueError(f"Refusing to initialize nonempty directory: {directory}")
        git(directory, "init", "--quiet")
        git(directory, "remote", "add", "origin", repo["url"])
    if git(directory, "remote", "get-url", "origin") != repo["url"]:
        raise ValueError(f"{repo['name']}: origin differs from manifest")
    if git(directory, "status", "--porcelain", "--untracked-files=all", "--ignored"):
        raise ValueError(f"{repo['name']}: refusing to change a dirty checkout")
    git(directory, "config", "core.autocrlf", "false")
    git(directory, "fetch", "--quiet", "--depth=1", "origin", repo["revision"])
    git(directory, "-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach", repo["revision"])
    verify(repo, directory)
    print(f"Fetched {repo['name']} ({repo['language']})", flush=True)


def scan(binary, directory, timeout):
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [str(binary), "check", "."], cwd=directory,
            env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
            capture_output=True, timeout=timeout,
        )
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
        status = "ok" if code in (0, 1) else "error"
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr = None, error.stdout or b"", error.stderr or b""
        status = "timeout"
    elapsed = time.perf_counter() - started
    stdout = stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
    stderr = stderr.decode("utf-8", errors="replace").replace("\r\n", "\n")
    stderr = stderr.replace(str(directory), "<repo>")
    rules = dict(sorted(Counter(re.findall(r"^([a-z][a-z0-9-]+): ", stdout, re.M)).items()))
    fingerprint = hashlib.sha256((stdout + "\0" + stderr).encode()).hexdigest()
    return {
        "status": status, "exit_code": code, "rules": rules,
        "findings": sum(rules.values()), "output_sha256": fingerprint,
    }, elapsed, stdout, stderr


def inventory(directory):
    markdown = skills = 0
    for parent, _, files in os.walk(directory, followlinks=False):
        for filename in files:
            path = Path(parent) / filename
            if not path.is_symlink() and path.suffix.lower() in (".md", ".markdown"):
                markdown += 1
                skills += filename == "SKILL.md"
    return {"markdown_files": markdown, "skill_files": skills}


def differences(current, baseline):
    changes = []
    for name in sorted(current.keys() | baseline.keys()):
        if name not in current or name not in baseline:
            changes.append(f"{name}: repository added or removed")
            continue
        for key in ("revision", "status", "exit_code", "output_sha256"):
            if current[name][key] != baseline[name][key]:
                changes.append(f"{name}: {key} changed")
    return changes


def positive_integer(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch", "run"))
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--repo", action="append", help="select a name; repeat for multiple repos")
    parser.add_argument("--binary", type=Path,
                        default=ROOT.parent / "target/release" / ("ryni.exe" if os.name == "nt" else "ryni"))
    parser.add_argument("--repeat", type=positive_integer, default=3)
    parser.add_argument("--timeout", type=positive_integer, default=60, help="seconds per scan")
    parser.add_argument("--output", type=Path, default=ROOT / "results/latest.json")
    parser.add_argument("--baseline", type=Path, help="fail on changed behavior; timing is informational")
    args = parser.parse_args()
    repos = json.loads((ROOT / "repos.json").read_text())
    if args.repo:
        unknown = set(args.repo) - {repo["name"] for repo in repos}
        if unknown:
            parser.error(f"unknown repositories: {', '.join(sorted(unknown))}")
        repos = [repo for repo in repos if repo["name"] in args.repo]
    cache = args.cache.resolve()
    if cache.is_relative_to(ROOT.parent):
        parser.error("keep the corpus outside ryni: its scanner does not honor .gitignore")
    if args.command == "fetch":
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda repo: fetch(repo, cache), repos))
        return 0

    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("binary missing; run cargo build --release --locked")
    baseline = json.loads(args.baseline.read_text())["repos"] if args.baseline else None
    if baseline is not None and args.repo:
        baseline = {name: value for name, value in baseline.items() if name in args.repo}
    if args.baseline and args.output.resolve() == args.baseline.resolve():
        parser.error("output must not overwrite the baseline")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logs = args.output.parent / args.output.stem
    logs.mkdir(exist_ok=True)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "repeat": args.repeat, "repos": {},
    }
    failed = False
    for repo in repos:
        directory = cache / repo["name"]
        try:
            verify(repo, directory)
            times = []
            first = None
            for iteration in range(args.repeat):
                result, elapsed, stdout, stderr = scan(binary, directory, args.timeout)
                times.append(elapsed)
                (logs / f"{repo['name']}.{iteration + 1}.stdout.txt").write_text(stdout, encoding="utf-8")
                (logs / f"{repo['name']}.{iteration + 1}.stderr.txt").write_text(stderr, encoding="utf-8")
                if first is None:
                    first = result
                elif first != result:
                    first = {**result, "status": "unstable"}
                    break
                if result["status"] != "ok":
                    break
            result = {**first, "seconds": times, "median_seconds": statistics.median(times)}
            result.update(inventory(directory))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            result = {"status": "error", "exit_code": None, "output_sha256": None, "error": str(error)}
        result["revision"] = repo["revision"]
        report["repos"][repo["name"]] = result
        failed |= result["status"] != "ok"
        print(f"{repo['name']:16} {result['status']:8} "
              f"{result.get('findings', '-'):>5} findings  "
              f"{result.get('median_seconds', 0):.3f}s", flush=True)
        if "error" in result:
            print(f"  {result['error']}", flush=True)
    changes = differences(report["repos"], baseline) if baseline is not None else []
    report["changes"] = changes
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for change in changes:
        print(change)
    print(f"Report: {args.output}")
    return int(failed or bool(changes))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"benchmark: {error}", file=sys.stderr)
        sys.exit(1)
