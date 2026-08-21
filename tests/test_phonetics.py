"""Tests for the radio test.

Each case names the REAL failure it guards, not the code path. A test called
`test_silent_k` tells the next reader nothing; a test that says "Knightly must not report a /k/
sound the listener never hears" tells them why the guard exists and what breaks if it goes.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof.phonetics import analyse, syllables  # noqa: E402


def codes(name):
    return [f.code for f in analyse(name)]


def total(name):
    return sum(f.weight for f in analyse(name))


class TestSilentLetters(unittest.TestCase):
    def test_knightly_does_not_report_a_k_sound_nobody_hears(self):
        """The bug this file was written for.

        In `knight` the k is silent. The tool used to report BOTH a silent-letter finding and a
        '/k/ can be spelled c, k, ck, qu' finding, which is incoherent: there is no /k/ sound to
        misspell. Reporting a phantom sound is worse than reporting nothing, because it makes
        the whole output look guessed."""
        found = codes("Knightly")
        self.assertIn("SILENT_LETTER", found)
        self.assertNotIn("SPELL_AMBIGUOUS", found)

    def test_a_real_k_still_fires(self):
        """The guard above must not silence the case it was never about."""
        self.assertIn("SPELL_AMBIGUOUS", codes("Kestra"))

    def test_wr_and_ps_openings(self):
        self.assertIn("SILENT_LETTER", codes("Wrenly"))
        self.assertIn("SILENT_LETTER", codes("Psalis"))


class TestSoundToSpelling(unittest.TestCase):
    def test_ph_opening_costs_the_most(self):
        """A name opening on ph is heard as f and typed as f, every time."""
        self.assertIn("SPELL_AMBIGUOUS", codes("Phrasely"))

    def test_soft_c_opening(self):
        self.assertIn("SPELL_AMBIGUOUS", codes("Cyclr"))

    def test_clean_name_reports_nothing(self):
        """Vanta is the control. If this ever fails, the rules got greedy and the tool will
        start flagging every name, which is the same as flagging none."""
        self.assertEqual(analyse("Vanta"), [])
        self.assertEqual(total("Vanta"), 0)


class TestShape(unittest.TestCase):
    def test_hyphen_and_digit_are_heavy(self):
        self.assertIn("CONTAINS_HYPHEN", codes("get-name"))
        self.assertIn("CONTAINS_DIGIT", codes("name4you"))

    def test_long_name_flagged(self):
        self.assertIn("TOO_LONG", codes("supercalifragilistic"))

    def test_two_letter_name_flagged(self):
        self.assertIn("TOO_SHORT", codes("qz"))


class TestSyllables(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(syllables("vanta"), 2)
        self.assertEqual(syllables("drata"), 2)
        self.assertEqual(syllables("jq"), 1)
        self.assertEqual(syllables("commitizen"), 4)

    def test_silent_e_not_counted(self):
        """A raw vowel-group count over-reads a trailing e, so the rule subtracts it.

        `marque` is said /mark/, ONE syllable, even though it carries two vowel groups. This
        assertion was written the other way round on the first pass and the code was right: a
        test that encodes the author's guess instead of the language is worse than no test."""
        self.assertEqual(syllables("marque"), 1)
        self.assertEqual(syllables("cadence"), 2)
        self.assertEqual(syllables("vantage"), 2)


class TestOrdering(unittest.TestCase):
    def test_findings_come_back_heaviest_first(self):
        """A person reads the first line and stops. The first line has to be the worst one."""
        found = analyse("Knightsbridge-2")
        weights = [f.weight for f in found]
        self.assertEqual(weights, sorted(weights, reverse=True))


if __name__ == "__main__":
    unittest.main()
