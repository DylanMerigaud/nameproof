"""Tests for the search-hijack check.

Only the OFFLINE half runs here. `hijack` talks to Google's suggest endpoint, and a test that
needs the network is a test that fails on a plane and gets deleted a month later. What is covered
instead is the part that must never regress: a lookup that cannot complete returns weight 0 and
says so, rather than an empty list that would read as a clean pass.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof.phonetics import grade  # noqa: E402
from nameproof.search import SUGGEST, near_miss  # noqa: E402

WORDS = {"web", "wet", "weed", "palette", "wed", "name", "scope", "fire", "base",
         "code", "ship", "mind", "set", "sun", "rise"}


class TestNearMiss(unittest.TestCase):
    def test_the_wedpalette_case(self):
        """The case the whole module exists for.

        `wedpalette` is one substitution from `webpalette`, which splits into two ordinary
        words. Google corrects toward frequent strings, and a two-word phrase beats a new
        coinage every time, which is why every search for that brand lands on 'web palette'."""
        found = near_miss("wedpalette", WORDS)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].code, "SPLIT_RISK")
        self.assertEqual(found[0].weight, 3)

    def test_an_exact_two_word_compound_is_caught_too(self):
        """`namescope` needs no edit at all: it already IS two words."""
        self.assertTrue(near_miss("namescope", WORDS))

    def test_a_coined_name_is_clean(self):
        self.assertEqual(near_miss("vantablack"[:5], WORDS), [])
        self.assertEqual(near_miss("sprinto", WORDS), [])

    def test_short_names_are_skipped(self):
        """Under six letters, edit-distance-one neighbours are so numerous that everything
        matches something. A check that fires on every name is the same as no check."""
        self.assertEqual(near_miss("wed", WORDS), [])


class TestUsGeolocation(unittest.TestCase):
    def test_the_endpoint_forces_a_country(self):
        """The bug this guards, measured 2026-08-21: run from Lima without `gl`, the endpoint
        answered with Peruvian government services, so `probia` looked hijacked by 'provias
        nacional'. Forced to the US it is hijacked by 'probiotics' instead, a completely
        different verdict for a product sold to Americans. The market you sell to is the market
        you must query."""
        self.assertIn("gl={gl}", SUGGEST)
        self.assertIn("hl={hl}", SUGGEST)


class TestBonusGrade(unittest.TestCase):
    def test_a_negative_total_earns_its_own_band(self):
        """A free bare .com carries a negative weight, so a name can score better than clean.
        Collapsing that into A would hide the thing Dylan called a huge bonus."""
        class F:
            def __init__(self, w):
                self.weight = w
        self.assertEqual(grade([F(-3)]), ("A+", -3))
        # A bonus that outweighs a real flaw still lands above clean, which is the point.
        self.assertEqual(grade([F(-3), F(2)]), ("A+", -1))
        # But it does not erase a heavy one: two 3-weight flaws survive the bonus.
        self.assertEqual(grade([F(-3), F(3), F(3)]), ("C", 3))
        self.assertEqual(grade([]), ("A", 0))


if __name__ == "__main__":
    unittest.main()
