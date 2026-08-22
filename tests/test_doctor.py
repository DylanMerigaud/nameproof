"""Tests for the calibration harness itself.

Only the offline parts. `doctor` talks to the network by design, and its real proof is not a
unit test: it is that re-introducing each bug the repo actually shipped makes it fail. That
proof lives in the README rather than here, because it needs the network and a scratch copy of
the tree.

What IS worth guarding offline is the harness's own plumbing, because a calibration file that
silently loads zero cases would report a clean bill of health for a tool that was never checked.
That is the same class of failure the harness exists to catch, which makes it the one thing here
that must not be allowed to fail quietly.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof import doctor  # noqa: E402


class TestCases(unittest.TestCase):
    def test_the_shipped_file_loads_and_is_not_empty(self):
        """A calibration suite that loads nothing passes perfectly and proves nothing."""
        cases = doctor.load_cases()
        self.assertGreaterEqual(len(cases), 10)

    def test_every_case_says_what_it_guards(self):
        """`why` is not documentation, it is the case's reason to exist. A case nobody can
        explain gets deleted the first time it is inconvenient, which is exactly when it
        matters."""
        for c in doctor.load_cases():
            self.assertTrue(c.get("why", "").strip(),
                            "case {} has no why".format(c.get("name")))
            self.assertGreater(len(c["why"]), 40, "case {} explains too little".format(c["name"]))

    def test_both_directions_are_represented(self):
        """A suite of only-flag cases passes with a check that flags everything, and a suite of
        only-clean cases passes with a check that flags nothing. Both directions or neither."""
        expects = {c["expect"] for c in doctor.load_cases()}
        self.assertIn("flag", expects)
        self.assertIn("clean", expects)

    def test_domain_controls_are_positive_and_negative(self):
        """The registry path needs a name known taken AND one known free. With only one, a
        client that answers the same thing to everything still passes."""
        dom = [c for c in doctor.load_cases() if c["check"] == "domain"]
        self.assertIn("taken", {c["expect"] for c in dom})
        self.assertIn("free", {c["expect"] for c in dom})

    def test_comment_lines_are_skipped(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(json.dumps({"_comment": "header"}) + "\n")
            fh.write("\n")
            fh.write(json.dumps({"name": "x", "check": "dictionary",
                                 "expect": "clean", "why": "y" * 50}) + "\n")
            tmp = fh.name
        try:
            self.assertEqual(len(doctor.load_cases(tmp)), 1)
        finally:
            os.unlink(tmp)


class TestRunCase(unittest.TestCase):
    def test_an_unknown_check_kind_is_skipped_not_passed(self):
        """Silence has to read as 'could not run', never as agreement."""
        ok, observed, _ = doctor.run_case(
            {"name": "x", "check": "nonsense", "expect": "clean", "why": "z" * 50})
        self.assertIsNone(ok)
        self.assertEqual(observed, "unknown")

    def test_offline_dictionary_case_runs(self):
        ok, observed, _ = doctor.run_case(
            {"name": "anchor", "check": "dictionary", "expect": "flag", "why": "z" * 50})
        self.assertTrue(ok)
        self.assertEqual(observed, "flag")


if __name__ == "__main__":
    unittest.main()
