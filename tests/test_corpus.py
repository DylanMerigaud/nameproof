"""Tests for the market statistics, the module that had none.

WHY THIS FILE STARTS EXISTING ON 2026-08-25. `corpus.py` was the only module in the package with
no test file, and it is the module the README's best finding rests on: product companies name
the category 10% of the time, service firms 50%. Nothing guarded that number, and the module was
carrying a live substring bug of exactly the class `corpora/calibration.jsonl` exists to catch.

Each case names the REAL defect it guards, not the code path, same convention as
`test_phonetics.py` and `test_generate.py`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof import corpus, seo  # noqa: E402

# The real-word share degrades to a 52-word embedded list when the machine has no
# /usr/share/dict/words, and `CorpusReport` reports that degradation rather than printing a
# share off a stub. A test that asserted the share anyway would fail on exactly the machines
# the tool promises to run on with nothing installed, so those cases skip instead of lying.
HAS_DICT = seo.has_system_dict()

CORPORA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpora")


def report(basename):
    path = os.path.join(CORPORA, basename)
    return corpus.CorpusReport(corpus.load(path), label=basename)


class TestCategoryIsMatchedAtAWordEdge(unittest.TestCase):
    """The substring bug, shipped twice.

    `corpora/calibration.jsonl` already carries this failure for the search check: `normfin` IS
    inside `normfinder`, so a naive `in` test called a hijacked name healthy. The same mistake
    was live in `corpus.py` against `CATEGORY_HINTS`, and it returned a confident, plausible,
    wrong answer only on names nobody had fed it yet, which is why nothing noticed.
    """

    def test_hint_inside_an_unrelated_word_does_not_count(self):
        """The three found by probing 40 real startup names on 2026-08-25. `api` is inside
        Rapid7 and `hr` is inside Anthropic and Threads; none of the three names the category."""
        for name in ("Rapid7", "Anthropic", "Threads"):
            self.assertEqual([], corpus.names_category(name), name)

    def test_hint_opening_a_token_still_counts(self):
        """The opposite failure is just as real: a fix that only accepted a whole-token match
        would miss every compound, which is most of how a category word shows up in a brand."""
        self.assertIn("secure", corpus.names_category("Secureframe"))
        self.assertIn("data", corpus.names_category("Datadog"))

    def test_hint_closing_a_token_still_counts(self):
        self.assertIn("tech", corpus.names_category("Fintech"))
        self.assertIn("pay", corpus.names_category("Gopay"))

    def test_camel_case_seam_is_a_word_boundary(self):
        """`MyComplianceOffice` has no spaces, and the capital is the only boundary signal
        there is. Lowercasing before the split throws it away."""
        self.assertEqual(["compliance"], corpus.names_category("MyComplianceOffice"))

    def test_all_caps_name_is_one_token(self):
        """`COMPLY` and `ACA` have no camel seam; splitting an all-caps run on capitals would
        produce one token per letter and match nothing."""
        self.assertEqual(["comply"], corpus.names_category("COMPLY"))
        self.assertEqual(["group"], corpus.names_category("ACA Group"))


class TestTheHeadlineFindingStillReproduces(unittest.TestCase):
    """The README's flagship result, as a regression instead of a claim.

    It was produced by a human running `market` twice and diffing by eye. That makes it exactly
    the kind of number that quietly stops being true after a refactor, so it is pinned here
    against the real bundled corpora rather than a fixture: if the category test changes
    meaning, this is what says so.
    """

    def test_product_market_rarely_names_the_category(self):
        r = report("soc2-compliance.txt")
        self.assertEqual(10, r.n)
        self.assertEqual(["Secureframe"], r.with_category)

    def test_service_market_names_the_category_far_more_often(self):
        r = report("ria-compliance.txt")
        self.assertEqual(12, r.n)
        self.assertGreaterEqual(r.category_share, 0.5)

    def test_the_gap_between_them_is_the_finding(self):
        """A tool that reported the same share for both would be useless here, and the whole
        claim in the README is the DISTANCE, not either number on its own."""
        product = report("soc2-compliance.txt").category_share
        service = report("ria-compliance.txt").category_share
        self.assertGreaterEqual(service - product, 0.3)


@unittest.skipUnless(HAS_DICT, "no system dictionary on this machine")
class TestRealWordShare(unittest.TestCase):
    """The axis the naming rule turns on, and the one the stats could not report until now."""

    def test_a_coined_name_is_not_built_from_real_words(self):
        self.assertFalse(corpus.built_from_real_words("Vanta"))
        self.assertFalse(corpus.built_from_real_words("Drata"))

    def test_a_compound_of_real_words_counts_as_real(self):
        """`Strike Graph` is not a dictionary entry itself, and it is still a different register
        from `Vanta`. Testing the name as one string would call it coined."""
        self.assertTrue(corpus.built_from_real_words("Strike Graph"))

    def test_an_empty_name_is_not_a_real_word(self):
        """Guards the `all()` of an empty sequence, which is True and would report a blank line
        as an ordinary English word."""
        self.assertFalse(corpus.built_from_real_words(""))
        self.assertFalse(corpus.built_from_real_words("42"))


class TestReportShape(unittest.TestCase):
    def test_empty_corpus_does_not_divide_by_zero(self):
        r = corpus.CorpusReport([])
        self.assertEqual(0, r.n)
        self.assertEqual(0.0, r.category_share)
        self.assertEqual("empty corpus", r.verdict())
        r.render()

    def test_verdict_carries_n(self):
        """Every corpus in this repository is between 10 and 21 names. A share computed on 10
        reads exactly like a share computed on 1000 until the day somebody acts on one."""
        self.assertIn("(n=10)", report("soc2-compliance.txt").verdict())

    def test_blank_and_comment_lines_are_not_names(self):
        r = corpus.CorpusReport(["Vanta", "", "  ", "Drata"])
        self.assertEqual(2, r.n)


class TestFits(unittest.TestCase):
    def test_a_space_against_a_single_word_market_is_a_finding(self):
        r = report("soc2-compliance.txt")
        codes = [f.code for f in corpus.fits("Strike Graph", r)]
        self.assertIn("OFF_PATTERN", codes)

    def test_a_conforming_name_produces_nothing(self):
        r = report("soc2-compliance.txt")
        self.assertEqual([], corpus.fits("Vanta", r))

    def test_empty_name_does_not_raise(self):
        """`fits` splits on whitespace and indexes [0]. A blank name reaching it through a
        generator's fallback path would have been an IndexError, not a finding."""
        self.assertEqual([], corpus.fits("   ", report("soc2-compliance.txt")))


class TestMarketProfile(unittest.TestCase):
    """The contract with `generate.py`. Everything here is a number a technique acts on, so a
    change to one of these silently changes the names the tool produces."""

    def test_open_final_target_comes_from_the_corpus(self):
        self.assertEqual(0.0, corpus.profile(report("dev-cli.txt")).open_final)
        self.assertAlmostEqual(0.3, corpus.profile(report("soc2-compliance.txt")).open_final)

    def test_length_band_is_clamped_to_what_the_scorer_accepts(self):
        """`dev-cli` contains `jq` and `fd` at two letters, and `phonetics.shape_risk` calls
        anything under three unsearchable. An unclamped band would ask the generator for names
        its own scorer rejects on sight."""
        p = corpus.profile(report("dev-cli.txt"))
        self.assertGreaterEqual(p.len_min, 3)
        self.assertTrue(p.clamped)
        self.assertIn("clamped", p.describe())

    def test_syllable_weights_carry_the_markets_own_distribution(self):
        """`dev-cli` is 7 of 12 one-syllable. Before the profile existed, `phonotactic` could
        not emit a one-syllable name at all, so that market was unreachable."""
        w = corpus.profile(report("dev-cli.txt")).syllable_weights
        self.assertEqual(1, max(w, key=lambda k: w[k]))

    def test_an_unbuildable_corpus_falls_back_to_the_old_default(self):
        """A corpus whose every name is longer than the builder can assemble must not produce
        an empty weight table: `random.choices` raises on one, and the honest fallback is the
        pre-profile behaviour rather than a number the builder cannot honour."""
        p = corpus.profile(corpus.CorpusReport(["Supercalifragilisticexpialidocious"]))
        self.assertEqual({2: 80, 3: 20}, p.syllable_weights)

    def test_fits_shape_rejects_outside_the_band(self):
        p = corpus.profile(report("dev-cli.txt"))
        self.assertTrue(p.fits_shape("ripgrep"))
        self.assertFalse(p.fits_shape("Supercalifragilistic"))


class TestDegradedDictionary(unittest.TestCase):
    def test_report_states_whether_the_share_was_measurable(self):
        """`0% are real words` off a missing dictionary is the confident-plausible-wrong shape
        `doctor` exists for. The render says which of the two it is."""
        r = report("soc2-compliance.txt")
        if r.dictionary_available:
            self.assertIn("built from real words  :", r.render())
            self.assertIn("built from real words", r.verdict())
        else:
            self.assertIn("no system dictionary", r.render())
            self.assertNotIn("built from real words", r.verdict())


class TestCompare(unittest.TestCase):
    def test_comparison_names_the_market_that_splits_them(self):
        out = corpus.compare([report("soc2-compliance.txt"), report("ria-compliance.txt")])
        self.assertIn("names the category splits these markets", out)
        self.assertIn("ria-compliance.txt", out)

    def test_comparison_carries_n_for_every_column(self):
        out = corpus.compare([report("soc2-compliance.txt"), report("ria-compliance.txt")])
        self.assertIn("(n=10)", out)
        self.assertIn("(n=12)", out)

    def test_two_identical_markets_split_nothing(self):
        """A comparison that always finds a split is the same as no comparison at all."""
        out = corpus.compare([report("dev-cli.txt"), report("dev-cli.txt")])
        self.assertNotIn("splits these markets", out)


if __name__ == "__main__":
    unittest.main()
