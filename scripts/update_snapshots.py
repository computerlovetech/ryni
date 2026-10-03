"""Regenerate diagnostic snapshots with a built debug binary; review the diff."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
binary = root / "target/debug" / ("ryni.exe" if os.name == "nt" else "ryni")
with tempfile.TemporaryDirectory() as directory:
    (Path(directory) / "README.md").write_bytes(b"# Guide\r\n\r\n\xc3\xa9 [Testing](docs/testing.md)\r\n")
    result = subprocess.run([str(binary), "check", "--isolated", directory], capture_output=True,
                            env={**os.environ, "NO_COLOR": "1"}, check=False)
    if result.returncode != 1 or result.stderr:
        raise RuntimeError(f"snapshot scan failed: {result}")
    destination = root / "tests/snapshots/local-link.txt"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(result.stdout.decode().replace("\r\n", "\n"), encoding="utf-8")
