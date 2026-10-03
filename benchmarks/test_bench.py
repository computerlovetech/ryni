import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bench


class BenchmarkTests(unittest.TestCase):
    def test_inventory_includes_hidden_skills_and_case_insensitive_markdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            skill = directory / ".agents/skills/demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("skill")
            (directory / "README.MARKDOWN").write_text("readme")
            (directory / "source.rs").write_text("source")
            self.assertEqual(bench.inventory(directory), {"markdown_files": 2, "skill_files": 1})

    def test_lint_findings_are_successful_scans(self):
        payload = {"schema_version": 1, "complete": True, "files_checked": 1, "errors": [],
                   "diagnostics": [{"rule": "markdown-local-link", "path": "README.md", "message": "Missing", "severity": "error", "range": None}]}
        output = subprocess.CompletedProcess([], 1, json.dumps(payload).encode(), b"")
        with patch("bench.subprocess.run", return_value=output):
            result, _, _, _ = bench.scan(Path("ryni"), Path("repo"), 1)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["rules"], {"markdown-local-link": 1})

    def test_json_whitespace_is_not_a_behavior_change(self):
        payload = {"schema_version": 1, "complete": True, "files_checked": 0, "errors": [], "diagnostics": []}
        results = []
        for indent in (None, 2):
            output = subprocess.CompletedProcess([], 0, json.dumps(payload, indent=indent).encode(), b"")
            with patch("bench.subprocess.run", return_value=output):
                results.append(bench.scan(Path("ryni"), Path("repo"), 1)[0])
        self.assertEqual(results[0], results[1])

    def test_malformed_or_incomplete_reports_fail(self):
        for payload in (b"not json", b"{}", b'{"schema_version":1,"complete":false}'):
            with patch("bench.subprocess.run", return_value=subprocess.CompletedProcess([], 0, payload, b"")):
                self.assertEqual(bench.scan(Path("ryni"), Path("repo"), 1)[0]["status"], "error")

    def test_execution_errors_and_crashes_fail(self):
        for code in (2, -11):
            with self.subTest(code=code):
                output = subprocess.CompletedProcess([], code, b"", b"failed")
                with patch("bench.subprocess.run", return_value=output):
                    result, _, _, _ = bench.scan(Path("ryni"), Path("repo"), 1)
                self.assertEqual(result["status"], "error")

    def test_timeout_keeps_partial_output(self):
        error = subprocess.TimeoutExpired([], 1, output=b"partial", stderr=b"details")
        with patch("bench.subprocess.run", side_effect=error):
            result, _, stdout, stderr = bench.scan(Path("ryni"), Path("repo"), 1)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual((stdout, stderr), ("partial", "details"))

    def test_comparison_ignores_timing_but_detects_behavior_and_revision(self):
        original = {"revision": "abc", "status": "ok", "exit_code": 1,
                    "diagnostics_sha256": "old", "median_seconds": 1}
        faster = {**original, "median_seconds": 0.5}
        self.assertEqual(bench.differences({"repo": faster}, {"repo": original}), [])
        changed = {**faster, "diagnostics_sha256": "new", "revision": "def"}
        self.assertEqual(bench.differences({"repo": changed}, {"repo": original}),
                         ["repo: revision changed", "repo: diagnostics_sha256 changed"])

    def test_comparison_detects_missing_repositories(self):
        self.assertEqual(bench.differences({}, {"repo": {}}),
                         ["repo: repository added or removed"])


if __name__ == "__main__":
    unittest.main()
