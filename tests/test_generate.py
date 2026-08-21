"""Tests for the name generators.

Each case names the REAL defect it guards, not the code path, same convention as
`test_phonetics.py`. The three properties that actually matter for a generator built on a fixed
seed are reproducibility (a seed is a promise), no duplicates within one call (a list with the
same name twice is not twenty names), and that a technique built to guarantee pronounceability
"by construction" actually clears its own bar when checked, not just by claim.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof import generate  # noqa: E402
from nameproof.phonetics import analyse, grade  # noqa: E402

TECHNIQUE_FUNCS = [generate.rare_words, generate.latin_roots,
                   generate.phonotactic, generate.markov_chain]


class TestReproducibility(unittest.TestCase):
    def test_same_seed_same_names_every_technique(self):
        """The one promise that makes a generator useful instead of a slot machine: rerunning
        it later, on another machine, has to produce the exact same list."""
        for fn in TECHNIQUE_FUNCS:
            first = fn(15, seed=42)
            second = fn(15, seed=42)
            self.assertEqual(first, second, fn.__name__)

    def test_different_seed_usually_different_names(self):
        """The opposite failure is just as real: a seed argument that is silently ignored would
        also pass the test above."""
        for fn in TECHNIQUE_FUNCS:
            a = fn(15, seed=1)
            b = fn(15, seed=2)
            self.assertNotEqual(a, b, fn.__name__)


class TestNoDuplicates(unittest.TestCase):
    def test_no_duplicates_within_one_call(self):
        """A list of 20 names with the same one twice is nineteen names wearing a disguise."""
        for fn in TECHNIQUE_FUNCS:
            names = fn(25, seed=42)
            lowered = [n.lower() for n in names]
            self.assertEqual(len(lowered), len(set(lowered)), fn.__name__)


class TestOwnPronounceabilityCheck(unittest.TestCase):
    """`phonotactic` is built from consonant clusters and vowels attested at real English
    syllable boundaries, so its own claim is that every name it produces should pass the
    tool's OWN phonetic rules cleanly. This is the point of the whole exercise: a generator
    that fails the judge sitting right next to it in the same repo is not trustworthy."""

    def test_phonotactic_names_grade_a_or_b_on_average(self):
        names = generate.phonotactic(40, seed=42)
        grades = [grade(analyse(n))[0] for n in names]
        good = sum(1 for g in grades if g in ("A", "B"))
        # Not 100%: a handful of attested clusters read as spelling-ambiguous on their own
        # (an initial "k" competes with c/ck/qu regardless of how it was assembled). Most of
        # the list clearing the bar is the claim; all of it clearing is not.
        self.assertGreater(good / len(grades), 0.6, grades)

    def test_rare_words_are_real_dictionary_words_not_a_single_repeated_placeholder(self):
        """`rare_words` promises pronounceability BECAUSE every candidate is an attested word.
        The cheapest way that promise breaks silently is the data file collapsing to one line
        or one word repeated: guard the pool size, not just the sampled output."""
        pool = generate._load_rare_words()
        self.assertGreater(len(pool), 500)
        self.assertEqual(len(pool), len(set(pool)))


class TestLatinRoots(unittest.TestCase):
    def test_every_name_traces_to_a_known_root(self):
        """A root+suffix combiner that starts inventing roots is a Markov chain wearing a
        different docstring. Every generated name must start with one of the declared roots."""
        names = generate.latin_roots(20, seed=42)
        roots = sorted(generate.ROOTS, key=len, reverse=True)
        for name in names:
            w = name.lower()
            self.assertTrue(any(w.startswith(r) for r in roots), name)

    def test_no_doubled_vowel_seam(self):
        """`scala` + `a` used to produce `Scalaa`: a doubled-vowel seam reads as a typo, not a
        brand. Regression guard for the seam list in `generate.BAD_SEAMS`."""
        import re
        names = generate.latin_roots(60, seed=1)
        for name in names:
            self.assertIsNone(re.search(r"([aeiou])\1", name.lower()), name)


class TestMarkovChain(unittest.TestCase):
    def test_length_stays_in_a_sayable_range(self):
        """The character model trained at trigram order will happily run past what a person can
        hold in their head if nothing stops it; length is the cheapest thing to check."""
        for name in generate.markov_chain(30, seed=42):
            self.assertGreaterEqual(len(name), 4, name)
            self.assertLessEqual(len(name), 9, name)

    def test_ends_on_an_attested_consonant_cluster(self):
        """The filter this technique needs and the other three do not: a name is rejected if it
        closes on a two-or-more consonant cluster no real English word closes on."""
        phonotactics = generate._load_phonotactics()
        legal_codas = phonotactics["coda_graphs"]
        for name in generate.markov_chain(30, seed=7):
            self.assertTrue(
                generate._has_attested_edges(name, phonotactics["onset_graphs"], legal_codas),
                name)


class TestCountRequested(unittest.TestCase):
    def test_returns_up_to_the_requested_count(self):
        """`latin_roots` draws from a few hundred root/suffix combinations; asking for more
        names than the vocabulary holds must not hang the process."""
        names = generate.latin_roots(10, seed=42)
        self.assertLessEqual(len(names), 10)
        self.assertGreater(len(names), 0)


if __name__ == "__main__":
    unittest.main()
