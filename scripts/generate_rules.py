"""Generate rule tables from the built CLI registry, or verify them with --check."""
import argparse
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
binary = root / "target/debug" / ("ryni.exe" if os.name == "nt" else "ryni")
rules = json.loads(subprocess.check_output([str(binary), "rule", "--output-format", "json"]))
start, end = "<!-- rules:start -->", "<!-- rules:end -->"
failed = False
for relative in ("README.md", "website/rules.md"):
    path = root / relative
    text = path.read_text(encoding="utf-8")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    selected = [rule for rule in rules if relative != "README.md" or rule["default_enabled"]]
    lines = ["| Rule | Status | Check |", "| --- | --- | --- |"]
    for rule in selected:
        lines.append(f'| `{rule["id"]}` | {rule["stability"]} | {rule["explanation"]} |')
    generated = before + start + "\n" + "\n".join(lines) + "\n" + end + after
    if args.check:
        if text != generated:
            print(f"Stale rule table: {relative}; run python3 scripts/generate_rules.py")
            failed = True
    else:
        path.write_text(generated, encoding="utf-8")
raise SystemExit(int(failed))
