"""Tests for the check that reads a real results page.

OFFLINE ON PURPOSE, all of it. This module's whole job is to make a network call, and a suite
that made one would be slow, flaky, and would fail on a train rather than when the code broke.
The fixtures below are trimmed from the real Bing and DuckDuckGo pages fetched on 2026-08-25 for
`msbrenew` and `msbreewc`, so the parsers are tested against the markup those engines actually
serve rather than against markup invented to match the parser.

The live behaviour is pinned separately, in `corpora/calibration.jsonl`, which is where anything
that talks to the network belongs in this repo.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof import serp  # noqa: E402
from nameproof.phonetics import grade  # noqa: E402

# Bing hides the destination behind a `bing.com/ck/a?` redirect and puts the domain in the
# aria-label of the title anchor. Trimmed from the real page for `msbreewc`.
BING_ADULT = '''
<li class="b_algo"><div class="b_tpcn"><a class="tilk" aria-label="x.com" href="https://www.bing.com/ck/a?!&amp;&amp;p=1">x</a></div></li>
<li class="b_algo"><div class="b_tpcn"><a class="tilk" aria-label="instagram.com" href="https://www.bing.com/ck/a?!&amp;&amp;p=2">ig</a></div></li>
<li class="b_algo"><div class="b_tpcn"><a class="tilk" aria-label="onlyfans.com" href="https://www.bing.com/ck/a?!&amp;&amp;p=3">of</a></div></li>
'''

BING_CLEAN = '''
<li class="b_algo"><div class="b_tpcn"><a class="tilk" aria-label="fincen.gov" href="https://www.bing.com/ck/a?!&amp;&amp;p=1">f</a></div></li>
<li class="b_algo"><div class="b_tpcn"><a class="tilk" aria-label="msrenewal.com" href="https://www.bing.com/ck/a?!&amp;&amp;p=2">m</a></div></li>
'''

# DuckDuckGo puts the real URL, percent-encoded, in the `uddg` parameter of its redirect.
DDG_ADULT = '''
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fonlyfans.com%2Fmsbreewc&amp;rut=x">OnlyFans</a>
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.instagram.com%2Fbree&amp;rut=y">Instagram</a>
'''

DDG_CLEAN = '''
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.fincen.gov%2Fmsb&amp;rut=x">FinCEN</a>
'''


class TestParsers(unittest.TestCase):
    """Parsed against the markup the engines really serve, which is the half a hand-written
    fixture always gets wrong."""

    def test_bing_domain_comes_from_the_aria_label_not_the_href(self):
        """Every Bing href is a `bing.com/ck/a?` redirect, so a parser that read hrefs would
        report bing.com ten times and call every name clean."""
        self.assertEqual(["x.com", "instagram.com", "onlyfans.com"], serp.parse_bing(BING_ADULT))

    def test_duckduckgo_url_comes_out_of_the_uddg_parameter(self):
        self.assertEqual(["onlyfans.com", "www.instagram.com"], serp.parse_duckduckgo(DDG_ADULT))

    def test_a_page_with_no_results_parses_to_nothing_rather_than_raising(self):
        self.assertEqual([], serp.parse_bing("<html><body>no results</body></html>"))
        self.assertEqual([], serp.parse_duckduckgo("<html><body>no results</body></html>"))


class TestAdultDetection(unittest.TestCase):
    def test_a_subdomain_still_resolves_to_the_registrable_domain(self):
        """The result Dylan actually saw was on `es.pornhub.com`, a localised subdomain. A
        matcher keyed on the full host would have missed it."""
        self.assertEqual(["es.pornhub.com"], serp.adult_hits(["es.pornhub.com"]))
        self.assertEqual(["www.onlyfans.com"], serp.adult_hits(["www.onlyfans.com"]))

    def test_an_adult_tld_needs_no_list_entry(self):
        self.assertEqual(["something.xxx"], serp.adult_hits(["something.xxx"]))

    def test_ordinary_results_are_not_hits(self):
        clean = ["fincen.gov", "www.microsoft.com", "fintrac-canafe.canada.ca", "x.com",
                 "www.instagram.com", "github.com", "stripe.com"]
        self.assertEqual([], serp.adult_hits(clean))

    def test_a_domain_merely_containing_an_adult_name_is_not_a_hit(self):
        """Matching on the registrable domain and never on a substring: `pornhub.com.br.evil`
        reduces to `br.evil`, and `cambridge.org` is not a cam site."""
        self.assertEqual([], serp.adult_hits(["cambridge.org", "sextantsoftware.io"]))


class TestVerdict(unittest.TestCase):
    def _patched(self, mapping):
        original = serp.results
        serp.results = lambda name, engines=None, timeout=None: mapping
        self.addCleanup(lambda: setattr(serp, "results", original))

    def test_an_adult_first_page_is_a_veto_not_a_penalty(self):
        self._patched({"bing": ["x.com", "onlyfans.com"], "duckduckgo": ["onlyfans.com"]})
        found = serp.analyse("whatever")
        self.assertEqual("NSFW_SERP", found[0].code)
        self.assertEqual(5, found[0].weight)
        self.assertEqual("X", grade(found)[0])

    def test_a_clean_first_page_carries_the_google_caveat(self):
        """`msbrenew` is clean on both readable engines and was still the name that started
        this, because Google rewrites it. A SERP_CLEAN that did not say so would be the same
        false reassurance in a new place."""
        self._patched({"bing": ["fincen.gov"], "duckduckgo": ["www.fincen.gov"]})
        found = serp.analyse("msbrenew")
        self.assertEqual("SERP_CLEAN", found[0].code)
        self.assertEqual(0, found[0].weight)
        self.assertIn("Google cannot be read", found[0].detail)

    def test_no_fetcher_is_reported_as_unchecked_and_never_as_clean(self):
        original = serp.results

        def boom(*a, **k):
            raise serp.Unavailable("no stealth fetcher configured")

        serp.results = boom
        self.addCleanup(lambda: setattr(serp, "results", original))
        found = serp.analyse("whatever")
        self.assertEqual("SERP_UNCHECKED", found[0].code)
        self.assertEqual(0, found[0].weight)
        self.assertIn("Not a pass", found[0].detail)


class TestFetcherDiscovery(unittest.TestCase):
    def test_an_unset_env_var_means_unavailable_rather_than_a_guess(self):
        """The fetcher path is machine-specific and this is a public repository. Hardcoding one
        person's home directory would make the feature look broken for everybody else."""
        original = os.environ.pop(serp.FETCHER_ENV, None)
        self.addCleanup(
            lambda: os.environ.__setitem__(serp.FETCHER_ENV, original) if original else None)
        self.assertIsNone(serp.fetcher_path())
        with self.assertRaises(serp.Unavailable):
            serp.fetch("https://example.com")

    def test_a_path_that_does_not_exist_is_not_accepted(self):
        os.environ[serp.FETCHER_ENV] = "/nope/does/not/exist.py"
        self.addCleanup(lambda: os.environ.pop(serp.FETCHER_ENV, None))
        self.assertIsNone(serp.fetcher_path())


if __name__ == "__main__":
    unittest.main()
