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
        output = subprocess.CompletedProcess([], 1, b"markdown-local-link: Missing\nFound 1 error.\n", b"")
        with patch("bench.subprocess.run", return_value=output):
            result, _, _, _ = bench.scan(Path("ryni"), Path("repo"), 1)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["rules"], {"markdown-local-link": 1})

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
                    "output_sha256": "old", "median_seconds": 1}
        faster = {**original, "median_seconds": 0.5}
        self.assertEqual(bench.differences({"repo": faster}, {"repo": original}), [])
        changed = {**faster, "output_sha256": "new", "revision": "def"}
        self.assertEqual(bench.differences({"repo": changed}, {"repo": original}),
                         ["repo: revision changed", "repo: output_sha256 changed"])

    def test_comparison_detects_missing_repositories(self):
        self.assertEqual(bench.differences({}, {"repo": {}}),
                         ["repo: repository added or removed"])


if __name__ == "__main__":
    unittest.main()
