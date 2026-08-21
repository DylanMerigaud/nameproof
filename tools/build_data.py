"""Turn the CMU Pronouncing Dictionary and SEC's company list into the small extracts that
`nameproof generate` ships with, so the 3.6 MB raw dictionary never has to live in the repo.

This script is a MAINTAINER tool. It runs once in a while, by hand, and its output is three
files under `nameproof/data/`, committed to the repo. `nameproof generate` never runs this, never
touches the network, and never needs the files this script reads from. That split is the whole
point: the promise in the README is "zero runtime dependencies", not "zero build-time work".

THE PROPER NOUN PROBLEM, and why a second wordlist is load-bearing here. The CMU dict is built
from a broadcast-news speech corpus, so a large share of its 135k entries are surnames and place
names picked up because someone said them on the air (`ditmars`, `gareth`, `sweeney`), not because
they are English words. A phonotactic model or a rare-word miner trained on the raw dictionary
inherits that bias: it overrepresents transliterated foreign clusters, and half the "rare word"
candidates are somebody's last name. The fix used throughout this script is to intersect cmudict
against `/usr/share/dict/words` and only keep an entry if it appears there in LOWERCASE. That
system wordlist capitalizes proper nouns ("Aaron") and leaves common words alone ("anchor"), so
the lowercase-presence test is a cheap, standard-library way to ask "is this a word, not a name".
It is not perfect (a handful of archaic dictionary entries double as surnames, "tubman" among
them, and it survives the filter because Webster's lists it as an old word for a cab driver) but
it is what turns 84999 cmudict entries into a clean 32k-word pool instead of a scrape of surnames.

Requires `/usr/share/dict/words` on the machine running this script (standard on macOS; on
Debian/Ubuntu, `apt-get install wamerican`). Nothing downstream of the generated data files needs
it: it is consulted here, once, and its judgement is baked into what gets committed.
"""
import collections
import json
import os
import re
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "nameproof", "data")

sys.path.insert(0, REPO_ROOT)
from nameproof.seo import COMMON as SEO_COMMON  # noqa: E402

CMUDICT_URL = "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SYSTEM_DICT = "/usr/share/dict/words"
UA = "nameproof-build-data (https://github.com/DylanMerigaud/nameproof)"
# SEC's fair-access policy rejects requests whose User-Agent does not look like
# "organisation contact-email": https://www.sec.gov/os/webmaster-faq#developers . The placeholder
# below is enough to pass that check; swap in a real contact if you run this script often.
SEC_UA = "nameproof-build-data contact@example.com"

CMUDICT_ATTRIBUTION = (
    "Derived from the CMU Pronouncing Dictionary (cmudict.dict), "
    "Copyright (c) 1993-2015 Carnegie Mellon University. Redistributed under CMU's BSD-style "
    "license: redistribution and use in source and binary form are permitted provided the "
    "copyright notice and disclaimer are retained. Full text: "
    "https://github.com/cmusphinx/cmudict/blob/master/LICENSE . This file is a small filtered "
    "extract, not the dictionary itself."
)
SEC_ATTRIBUTION = (
    "Derived from the U.S. Securities and Exchange Commission's company_tickers.json "
    "(https://www.sec.gov/files/company_tickers.json), a work of the U.S. federal government "
    "and public domain in the United States (17 U.S.C. 105). Names are cleaned (legal suffixes "
    "stripped, non-letters removed) and deduplicated; this file is a name list, not the SEC "
    "dataset itself."
)


def _fetch(url, user_agent=UA):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# CMU dict parsing
# ---------------------------------------------------------------------------

def parse_cmudict(text):
    """word -> list of ARPABET phones, primary pronunciation only.

    Twenty-two entries in the dictionary carry a trailing `# place, danish` style comment; split
    it off before tokenising, or those comment words end up in the phone list and get rendered
    as garbage letters later. Entries like `dail(2)` are alternate pronunciations of a word
    already covered by the unparenthesised form, so they are skipped rather than double counted.
    """
    entries = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].rstrip()
        if not line:
            continue
        parts = line.split()
        if not parts:
            continue
        word = parts[0]
        if "(" in word:
            continue
        phones = parts[1:]
        if not phones:
            continue
        entries[word] = phones
    return entries


def load_lower_common(path=SYSTEM_DICT):
    """Words that appear lowercase in the system dictionary: the "not a proper noun" signal.

    A word that ONLY appears capitalized ("Aaron") is a name. A word that appears lowercase
    ("anchor", and as it happens "tubman", an archaic word for a cab driver) reads as ordinary
    vocabulary to whatever compiled this list, which is the property we want.
    """
    if not os.path.isfile(path):
        raise SystemExit(
            "{} not found. This script needs a system word list to separate ordinary English "
            "words from the surnames and place names that fill up the CMU dictionary. On "
            "macOS it ships by default; on Debian/Ubuntu install it with "
            "`apt-get install wamerican`.".format(path))
    lower = set()
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            w = line.strip()
            if w and w[0].islower():
                lower.add(w.lower())
    return lower


VOWELS_ARPABET = set("AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW".split())


def is_vowel_phone(phone):
    return re.sub(r"[0-9]", "", phone) in VOWELS_ARPABET


def strip_stress(phone):
    return re.sub(r"[0-9]", "", phone)


# ---------------------------------------------------------------------------
# 1. Phonotactics: attested onset and coda phoneme clusters, with frequency
# ---------------------------------------------------------------------------

# ARPABET consonant phone to the spelling nameproof renders it as. Chosen for the common case,
# not for accuracy on every borrowed word: this is a name generator, not a transcription tool.
CONSONANT_GRAPH = {
    "B": "b", "CH": "ch", "D": "d", "DH": "th", "F": "f", "G": "g",
    "HH": "h", "JH": "j", "K": "k", "L": "l", "M": "m", "N": "n",
    "NG": "ng", "P": "p", "R": "r", "S": "s", "SH": "sh", "T": "t",
    "TH": "th", "V": "v", "W": "w", "Y": "y", "Z": "z", "ZH": "zh",
}


def render_cluster(phones):
    return "".join(CONSONANT_GRAPH.get(p, p.lower()) for p in phones)


def derive_phone_clusters(pool, min_count=15, max_phones=2):
    """Attested word-initial (onset) and word-final (coda) consonant clusters, at the PHONEME
    level, each with how many words in the pool carry it.

    Doing this on letters instead of phonemes is the mistake that produces charabia: `ph` is one
    sound, `kn` is a silent letter followed by one sound, and a letter-level scanner treats both
    as two-consonant clusters that do not behave like one. Scanning phones avoids that entirely.

    `min_count` is a frequency floor, not a whitelist: a one-off cluster dragged in by a single
    odd word (there will always be one) should not become 1-in-N in the generator's output just
    because it happened to survive the proper-noun filter.
    """
    onset_counter = collections.Counter()
    coda_counter = collections.Counter()
    for phones in pool.values():
        phones = [strip_stress(p) for p in phones]
        vowel_positions = [i for i, p in enumerate(phones) if p in VOWELS_ARPABET]
        if not vowel_positions:
            continue
        onset = tuple(phones[:vowel_positions[0]])
        coda = tuple(phones[vowel_positions[-1] + 1:])
        if len(onset) <= max_phones:
            onset_counter[onset] += 1
        if len(coda) <= max_phones:
            coda_counter[coda] += 1
    onsets = [(render_cluster(o), len(o), c) for o, c in onset_counter.items() if c >= min_count]
    codas = [(render_cluster(o), len(o), c) for o, c in coda_counter.items() if c >= min_count]
    onsets.sort(key=lambda t: (-t[2], t[0]))
    codas.sort(key=lambda t: (-t[2], t[0]))
    return onsets, codas


# ---------------------------------------------------------------------------
# 2. Rare but pronounceable words
# ---------------------------------------------------------------------------

# Function words and other extremely high frequency words. Length already does most of the work
# (nearly every function word is under six letters) but a few sneak past it ("because", "people").
ULTRA_COMMON = """
the be to of and a in that have i it for not on with he as you do at this but his by from they
we say her she or an will my one all would there their what so up out if about who get which go
me when make can like time no just him know take people into year your good some could them see
other than then now look only come its over think also back after use two how our work first
well way even new want because any these give day most us
""".split()

# Inflected endings drop a word out of the "sounds like a coined name" register even when the
# root passes every other filter: "polluted" and "starred" are real, rare-enough, pronounceable
# words, and neither reads as a name. Cutting them is a judgement call this file owns, separate
# from the proper-noun and frequency filters above it.
NAME_UNLIKE_SUFFIXES = ("ing", "ed", "ly", "ness", "tion", "sion")


def mine_rare_words(pool, min_len=6, max_len=9, max_syllables=3):
    out = []
    ultra = set(ULTRA_COMMON) | {w.lower() for w in SEO_COMMON}
    for word, phones in pool.items():
        w = word.lower()
        if not (min_len <= len(w) <= max_len):
            continue
        if w in ultra:
            continue
        if any(w.endswith(s) for s in NAME_UNLIKE_SUFFIXES):
            continue
        if sum(1 for p in phones if is_vowel_phone(p)) > max_syllables:
            continue
        out.append(w)
    return sorted(set(out))


# ---------------------------------------------------------------------------
# 3. SEC company names, cleaned, for the Markov chain
# ---------------------------------------------------------------------------

LEGAL_SUFFIX_RE = re.compile(
    r"[,.]?\s*(INC|CORP|CORPORATION|CO|LLC|LTD|LTD\.|LP|PLC|GROUP|HOLDINGS?|"
    r"COMPANY|TRUST|FUND|N\.?A\.?|SA|AG|NV|SE)\.?$", re.IGNORECASE)


def clean_company_name(name):
    """Strip legal suffixes (repeatedly: "X Holdings Corp" sheds two) and non-letters, so the
    Markov chain trains on the brandable part of the name instead of learning that half of
    corporate America ends in "Inc"."""
    prev, n = None, name.upper()
    while prev != n:
        prev = n
        n = LEGAL_SUFFIX_RE.sub("", n).strip()
    n = re.sub(r"[^A-Z ]", "", n)
    return re.sub(r"\s+", "", n)


def clean_company_names(tickers_json):
    data = json.loads(tickers_json)
    titles = [v["title"] for v in data.values()]
    cleaned = (clean_company_name(t) for t in titles)
    kept = {c for c in cleaned if 4 <= len(c) <= 12}
    return sorted(kept)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cmudict-file", help="local cmudict.dict, skip the download")
    p.add_argument("--sec-file", help="local company_tickers.json, skip the download")
    args = p.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    print("loading cmudict...")
    if args.cmudict_file:
        cmudict_text = open(args.cmudict_file, encoding="utf-8").read()
    else:
        cmudict_text = _fetch(CMUDICT_URL)
    cmu = parse_cmudict(cmudict_text)
    print("  {} entries".format(len(cmu)))

    print("loading {} to separate words from names...".format(SYSTEM_DICT))
    lower_common = load_lower_common()
    pool = {w: p for w, p in cmu.items() if w.isalpha() and w.lower() in lower_common}
    print("  {} of {} alphabetic entries are ordinary words, not names".format(
        len(pool), sum(1 for w in cmu if w.isalpha())))

    print("deriving phonotactics...")
    onsets, codas = derive_phone_clusters(pool)
    phonotactics = {
        "_attribution": CMUDICT_ATTRIBUTION,
        "onsets": onsets,
        "codas": codas,
    }
    out_path = os.path.join(DATA_DIR, "phonotactics.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(phonotactics, fh, indent=None, separators=(",", ":"))
    print("  {} onset clusters, {} coda clusters -> {} ({:.1f} KB)".format(
        len(onsets), len(codas), out_path, os.path.getsize(out_path) / 1024))

    print("mining rare words...")
    rare = mine_rare_words(pool)
    out_path = os.path.join(DATA_DIR, "rare_words.txt")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("# " + CMUDICT_ATTRIBUTION + "\n")
        fh.write("# One word per line: 6-9 letters, 3 syllables max, filtered against a system\n")
        fh.write("# wordlist to drop proper nouns. See tools/build_data.py.\n")
        for w in rare:
            fh.write(w + "\n")
    print("  {} words -> {} ({:.1f} KB)".format(len(rare), out_path, os.path.getsize(out_path) / 1024))

    print("loading SEC company tickers...")
    if args.sec_file:
        sec_text = open(args.sec_file, encoding="utf-8").read()
    else:
        sec_text = _fetch(SEC_TICKERS_URL, user_agent=SEC_UA)
    names = clean_company_names(sec_text)
    out_path = os.path.join(DATA_DIR, "company_names.txt")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("# " + SEC_ATTRIBUTION + "\n")
        for n in names:
            fh.write(n + "\n")
    print("  {} names -> {} ({:.1f} KB)".format(len(names), out_path, os.path.getsize(out_path) / 1024))

    total = sum(os.path.getsize(os.path.join(DATA_DIR, f)) for f in os.listdir(DATA_DIR))
    print("\ntotal nameproof/data/ size: {:.1f} KB".format(total / 1024))


if __name__ == "__main__":
    main()
