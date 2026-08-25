"""Tests for `nameproof gold`.

Same convention as `test_generate.py`: each case names the real defect it guards. `gold` adds
exactly one new thing over `generate`, the profile gate in `gold.passes_profile`, plus one
wiring fact worth its own test: the embedded GOLD lexicon actually drives `gold_roots`, the same
way `--roots <file>` had to be proven to actually drive `latin_roots` in `test_generate.py`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof import gold  # noqa: E402
from nameproof.phonetics import syllables  # noqa: E402


class TestReproducibility(unittest.TestCase):
    def test_same_seed_same_names_every_technique(self):
        """The one promise that makes a generator useful instead of a slot machine."""
        for fn in gold.TECHNIQUES.values():
            first = fn(20, seed=42)
            second = fn(20, seed=42)
            self.assertEqual(first, second, fn.__name__)

    def test_different_seed_usually_different_names(self):
        for fn in gold.TECHNIQUES.values():
            a = fn(20, seed=1)
            b = fn(20, seed=2)
            self.assertNotEqual(a, b, fn.__name__)


class TestGoldRootsLexicon(unittest.TestCase):
    """`gold_roots` has to actually come from `GOLD_ROOTS`, not silently fall back to
    `generate.ROOTS`. The wiring for `--roots <file>` broke exactly this way once (see
    `test_generate.TestRootLexicon`), so the same regression is worth guarding here even though
    the lexicon is embedded rather than a file."""

    def test_every_name_traces_to_a_gold_root(self):
        names = gold.gold_roots(30, seed=42)
        roots = sorted(gold.GOLD_ROOTS, key=len, reverse=True)
        for name in names:
            w = name.lower()
            self.assertTrue(any(w.startswith(r) for r in roots), name)

    def test_gold_roots_are_not_just_the_generic_builtin_roots(self):
        """`GOLD_ROOTS` overlaps `generate.ROOTS` on a few entries on purpose (nova, vera, flux
        were named explicitly in the request this module answers), but it has to be its OWN
        lexicon, not a re-export: it carries roots `generate.ROOTS` does not have."""
        from nameproof import generate
        self.assertTrue(set(gold.GOLD_ROOTS) - set(generate.ROOTS))


class TestGoldProfile(unittest.TestCase):
    """`passes_profile` is the gate that makes `gold` different from `generate --score`: length,
    syllable count, no digit or hyphen, no niche vertical morpheme, on top of the same
    pronounceability grade cut."""

    def test_too_short_is_rejected(self):
        self.assertFalse(gold.passes_profile("Ax"))

    def test_too_long_is_rejected(self):
        self.assertFalse(gold.passes_profile("Supercalifragilistic"))

    def test_length_window_is_configurable(self):
        # "Nova" is 4 letters: kept at the default floor, rejected once the floor is raised.
        self.assertTrue(gold.passes_profile("Nova", min_length=4, max_length=9))
        self.assertFalse(gold.passes_profile("Nova", min_length=5, max_length=9))

    def test_wrong_syllable_count_is_rejected(self):
        # "Strengths" is one syllable, below the GOLD floor of two.
        self.assertLessEqual(syllables("Strengths"), 1)
        self.assertFalse(gold.passes_profile("Strengths"))

    def test_digit_is_rejected(self):
        self.assertFalse(gold.passes_profile("Nova4"))

    def test_hyphen_is_rejected(self):
        self.assertFalse(gold.passes_profile("No-va"))

    def test_niche_morpheme_is_rejected_even_inside_a_shaped_candidate(self):
        """The three morphemes named in the request that created this gate: `msb` (money
        service business), `pama`, `clfs`. All three are also real fragments of other bets in
        this portfolio (msbrenew, pamawatch), which is exactly the failure mode: a GOLD name
        must not read as bought for one of them."""
        self.assertFalse(gold.passes_profile("Msbara"))
        self.assertFalse(gold.passes_profile("Pamano"))
        self.assertFalse(gold.passes_profile("Clfsonic"))

    def test_a_clean_short_pronounceable_name_passes(self):
        self.assertTrue(gold.passes_profile("Nova"))
        self.assertTrue(gold.passes_profile("Vanta"))

    def test_rough_pronounceability_is_rejected(self):
        """The profile has to reuse the SAME phonetic gate `score` uses, not a laxer one.
        `Phrasely` is this repo's own README example of a grade-C name (the initial `ph` reads
        as /f/ and competes with `f`), and it clears length and syllable count fine: the grade
        gate is the only thing standing between it and a GOLD candidate."""
        self.assertFalse(gold.passes_profile("Phrasely"))


class TestNoDuplicates(unittest.TestCase):
    def test_no_duplicates_within_one_call(self):
        for fn in gold.TECHNIQUES.values():
            names = fn(25, seed=42)
            lowered = [n.lower() for n in names]
            self.assertEqual(len(lowered), len(set(lowered)), fn.__name__)


class TestPoolAfterProfile(unittest.TestCase):
    """An end-to-end check of the same pooling logic `cli.cmd_gold` runs, without going through
    argparse: pool every technique, filter by the profile, and expect a non-trivial number of
    survivors at the CLI's own defaults, deterministically for a fixed seed."""

    def test_default_seed_yields_gold_grade_survivors(self):
        survivors = []
        for fn in gold.TECHNIQUES.values():
            for name in fn(n=30, seed=42):
                if gold.passes_profile(name):
                    survivors.append(name)
        self.assertGreater(len(survivors), 0)
        # Reproducible: rerunning the exact same pooling must yield the exact same survivors.
        again = []
        for fn in gold.TECHNIQUES.values():
            for name in fn(n=30, seed=42):
                if gold.passes_profile(name):
                    again.append(name)
        self.assertEqual(survivors, again)


if __name__ == "__main__":
    unittest.main()
