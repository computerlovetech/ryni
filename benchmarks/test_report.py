import copy
import unittest

import report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.manifest = [{"name": "demo", "language": "Rust", "revision": "abc", "url": "https://example.com/demo.git"}]
        self.run = {"repeat": 3, "repos": {"demo": {
            "status": "ok", "revision": "abc", "markdown_files": 10, "skill_files": 2,
            "findings": 3, "rules": {"markdown-local-link": 2, "skill-name": 1},
            "seconds": [.01, .05, .03],
        }}}

    def test_aggregates_per_scan_counts_and_includes_zero_rules(self):
        rows, totals = report.summarize(self.run, self.manifest)
        self.assertEqual(totals["markdown_files"], 10)
        self.assertEqual(totals["skill_files"], 2)
        self.assertEqual(totals["findings"], 3)
        self.assertEqual(totals["rules"]["skill-description"], 0)
        self.assertEqual(rows[0]["median_ms"], 30)

    def test_refuses_incomplete_or_inconsistent_data(self):
        for replacement in ({"status": "timeout"}, {"revision": "other"},
                            {"findings": 4}, {"seconds": [.01]}, {"skill_files": 11}):
            with self.subTest(replacement=replacement):
                run = copy.deepcopy(self.run)
                run["repos"]["demo"].update(replacement)
                with self.assertRaises(ValueError):
                    report.summarize(run, self.manifest)

    def test_unknown_rules_are_retained(self):
        self.run["repos"]["demo"]["rules"] = {"future-rule": 3}
        _, totals = report.summarize(self.run, self.manifest)
        self.assertEqual(totals["rules"]["future-rule"], 3)


if __name__ == "__main__":
    unittest.main()
