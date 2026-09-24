"""Create shallow, full-working-tree benchmark checkouts; never run their code."""

import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys

REPOSITORIES = (
    "microsoft/vscode",
    "vercel/next.js",
    "facebook/react",
    "pytorch/pytorch",
    "kubernetes/kubernetes",
    "rust-lang/rust",
    "golang/go",
    "django/django",
    "fastapi/fastapi",
    "nodejs/node",
    "grafana/grafana",
    "microsoft/TypeScript",
)


def clone(repo, destination):
    path = destination / repo.replace("/", "--")
    if not path.exists():
        subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", f"https://github.com/{repo}.git", str(path)],
            check=True,
        )
    sha = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    count = (
        len(subprocess.check_output(["git", "-C", str(path), "ls-files", "-z"]).split(b"\0")) - 1
    )
    record = dict(
        repository=repo,
        url=f"https://github.com/{repo}",
        commit=sha,
        tracked_files=count,
        directory=path.name,
    )
    print(json.dumps(record), flush=True)
    return record


if __name__ == "__main__":
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda repo: clone(repo, destination), REPOSITORIES))
    Path(sys.argv[2]).write_text(json.dumps(records, indent=2) + "\n")
