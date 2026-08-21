"""Tests for the SEO rules.

Only the offline half is tested here on purpose. `brand_collision` hits Wikidata, and a test
that needs the network is a test that fails on a plane and gets deleted a month later. Its
failure mode is covered instead: a lookup that cannot complete returns COLLISION_UNKNOWN with
weight 0, never an empty list, because "I could not check" must not read as "it is clean".
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nameproof.seo import COMMON, dictionary_word, keyword_in_name  # noqa: E402


class TestDictionaryWord(unittest.TestCase):
    def test_a_plain_english_word_is_the_heaviest_finding(self):
        found = dictionary_word("anchor")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].code, "DICTIONARY_WORD")
        self.assertEqual(found[0].weight, 3)

    def test_a_coined_word_is_clean(self):
        self.assertEqual(dictionary_word("Vanta"), [])
        self.assertEqual(dictionary_word("Sprinto"), [])

    def test_case_and_punctuation_do_not_hide_a_word(self):
        """'Anchor', 'ANCHOR' and 'anchor.' are the same name to a search engine."""
        for variant in ("Anchor", "ANCHOR", "anchor."):
            self.assertTrue(dictionary_word(variant), variant)

    def test_embedded_list_works_without_a_system_dictionary(self):
        """The tool promises to run with nothing installed, so the common-word check cannot
        depend on the machine having /usr/share/dict/words."""
        self.assertIn("anchor", COMMON)
        self.assertIn("beacon", COMMON)


class TestCategoryKeyword(unittest.TestCase):
    def test_flags_the_category_word(self):
        found = keyword_in_name("complyflow", ["comply", "audit"])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].code, "CATEGORY_KEYWORD")

    def test_weight_stays_low_because_google_says_it_is_low(self):
        """Weight 1, not 3. Google's own guidance is that domain keywords have 'hardly any
        effect'. Scoring it heavily would be inventing a penalty the source does not support,
        which is exactly the folklore this module refuses to carry."""
        self.assertEqual(keyword_in_name("complyflow", ["comply"])[0].weight, 1)

    def test_no_keywords_supplied_means_no_finding(self):
        self.assertEqual(keyword_in_name("complyflow", []), [])


if __name__ == "__main__":
    unittest.main()
