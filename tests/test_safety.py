"""Tests for the connotation gate: does the name mean something you cannot put on an invoice?

THE TWO WAYS THIS CHECK FAILS ARE OPPOSITE AND BOTH ARE FATAL, so the file is organised around
them rather than around the functions.

  It lets a no-go through. That is what happened: Dylan searched a candidate on 2026-08-25 and
  got pornography, and every check in the tool had said the name was fine.

  It blocks a clean name. That is worse in practice, because a gate that fires on `Cultura`,
  `Oculus` or `Computix` gets switched off, and a gate nobody runs protects nothing. The first
  version of the fragment list did exactly this, which is why there are two tiers.

Each case names the real defect it guards, same convention as the rest of the suite.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof import safety, seo  # noqa: E402
from nameproof.phonetics import grade  # noqa: E402

HAS_DICT = seo.has_system_dict()


class TestTheGateBlocksWhatItMust(unittest.TestCase):
    def test_a_coined_name_carrying_an_unambiguous_fragment_is_blocked(self):
        for name in ("Analfin", "Pornova", "Sexora", "Milfy", "Fuckly"):
            self.assertTrue(safety.is_blocked(name), name)

    def test_a_blocked_name_carries_a_weight_5_finding_with_the_fragment_named(self):
        found = safety.connotation("Pornova")
        self.assertEqual("NSFW_FRAGMENT", found[0].code)
        self.assertEqual(5, found[0].weight)
        self.assertIn("porn", found[0].detail)

    def test_french_fragments_count_too(self):
        """The skill's own rule asks for 'lecture involontaire en EN et FR'. A name that is
        clean in English and obscene in French is the classic expensive mistake, and this
        user's market is French."""
        self.assertTrue(safety.is_blocked("Salopix"))
        self.assertTrue(safety.is_blocked("Enculo"))


@unittest.skipUnless(HAS_DICT, "no system dictionary on this machine")
class TestTheGateDoesNotBlockWhatItMustNot(unittest.TestCase):
    """The Scunthorpe half. Every name here was a real false positive at some point today."""

    def test_an_ordinary_english_word_is_not_a_risky_name(self):
        for name in ("Analytics", "Scatter", "Cockpit", "Sextant", "Analyse"):
            self.assertFalse(safety.is_blocked(name), name)
            self.assertEqual([], safety.connotation(name), name)

    def test_the_soft_tier_warns_and_never_blocks(self):
        """`Cultura`, `Bitewave` and `Chattera` are coined, carry a productive fragment, and
        must still pass. A gate that stops them is a gate that gets disabled."""
        for name in ("Cultura", "Bitewave", "Chattera", "Computix"):
            self.assertFalse(safety.is_blocked(name), name)

    def test_a_soft_hit_is_still_reported_to_the_human(self):
        found = safety.connotation("Cultura")
        self.assertEqual(1, len(found))
        self.assertEqual("NSFW_NEAR", found[0].code)
        self.assertEqual(2, found[0].weight)

    def test_real_brands_that_would_embarrass_a_naive_matcher(self):
        """`Oculus` contains a French obscenity as a substring and is a real, successful brand.
        `Stripe` carries a 'slang' label on Wiktionary. Neither is a naming problem."""
        for name in ("Oculus", "Stripe", "Vanta", "Drata", "Ripgrep", "Nova"):
            self.assertFalse(safety.is_blocked(name), name)

    def test_the_suppression_does_not_suppress_the_fragment_itself(self):
        """The subtle one. `anal` is in the dictionary too, so a naive real-word suppression
        makes the fragment suppress itself and the gate never fires on the bare term."""
        self.assertTrue(safety.is_blocked("Anal"))
        self.assertTrue(safety.is_blocked("Porn"))

    def test_a_clean_token_next_to_a_dirty_one_does_not_launder_it(self):
        self.assertTrue(safety.is_blocked("Acme Porn"))


class TestVetoGrade(unittest.TestCase):
    def test_a_blocked_name_does_not_grade_as_merely_mediocre(self):
        """The bug this band exists for. At weight 5 the total landed in band C, which reads
        as 'usable but unremarkable'. Dylan called this class of name a no go, and a no go is
        not a C."""
        findings = safety.connotation("Analfin")
        g, _ = grade(findings)
        self.assertEqual("X", g)

    def test_a_soft_hit_stays_on_the_normal_scale(self):
        g, total = grade(safety.connotation("Cultura"))
        self.assertNotEqual("X", g)
        self.assertEqual(2, total)


class TestGoldRefusesBlockedNames(unittest.TestCase):
    def test_the_gold_profile_rejects_a_blocked_name_whatever_else_it_scores(self):
        """A GOLD name is meant to be a resellable asset. A name whose search results are
        pornography is not an asset with a drawback, it is not an asset, so the gate runs
        before length, syllables and phonetics rather than alongside them."""
        from nameproof import gold
        self.assertFalse(gold.passes_profile("Pornova"))
        self.assertFalse(gold.passes_profile("Analfin"))

    def test_a_clean_name_of_the_same_shape_still_passes(self):
        """Without this, the case above would also pass on a gate that rejected everything."""
        from nameproof import gold
        self.assertTrue(gold.passes_profile("Novara"))


class TestSenseLabelsCalibration(unittest.TestCase):
    """The online half. These hit Wiktionary, so they are skipped when it does not answer
    rather than failing: a network outage is not a regression."""

    def _labels(self, word):
        got = safety.labels_for(word)
        if got is None:
            self.skipTest("Wiktionary did not answer")
        return got

    def test_a_pornographic_term_is_labelled_as_one(self):
        self.assertTrue(self._labels("creampie") & safety.TRIGGER_LABELS)

    def test_stripe_is_not_flagged_by_a_bare_slang_label(self):
        """THE calibration case, and it decides the whole trigger set. Stripe is one of the
        most successful company names in software and Wiktionary labels it slang. A check that
        fired on 'slang' would reject it, so only sexual and abusive labels trigger."""
        labels = self._labels("stripe")
        self.assertIn("slang", labels)
        self.assertEqual(set(), labels & safety.TRIGGER_LABELS)
        self.assertEqual([], safety.sense_labels("stripe"))

    def test_a_word_with_no_entry_is_clean_and_not_unknown(self):
        """Every good coined name is missing from the dictionary. Reading a missing page as
        'could not check' would attach a warning to exactly the names this tool produces."""
        got = safety.labels_for("qzxkwvbnmpl")
        if got is None:
            self.skipTest("Wiktionary did not answer")
        self.assertEqual(set(), got)
        self.assertEqual([], safety.sense_labels("qzxkwvbnmpl"))

    def test_case_variants_are_tried(self):
        """`milf` has no Wiktionary entry; `MILF` does. A lookup that only tried the lowercase
        form reported the most predictable collision in the whole list as clean."""
        self.assertTrue(self._labels("milf") & safety.TRIGGER_LABELS)


class TestOfflineContract(unittest.TestCase):
    def test_the_gate_never_touches_the_network(self):
        """`gold` and `generate` run the gate on hundreds of candidates. A network call per
        candidate is not a filter, it is a rate limit, and a gate that depends on the network
        silently opens when the network is down."""
        import urllib.request

        def boom(*a, **k):
            raise AssertionError("the offline gate made a network call")

        original = urllib.request.urlopen
        urllib.request.urlopen = boom
        try:
            safety.is_blocked("Analfin")
            safety.connotation("Cultura")
        finally:
            urllib.request.urlopen = original

    def test_an_empty_name_does_not_raise(self):
        self.assertEqual([], safety.connotation(""))
        self.assertFalse(safety.is_blocked("   "))


if __name__ == "__main__":
    unittest.main()
