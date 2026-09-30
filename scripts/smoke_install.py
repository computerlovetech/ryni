"""Exercise generated release installers against local artifacts, without changing PATH."""
import functools
import http.server
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import tomllib


def main():
    artifacts = Path(sys.argv[1]).resolve()
    version = tomllib.loads(Path("Cargo.toml").read_text())["package"]["version"]
    windows = os.name == "nt"
    installer = artifacts / ("ryni-installer.ps1" if windows else "ryni-installer.sh")
    if not installer.is_file():
        raise RuntimeError(f"Missing installer: {installer}")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(artifacts))
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="ryni-install-") as temporary:
                root = Path(temporary)
                install_dir = root / "bin with spaces"
                env = os.environ.copy()
                env["RYNI_DOWNLOAD_URL"] = f"http://127.0.0.1:{server.server_port}"
                env["RYNI_UNMANAGED_INSTALL"] = str(install_dir)
                env["RYNI_NO_MODIFY_PATH"] = "1"
                command = (["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(installer)]
                           if windows else ["sh", str(installer)])
                binary = install_dir / ("ryni.exe" if windows else "ryni")
                # Installing twice exercises updates and paths containing spaces.
                for _ in range(2):
                    subprocess.run(command, env=env, check=True)
                    result = subprocess.run([str(binary), "--version"], check=True, capture_output=True, text=True)
                    assert result.stdout.strip() == f"ryni {version}", result.stdout
                skill = root / "demo-skill"
                skill.mkdir()
                (skill / "SKILL.md").write_text("---\nname: demo-skill\ndescription: Installer smoke test.\n---\n", encoding="utf-8")
                result = subprocess.run([str(binary), "check", str(skill)], capture_output=True, text=True)
                assert result.returncode == 0, result
                assert "All checks passed!" in result.stdout, result.stdout
                (skill / "README.md").write_text("[Missing](missing.md)\n", encoding="utf-8")
                result = subprocess.run([str(binary), "check", str(skill)], capture_output=True, text=True)
                assert result.returncode == 1, result
                assert "markdown-local-link" in result.stdout, result.stdout
                print(f"Installer smoke test passed for ryni {version}")
        finally:
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    main()
