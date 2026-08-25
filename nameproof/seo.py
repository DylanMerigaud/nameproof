"""Will you be able to rank for your own name?

Neither comparable tool touches SEO at all. That is the gap this module fills, and it fills it
with PRIMARY sources: every rule below cites a Google Search Central page and the date it was
read. SEO folklore is enormous and most of it is uncheckable, so a rule that cannot name its
source does not go in.

THE ONE THAT MATTERS MOST, and it is Google saying it about itself. From the Site names page
(developers.google.com/search/docs/appearance/site-names, last updated 2025-12-10, read
2026-08-21):

    "Avoid using a generic name. A generic name like 'Best Dentists In Iowa' is unlikely to be
     selected by our system as a site name, unless that's an extremely well-recognized brand
     name."

Read that twice, because it describes a trap with no exit for a new company. A generic name is
not shown as your site name until you are already famous, and being shown as your site name is
part of how you become famous. Pick a dictionary word and you start inside that loop.

WHAT THIS MODULE DELIBERATELY DOES NOT DO, and each omission is a decision:

  * No TLD ranking penalty. Google, SEO Starter Guide, same date: "The TLD ... only matters if
    you're targeting a specific country's users, and even then it's usually a low impact signal."
    Coding a .io penalty would contradict the primary source. TLD risk lives in `tld_risk.py`
    and is about SOVEREIGNTY, which is a different question entirely.
  * No domain-length rule. No Google page mentions it. The correlation everyone quotes is
    confounded by domain age and authority. Length stays in `phonetics.py` where it belongs, as
    a usability matter.
  * No hyphen-count coefficient. Google's URL structure page recommends hyphens over
    underscores for READABILITY and says nothing about ranking. Inventing a number would fake a
    precision that does not exist.
  * No separate AI Overview rule. It is a plausible deduction that a dictionary-word brand turns
    a navigational query into an ambiguous one, but no measurement was found. Folding it in as
    its own rule would count the same uncertainty twice under a figure that looks harder than it
    is.

A NOTE ON THE 2012 "EMD UPDATE", because it gets cited everywhere including by tools like this
one. A search of the Wayback CDX index of Google's official webmaster blog across September and
October 2012 returns NO post announcing it. The update is documented only by third-party SEO
press relaying a tweet. What IS documented, and current, is the exact-match-domain system listed
among Google's active ranking systems: it exists to "ensure we don't give too much credit for
content hosted under domains designed to exactly match particular queries". So the mechanism is
a CAP on benefit, not a penalty, and it is live today rather than a one-off event in 2012.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from .phonetics import Finding

UA = "nameproof (https://github.com/DylanMerigaud/nameproof)"

# A short embedded list of very high frequency English words. Deliberately small and embedded
# rather than a dependency: `wordfreq` (Apache-2.0) does this far better and is the right
# optional upgrade, but the promise of this tool is that it runs with nothing installed.
# The system dictionary at /usr/share/dict/words is consulted when present, which widens the
# net a lot on macOS and most Linux boxes.
COMMON = {
    "anchor", "beacon", "bridge", "circle", "compass", "corner", "delta", "echo", "field",
    "forge", "garden", "harbor", "harbour", "hunter", "island", "keystone", "lantern", "ledger",
    "lever", "marker", "meridian", "mirror", "north", "orbit", "pillar", "pilot", "pivot",
    "prism", "quill", "ranger", "ripple", "river", "sentry", "signal", "signet", "spark",
    "sphere", "spring", "stack", "summit", "tally", "tempo", "tenet", "thread", "threshold",
    "tiller", "torch", "vertex", "vessel", "warden", "watch", "wave", "willow",
}

SYSTEM_DICT = "/usr/share/dict/words"
_system_words = None


def _load_system_dict():
    """Words from the OS dictionary, if this machine has one.

    Absence is not failure: the check degrades to the embedded list and says so, rather than
    silently reporting a clean name because it had nothing to compare against.
    """
    global _system_words
    if _system_words is not None:
        return _system_words
    words = set()
    if os.path.isfile(SYSTEM_DICT):
        try:
            with open(SYSTEM_DICT, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    w = line.strip().lower()
                    if 3 <= len(w) <= 20:
                        words.add(w)
        except OSError:
            pass
    _system_words = words
    return words


def has_system_dict():
    """Whether this machine widened the net beyond the embedded 52-word list.

    Exposed because a caller reporting a SHARE rather than a single verdict has to disclose it:
    "8% of this market are real words" means something very different when the only dictionary
    available holds 52 entries. `corpus.py` prints the caveat on the strength of this.
    """
    return bool(_load_system_dict())


def is_real_word(word):
    """Is this one token an ordinary English word? The shared primitive.

    Split out of `dictionary_word` below so `corpus.py` can measure the real-word share of a
    market without duplicating the lookup, the fallback, or the definition of "ordinary". One
    dictionary, one answer, both callers.
    """
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return False
    return w in COMMON or w in _load_system_dict()


def dictionary_word(name):
    """Is the bare name an ordinary English word? The heaviest SEO finding there is."""
    w = re.sub(r"[^a-z]", "", name.lower())
    if not w:
        return []
    sysd = _load_system_dict()
    hit = is_real_word(w)
    if not hit:
        return []
    where = "the system dictionary" if w in sysd else "the built-in common-word list"
    return [Finding(
        "DICTIONARY_WORD", 3,
        "'{}' is an ordinary English word ({}). Google's Site names guidance says a generic "
        "name 'is unlikely to be selected by our system as a site name, unless that's an "
        "extremely well-recognized brand name', which is a loop a new company starts inside. "
        "You will also compete with the word's own meaning on every search.".format(w, where))]


def keyword_in_name(name, keywords):
    """A category keyword buys nothing, and costs distinctiveness. Informational, weight 1."""
    w = name.lower()
    hits = [k for k in keywords if k.lower() in w]
    if not hits:
        return []
    return [Finding(
        "CATEGORY_KEYWORD", 1,
        "contains {}. Per Google's SEO Starter Guide, 'the keywords in the name of the domain "
        "(or URL path) alone have hardly any effect beyond appearing in breadcrumbs', so this "
        "buys no ranking. It does spend your distinctiveness, and it boxes the product into one "
        "category you may want to grow out of.".format(", ".join(repr(h) for h in hits)))]


def brand_collision(name, timeout=15):
    """Does a notable entity already carry this name? Wikidata, no key, no signup.

    Verified working against the live API. The instructive example is `Anchor`: the search
    returns the object, the news presenter, the Alaskan city, AND Q62533715, the podcast
    platform now called Spotify for Creators. Four different things a searcher could mean.
    """
    url = ("https://www.wikidata.org/w/api.php?action=wbsearchentities&search={}"
           "&language=en&format=json&limit=8".format(urllib.parse.quote(name)))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except Exception:                                        # noqa: BLE001
        return [Finding("COLLISION_UNKNOWN", 0,
                        "Wikidata lookup failed; brand collision not checked. Not a pass.")]
    hits = [h for h in data.get("search", [])
            if h.get("label", "").lower() == name.lower()]
    if not hits:
        return []
    labels = ["{} ({})".format(h.get("label"), (h.get("description") or "no description")[:44])
              for h in hits[:4]]
    weight = 3 if len(hits) >= 3 else 2
    return [Finding(
        "BRAND_COLLISION", weight,
        "{} notable entit{} on Wikidata already carry this exact name: {}. Every one of them "
        "competes with you for your own brand search.".format(
            len(hits), "y" if len(hits) == 1 else "ies", "; ".join(labels)))]


def analyse(name, keywords=(), online=True):
    out = dictionary_word(name)
    if keywords:
        out += keyword_in_name(name, keywords)
    if online:
        out += brand_collision(name)
    return sorted(out, key=lambda f: -f.weight)
