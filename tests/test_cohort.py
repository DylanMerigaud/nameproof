"""Tests for the outcome analysis: does any measured name property predict a result?

THE HARDEST THING TO TEST HERE IS NOT THE CODE, IT IS THE METHOD. A permutation test that
forgets to stratify still runs, still prints a p-value, and still looks right; it just answers a
different question than the one asked, and it answers it confidently. That is the same failure
mode `corpora/calibration.jsonl` was built for, so the two cases that matter most below are
synthetic datasets whose true answer is known by construction:

  * an effect that lives ENTIRELY between batch years must come back null, or the stratification
    is not working and every real result is contaminated by company age;
  * an effect that lives WITHIN batch years must come back significant, or the test has no power
    and a null result means nothing at all.

Either one alone is worthless. A test with no power passes the first; a test with no
stratification passes the second. Both together are what make the real null readable.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof import cohort  # noqa: E402


def rows_from(spec):
    """`spec` is a list of (name, year, outcome) triples."""
    return [cohort.Row(n, y, o, []) for n, y, o in spec]


LENGTH_ONLY = [p for p in cohort.PROPERTIES if p[0] == "length"]


class TestStratificationActuallyStratifies(unittest.TestCase):
    """The method, proved by building the failure it has to survive."""

    def test_an_effect_that_is_purely_between_years_comes_back_null(self):
        """The confound, in its purest form. Year 2010 is all winners with short names, year
        2020 is all losers with long names. Across the whole set that is a perfect correlation
        between length and outcome; WITHIN each year there is none, and none is the truth.

        A test that pooled the years would report this as overwhelming evidence. It is the
        arithmetic version of comparing a 2007 batch against a 2025 one.
        """
        spec = ([("ab", 2010, "A") for _ in range(40)]
                + [("abcdefghij", 2020, "I") for _ in range(40)])
        results, _, strata = cohort.test_properties(rows_from(spec), properties=LENGTH_ONLY,
                                                    trials=200)
        # Neither year contains both outcomes, so neither survives `_strata`, and the honest
        # answer is that there is nothing to compare rather than a p-value.
        self.assertEqual(0, strata)
        self.assertEqual([], results)

    def test_a_between_year_effect_survives_even_with_both_outcomes_present(self):
        """The harder version: every year contains both outcomes, but the LENGTH difference is
        the same in both directions within a year, so the pooled within-year effect is zero
        while the raw means differ because the years have different name lengths."""
        spec = []
        for _ in range(20):
            spec += [("abcd", 2010, "A"), ("abcd", 2010, "I")]
        for _ in range(20):
            spec += [("abcdefghijkl", 2020, "A"), ("abcdefghijkl", 2020, "I")]
        results, _, _ = cohort.test_properties(rows_from(spec), properties=LENGTH_ONLY,
                                               trials=200)
        self.assertAlmostEqual(0.0, results[0]["difference"], places=6)
        self.assertGreater(results[0]["p_value"], 0.05)

    def test_a_real_within_year_effect_is_detected(self):
        """Power. Without this case a stratifier that always returned null would pass every
        other test in the file, and the real null result would mean nothing."""
        spec = []
        for _ in range(40):
            spec += [("ab", 2010, "A"), ("abcdefghijklmno", 2010, "I"),
                     ("ab", 2020, "A"), ("abcdefghijklmno", 2020, "I")]
        results, _, _ = cohort.test_properties(rows_from(spec), properties=LENGTH_ONLY,
                                               trials=200)
        self.assertLess(results[0]["difference"], -10)
        self.assertLess(results[0]["p_value"], 0.01)

    def test_a_year_with_only_one_outcome_is_dropped_not_defaulted(self):
        spec = ([("aaa", 2010, "A"), ("bbbb", 2010, "I")]
                + [("ccccc", 2015, "A") for _ in range(10)])
        results, n, strata = cohort.test_properties(rows_from(spec), properties=LENGTH_ONLY,
                                                    trials=100)
        self.assertEqual(1, strata)
        self.assertEqual(2, n)


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_p_value(self):
        """A p-value that moves between two runs of the same command is not evidence. Same
        promise `generate` makes about its seed, for the same reason."""
        rows = cohort.select(cohort.load())
        a, _, _ = cohort.test_properties(rows, properties=LENGTH_ONLY, trials=200, seed=7)
        b, _, _ = cohort.test_properties(rows, properties=LENGTH_ONLY, trials=200, seed=7)
        self.assertEqual(a[0]["p_value"], b[0]["p_value"])

    def test_the_observed_difference_does_not_depend_on_the_seed_at_all(self):
        """Only the null distribution is random. An observed statistic that moved with the seed
        would mean the permutation was being applied to the real labels."""
        rows = cohort.select(cohort.load())
        a, _, _ = cohort.test_properties(rows, properties=LENGTH_ONLY, trials=50, seed=1)
        b, _, _ = cohort.test_properties(rows, properties=LENGTH_ONLY, trials=50, seed=2)
        self.assertAlmostEqual(a[0]["difference"], b[0]["difference"], places=10)

    def test_p_is_never_reported_as_zero(self):
        """A finite number of permutations cannot distinguish 'very unlikely' from
        'impossible', and printing 0.0000 would claim it could."""
        spec = []
        for _ in range(40):
            spec += [("ab", 2010, "A"), ("abcdefghijklmno", 2010, "I")]
        results, _, _ = cohort.test_properties(rows_from(spec), properties=LENGTH_ONLY,
                                               trials=100)
        self.assertGreater(results[0]["p_value"], 0.0)


class TestTheRealFinding(unittest.TestCase):
    """The result this module exists to report, pinned so it cannot drift silently."""

    def setUp(self):
        self.rows = cohort.select(cohort.load())

    def test_the_cohort_is_the_size_it_claims_to_be(self):
        self.assertGreater(len(self.rows), 1800)
        self.assertGreater(sum(1 for r in self.rows if r.won), 700)

    def test_active_companies_are_excluded_from_the_comparison(self):
        """A company still running has not answered yet. Counting it as either outcome would
        let the batch year decide the result all over again."""
        self.assertTrue(all(r.outcome in ("A", "P", "I") for r in self.rows))
        self.assertGreater(len(cohort.load()), len(self.rows))

    def test_the_length_effect_dissolves_under_the_word_count_control(self):
        """THE finding. Overall, length reaches significance; restricted to single-word names
        it is noise. Anything that made this test fail would mean the headline in the README,
        the module docstring and the audit are all now wrong."""
        c = cohort.confound_check(self.rows, trials=500)
        self.assertIsNotNone(c)
        self.assertGreater(c["p_value"], 0.05)
        self.assertLess(abs(c["difference"]), 0.3)

    def test_the_verdict_says_so_in_words(self):
        results, _, _ = cohort.test_properties(self.rows, trials=300)
        confound = cohort.confound_check(self.rows, trials=300)
        text = cohort.verdict(results, cohort.alpha(len(results)), confound)
        self.assertIn("NOT about length", text)

    def test_a_null_verdict_says_nothing_predicts(self):
        results = [{"key": "length", "label": "l", "difference": 0.0, "p_value": 0.9, "n": 10}]
        self.assertIn("Nothing this tool measures predicts",
                      cohort.verdict(results, 0.05, None))


class TestLoading(unittest.TestCase):
    def test_every_market_slice_is_big_enough_to_report(self):
        rows = cohort.load()
        for m in cohort.MARKETS_IN_DATA:
            self.assertGreater(len(cohort.select(rows, market=m)), 100, m)

    def test_comment_and_blank_lines_are_not_companies(self):
        self.assertTrue(all(not r.name.startswith("#") for r in cohort.load()))

    def test_names_are_kept_verbatim(self):
        """Third-party names are data. A loader that title-cased or stripped punctuation would
        be editing the evidence, and every share measured on top of it would be measuring the
        edit."""
        names = {r.name for r in cohort.load()}
        self.assertTrue(any(n != n.title() for n in names))

    def test_render_runs_on_a_market_slice(self):
        rows = cohort.select(cohort.load(), market="ai")
        out = cohort.render(rows, market="ai", trials=100)
        self.assertIn("cohort: ai", out)
        self.assertIn("read as:", out)


if __name__ == "__main__":
    unittest.main()
