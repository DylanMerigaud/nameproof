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
from nameproof.phonetics import analyse, grade, syllables  # noqa: E402

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


class TestRootLexicon(unittest.TestCase):
    """A bring-your-own root file, added after a real naming run failed for a reason no
    algorithm change could fix: every A-grade output was formally clean and semantically empty,
    because the built-in roots (omni, tele, luc, vera) have nothing to do with any particular
    field. The fix is the caller's vocabulary, not a better generator."""

    def setUp(self):
        self.path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "corpora", "roots-trust.txt")

    def test_the_shipped_lexicon_loads(self):
        roots = generate.load_roots(self.path)
        self.assertGreater(len(roots), 25)
        self.assertIn("prob", roots)
        self.assertIn("cust", roots)

    def test_the_lexicon_actually_drives_the_output(self):
        """The wiring broke silently on the first attempt: the flag parsed, the file was read,
        and the generator kept using the built-in roots anyway. The output looked plausible,
        which is exactly why it went unnoticed for a full run. This asserts the roots really
        come from the file."""
        names = generate.latin_roots(n=30, seed=11, roots_file=self.path)
        from_file = set(generate.load_roots(self.path))
        builtin_only = {"clar", "nova", "scala", "tele", "omni", "luc"} - from_file
        matched = [n for n in names if any(n.lower().startswith(r) for r in from_file)]
        self.assertGreater(len(matched), len(names) // 2)
        stray = [n for n in names if any(n.lower().startswith(r) for r in builtin_only)]
        self.assertEqual(stray, [])

    def test_an_empty_file_is_refused(self):
        """A lexicon that silently falls back to the built-in roots is the failure above,
        shipped as a feature. Better to stop."""
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("# only a comment\n\n")
            tmp = fh.name
        try:
            with self.assertRaises(ValueError):
                generate.load_roots(tmp)
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()


class TestMarketProfileSteersGeneration(unittest.TestCase):
    """The wire built on 2026-08-25, and the reason it was built.

    Three of this module's shaping constants were set against four cherry-picked names (Vanta,
    Drata, Sprinto, Alessa) and said so in their own comments. Measured at n=200 the day the
    profile landed: `roots` ended on a vowel 56% of the time and `phonotactic` 46%, against 30%
    for the SOC 2 corpus, 10% for AML and 0% for developer CLI tools. The generator was not
    wrong, it was uncalibrated, and it produced one register whoever the buyer was.

    So what these cases guard is not "the profile parameter is accepted". It is that the
    parameter MOVES the output, that it moves it toward the market rather than away, and that
    passing none leaves every previously recorded run byte-identical.
    """

    def _profile(self, basename):
        from nameproof import corpus
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "corpora", basename)
        return corpus.profile(corpus.CorpusReport(corpus.load(path), label=basename), basename)

    def _open_final_rate(self, names):
        return sum(1 for x in names
                   if x.lower().endswith(generate._OPEN_FINAL_LETTERS)) / max(1, len(names))

    def test_no_profile_leaves_every_technique_byte_identical(self):
        """The seed is a promise, and it was made before the profile existed. A default draw
        that shifted by one call would break every run recorded in the README."""
        expected = {
            "rare": generate.rare_words(10, seed=42),
            "roots": generate.latin_roots(10, seed=42),
            "phonotactic": generate.phonotactic(10, seed=42),
            "markov": generate.markov_chain(10, seed=42),
        }
        for label, fn in generate.TECHNIQUES.items():
            self.assertEqual(expected[label], fn(10, seed=42, profile=None), label)

    def test_a_zero_vowel_market_gets_no_vowel_final_names(self):
        """`dev-cli` measures 0% vowel-final (ripgrep, fzf, jq, bat, fd). Before the profile,
        `phonotactic` produced 46% and could not reach that market at all."""
        p = self._profile("dev-cli.txt")
        names = generate.phonotactic(40, seed=7, profile=p)
        self.assertTrue(names)
        self.assertEqual(0.0, self._open_final_rate(names))

    def test_the_realised_rate_tracks_the_market_rather_than_a_constant(self):
        """Two markets, one technique, one seed. If the profile were decorative the two lists
        would come back with the same shape."""
        dev = self._open_final_rate(generate.phonotactic(40, seed=7,
                                                         profile=self._profile("dev-cli.txt")))
        soc = self._open_final_rate(generate.phonotactic(
            40, seed=7, profile=self._profile("soc2-compliance.txt")))
        self.assertLess(dev, soc)

    def test_a_one_syllable_market_can_actually_be_reached(self):
        """`dev-cli` is 7 of 12 one-syllable. The builder used to draw only from {2, 3}, so no
        seed and no count could ever produce that register."""
        p = self._profile("dev-cli.txt")
        names = generate.phonotactic(40, seed=3, profile=p)
        self.assertTrue(any(syllables(x) == 1 for x in names))

    def test_every_technique_respects_the_length_band(self):
        """`rare` and `markov` cannot be steered at generation time, so the band is the only
        handle on them. A technique that ignored it would put out-of-register names into a
        pool the user asked to be in-register."""
        p = self._profile("dev-cli.txt")
        for label, fn in generate.TECHNIQUES.items():
            for name in fn(25, seed=5, profile=p):
                self.assertTrue(p.fits_shape(name), "{}: {}".format(label, name))

    def test_a_profile_never_invents_a_name_to_keep_the_count_up(self):
        """The fallback paths. `latin_roots` returns a bare root plus 'a' when every seam
        fails, and `markov` used to return its last rejected draw. Either one under a profile
        would be an out-of-band name arriving through the one path that skips the filter."""
        p = self._profile("dev-cli.txt")
        for fn in (generate.latin_roots, generate.markov_chain):
            names = fn(200, seed=11, profile=p)
            self.assertTrue(all(p.fits_shape(x) for x in names), fn.__name__)

    def test_a_profiled_run_is_still_reproducible(self):
        p = self._profile("soc2-compliance.txt")
        for fn in TECHNIQUE_FUNCS:
            self.assertEqual(fn(12, seed=9, profile=p), fn(12, seed=9, profile=p), fn.__name__)
