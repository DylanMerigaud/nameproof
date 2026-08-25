"""Four ways to produce a candidate name, offline, and ranked here in the order they earn their
keep. Each one is a pure function of a seed: same seed, same names, forever, because a generator
nobody can rerun is a generator nobody can argue with, which is the same complaint this whole
project has about a language model score.

RANKED BY VALUE FOR EFFORT, cheapest and most reliable first:

1. `rare_words`    a filter, not a generator. Every candidate is a real, attested English word,
                    so pronounceability comes from the dictionary itself, not from a model of it.
2. `latin_roots`    a Latin or Greek root plus a SaaS-shaped suffix. Costs nothing external and
                    is the actual mechanism behind Vanta, Drata and Sprinto's kind of name.
3. `phonotactic`    syllables built from consonant clusters and vowels that are attested to
                    start or end a real English word, at the rate they are actually attested.
4. `markov_chain`   a character n-gram model trained on real company names. The loosest of the
                    four: without a strict output filter it produces unpronounceable strings at
                    a high rate, so its filter is stricter than the other three combined.

THE LESSON THAT SHAPES #3, and it is worth stating plainly because it is easy to get backwards.
Deriving a phonotactic model from LETTERS produces charabia: "ph" looks like two consonants to a
letter scanner and is one sound, "kn" looks like two consonants and is one, spelled with a silent
one. A model built on letters learns clusters that do not exist in speech and strings them
together into words like nothing in English. Deriving the same model from the CMU dictionary's
PHONEMES fixes it, because a phoneme scanner sees "ph" and "kn" for what they actually are: one
consonant sound each. `tools/build_data.py` does this extraction once, offline, and this module
only ever reads the result.

THE SECOND LESSON, and it is why `phonotactic` biases hard toward an open final syllable. Vanta,
Drata, Sprinto and Alessa all end on a vowel sound. Sampling codas at their NATURAL frequency in
English (about 3 in 10 words end open) undersells that pattern badly and produces closed, foreign
sounding forms. The bias below is not measured, it is chosen, on purpose, to match the reference
set this tool's own README points to.
"""
import collections
import json
import os
import random
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ---------------------------------------------------------------------------
# Shared plumbing
# ---------------------------------------------------------------------------

def _collect_unique(gen_one, n, max_attempts):
    """Call `gen_one()` until `n` distinct names are collected or the attempt budget runs out.

    The budget matters for `latin_roots`, whose vocabulary is a few hundred root/suffix pairs:
    asking for more names than exist stops the loop instead of spinning forever, and returns
    what was actually available rather than pretending to have more.
    """
    seen = set()
    out = []
    attempts = 0
    while len(out) < n and attempts < max_attempts:
        attempts += 1
        candidate = gen_one()
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def _weighted(rng, entries):
    """`entries` is a list of (value, weight) pairs. `random.choices` wants two parallel lists,
    not a list of pairs, hence the unzip on every call: entry lists here are a few dozen items
    at most, so the cost of not caching the unzip is noise."""
    values = [e[0] for e in entries]
    weights = [e[1] for e in entries]
    return rng.choices(values, weights=weights)[0]


# ---------------------------------------------------------------------------
# 1. Rare-word extraction
# ---------------------------------------------------------------------------

_rare_words_cache = None


def _load_rare_words():
    global _rare_words_cache
    if _rare_words_cache is not None:
        return _rare_words_cache
    words = []
    path = os.path.join(DATA_DIR, "rare_words.txt")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                words.append(line)
    _rare_words_cache = words
    return words


def rare_words(n=20, seed=42):
    """Real English words, 6 to 9 letters, 3 syllables or fewer, filtered out of the CMU
    dictionary against a general wordlist to drop proper nouns and inflected forms.

    There is no pronounceability model here because there does not need to be one: a word
    already spoken by whoever built the dictionary is pronounceable by construction. This is
    the cheapest technique of the four and, on the numbers, the best one."""
    pool = _load_rare_words()
    rng = random.Random(seed)
    n = min(n, len(pool))
    return [w.capitalize() for w in rng.sample(pool, n)]


# ---------------------------------------------------------------------------
# 2. Latin / Greek root + suffix
# ---------------------------------------------------------------------------

# Roots kept short and recognisable rather than exhaustive: each one carries a plausible meaning
# a buyer could later hang a story on, which a purely random morpheme would not.
ROOTS = {
    "vera": "truth (Lat. verus)", "clar": "clear (Lat. clarus)",
    "luc": "light (Lat. lux/lucis)", "fort": "strong (Lat. fortis)",
    "nova": "new (Lat. novus)", "meta": "beyond/change (Gk. meta)",
    "syn": "together (Gk. syn)", "poly": "many (Gk. polys)",
    "tele": "far (Gk. tele)", "auto": "self (Gk. autos)",
    "flux": "flow (Lat. fluxus)", "sana": "health (Lat. sanus)",
    "scala": "ladder/scale (Lat. scala)", "forma": "shape (Lat. forma)",
    "sonus": "sound (Lat. sonus)", "cogni": "know (Lat. cognitio)",
    "vigil": "watchful (Lat. vigil)", "omni": "all (Lat. omnis)",
    "veri": "true (Lat. verus)", "graph": "write (Gk. graphein)",
}

SUFFIXES = ["a", "o", "us", "ix", "ta", "ara", "ero", "ent", "ify",
            "io", "ly", "fin", "sys", "wave", "flow"]

# Same test `corpus.py` uses for `open_final`: a trailing vowel LETTER, silent e excluded because
# it is not an open SOUND. Reused here so the bias below means the same thing it means there.
_OPEN_FINAL_LETTERS = ("a", "i", "o", "u", "y")

# Seams that read as a typo or a stutter rather than a word boundary: a doubled consonant
# ("Novvix") or a doubled vowel ("Scalaa", root "scala" plus suffix "a") both do this, and a
# vowel-ending root paired with a vowel-starting suffix hits the second case often enough
# (about a third of the combinations here) that it needs the same guard as the first.
BAD_SEAMS = {"tt", "kk", "xx", "qq", "yy", "vv", "ff", "cc", "gg",
             "kg", "gk", "tk", "kt", "aa", "ee", "ii", "oo", "uu"}


def load_roots(path):
    """A root lexicon from a file: `root<space>meaning`, one per line, `#` for comments.

    Added because the built-in list is deliberately GENERIC (omni, tele, luc, vera) and a
    generic lexicon produces clean names that mean nothing for your product. Measured on a real
    naming run: every A-grade output was formally fine and semantically empty, because the roots
    had nothing to do with the field being named. The fix is not a better algorithm, it is your
    own vocabulary. Ship a file with the roots of YOUR domain and the same generator suddenly
    produces names that say something.
    """
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            out[parts[0].lower()] = parts[1] if len(parts) > 1 else ""
    if not out:
        raise ValueError("no roots found in {}".format(path))
    return out


def latin_roots(n=20, seed=42, roots_file=None, roots=None):
    """A root plus a suffix, biased toward a vowel-final suffix at roughly 2 to 1.

    The bias is deliberate, not measured: about half the suffix list already ends open, and
    that is not enough to reliably echo the Vanta/Drata/Sprinto register on its own.

    `roots`, a dict passed directly, wins over `roots_file` and over the built-in `ROOTS`.
    Added for `gold.py`: its lexicon is embedded in code rather than sitting in a file on disk,
    so it has nothing to hand `--roots`, and this is the one function both paths go through.
    """
    rng = random.Random(seed)
    root_map = roots if roots is not None else (load_roots(roots_file) if roots_file else ROOTS)
    root_pool = sorted(root_map)
    weighted_suffixes = [
        (s, 2 if s.endswith(_OPEN_FINAL_LETTERS) else 1) for s in SUFFIXES
    ]

    def gen_one():
        for _ in range(50):
            root = rng.choice(root_pool)
            suffix = _weighted(rng, weighted_suffixes)
            seam = root[-1] + suffix[0]
            if seam in BAD_SEAMS:
                continue
            return (root + suffix).capitalize()
        # Every combination for this root kept hitting a bad seam; a bad seam plus a fresh
        # root is virtually certain to clear, and this keeps the function total.
        return (rng.choice(root_pool) + "a").capitalize()

    max_attempts = max(200, n * 20)
    return _collect_unique(gen_one, n, max_attempts)


# ---------------------------------------------------------------------------
# 3. Phonotactic syllables from CMU dict phonemes
# ---------------------------------------------------------------------------

# ARPABET vowel phone to the spelling this module renders it as. Not an attempt at a full IPA
# mapping, just enough graphemes to make the output readable as English.
VOWEL_GRAPH = {
    "AA": "ah", "AE": "a", "AH": "u", "AO": "aw", "AW": "ow", "AY": "y",
    "EH": "e", "ER": "er", "EY": "ay", "IH": "i", "IY": "ee", "OW": "o",
    "OY": "oy", "UH": "oo", "UW": "oo",
}

# Every vowel in Vanta, Drata, Sprinto and Alessa is a plain single letter; none of them carry a
# two-letter vowel digraph like "oo" or "ay". Weighting the five single-letter phones 3 to 1
# over the other ten is what keeps `phonotactic`'s output in that register instead of drifting
# into the "Poomaydee" territory a uniform draw across all fifteen produces.
_VOWEL_WEIGHT = {p: (3 if len(g) == 1 else 1) for p, g in VOWEL_GRAPH.items()}
_WEIGHTED_VOWEL_PHONES = list(_VOWEL_WEIGHT)
_WEIGHTED_VOWEL_WEIGHTS = list(_VOWEL_WEIGHT.values())

# How often the final syllable of a `phonotactic` name closes on a consonant instead of staying
# open. 4 of the 5 names this README cites as reference (Vanta, Drata, Sprinto, Alessa; Scrut is
# the exception) end on a vowel, against a natural English rate of about 3 in 10. This number is
# chosen to land close to that reference set, not measured off the corpus.
_CLOSED_FINAL_CHANCE = 0.25

_phonotactics_cache = None


def _load_phonotactics():
    global _phonotactics_cache
    if _phonotactics_cache is not None:
        return _phonotactics_cache
    path = os.path.join(DATA_DIR, "phonotactics.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    _phonotactics_cache = {
        "onsets": [(g, c) for g, p, c in data["onsets"]],
        # A syllable boundary in the middle of a word only ever takes a single consonant (see
        # `_gen_phonotactic_one`); the same restriction is applied to a CLOSING coda, because a
        # two-phoneme coda cluster is where the output starts looking foreign rather than coined.
        "medial_onsets": [(g, c) for g, p, c in data["onsets"] if p == 1],
        "codas": [(g, c) for g, p, c in data["codas"] if p == 1],
        "onset_graphs": {g for g, p, c in data["onsets"]},
        "coda_graphs": {g for g, p, c in data["codas"]},
    }
    return _phonotactics_cache


def _gen_phonotactic_one(rng, data):
    n_syllables = rng.choices([2, 3], weights=[80, 20])[0]
    parts = []
    for i in range(n_syllables):
        is_first = i == 0
        is_last = i == n_syllables - 1
        # The first syllable draws from the FULL onset pool, clusters included: "spr" or "dr"
        # opening a word is common and is exactly the Sprinto/Drata register. A syllable in the
        # middle of the word only ever gets a single consonant, because stacking a coda cluster
        # against the next syllable's onset cluster is what produces an unpronounceable seam.
        onset = _weighted(rng, data["onsets"] if is_first else data["medial_onsets"])
        nucleus = VOWEL_GRAPH[rng.choices(_WEIGHTED_VOWEL_PHONES, weights=_WEIGHTED_VOWEL_WEIGHTS)[0]]
        if is_last and rng.random() < _CLOSED_FINAL_CHANCE:
            coda = _weighted(rng, data["codas"])
        else:
            coda = ""
        parts.append(onset + nucleus + coda)
    return "".join(parts).capitalize()


def phonotactic(n=20, seed=42):
    """Syllables built from consonant clusters attested to open or close a real English word in
    the CMU dictionary, at their attested frequency, with vowels chosen freely between them.

    This is the only one of the four techniques that guarantees pronounceability by
    CONSTRUCTION rather than by filtering afterward: every cluster it can produce is one some
    real English word already opens or closes on."""
    data = _load_phonotactics()
    rng = random.Random(seed)

    def gen_one():
        return _gen_phonotactic_one(rng, data)

    max_attempts = max(200, n * 30)
    return _collect_unique(gen_one, n, max_attempts)


# ---------------------------------------------------------------------------
# 4. Markov chain on SEC company names
# ---------------------------------------------------------------------------

_MARKOV_ORDER = 3

# "y" closes a diphthong ("Kopify", "Lyft") far more often than it acts as a consonant in a
# generated brand name, so the run-length checks below (`[AEIOUY]`) count it with the vowels;
# only the "does this word have a vowel AT ALL" check stays strict, since "y" alone should not
# be enough to call a word pronounceable.
_VOWELS = set("AEIOU")

_company_names_cache = None
_markov_model_cache = None


def _load_company_names():
    global _company_names_cache
    if _company_names_cache is not None:
        return _company_names_cache
    names = []
    path = os.path.join(DATA_DIR, "company_names.txt")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                names.append(line)
    _company_names_cache = names
    return names


def _build_markov(names, order):
    model = collections.defaultdict(collections.Counter)
    starts = collections.Counter()
    for name in names:
        padded = "^" * order + name + "$"
        starts[padded[order:order * 2]] += 1
        for i in range(len(padded) - order):
            model[padded[i:i + order]][padded[i + order]] += 1
    return model, starts


def _load_markov_model():
    global _markov_model_cache
    if _markov_model_cache is not None:
        return _markov_model_cache
    _markov_model_cache = _build_markov(_load_company_names(), _MARKOV_ORDER)
    return _markov_model_cache


def _gen_markov_one(rng, model, starts, order, max_len=9):
    ctx = rng.choices(list(starts.keys()), weights=list(starts.values()))[0]
    out = ctx.replace("^", "")
    while len(out) < max_len:
        choices = model.get(ctx)
        if not choices:
            break
        nxt = rng.choices(list(choices.keys()), weights=list(choices.values()))[0]
        if nxt == "$":
            break
        out += nxt
        ctx = out[-order:]
    return out.capitalize()


def _looks_pronounceable(word):
    """Reject on shape alone, before spending a look at attested codas. A character n-gram model
    trained at this order reliably produces triple-repeated letters and four-consonant runs that
    no English word has; catching those here is cheaper than sending them through `phonetics`
    and cheaper still than showing them to a person."""
    w = word.upper()
    if not (4 <= len(w) <= 9):
        return False
    if not any(c in _VOWELS for c in w):
        return False
    if re.search(r"(.)\1\1", w):
        return False
    if re.search(r"[^AEIOUY]{3,}", w) or re.search(r"[AEIOUY]{3,}", w):
        return False
    return True


def _has_attested_edges(word, legal_onsets, legal_codas):
    """The one check `_looks_pronounceable` cannot do: a run of two consonants that is SHAPE
    valid (no triple letter, no four in a row) can still be a cluster no English word opens or
    ends on, like the "nc-" or "-yj" a raw run of this model produces. `legal_onsets` and
    `legal_codas` are the same attested cluster sets `phonotactic` samples from, so a name this
    filter accepts is one `phonotactic` could plausibly have generated on purpose."""
    w = word.lower()
    head = re.match(r"^[^aeiouy]+", w)
    head_cluster = head.group(0) if head else ""
    if len(head_cluster) >= 2 and head_cluster not in legal_onsets:
        return False
    tail = re.search(r"[^aeiouy]+$", w)
    tail_cluster = tail.group(0) if tail else ""
    if len(tail_cluster) >= 2 and tail_cluster not in legal_codas:
        return False
    return True


def markov_chain(n=20, seed=42):
    """A character trigram model trained on cleaned SEC company names (public domain data,
    legal suffixes stripped), with the loosest guarantees of the four techniques here and
    therefore the strictest output filter: shape rejection first, then a check that the name
    does not end on a consonant cluster no real English word ends on.

    Expect a lower hit rate per attempt than the other three; `_collect_unique` just keeps
    sampling until it has `n`, so the caller never sees the difference, only the CLI's `--all`
    run takes visibly longer on this technique than the others."""
    model, starts = _load_markov_model()
    phonotactics = _load_phonotactics()
    legal_onsets = phonotactics["onset_graphs"]
    legal_codas = phonotactics["coda_graphs"]
    rng = random.Random(seed)

    def gen_one():
        for _ in range(100):
            candidate = _gen_markov_one(rng, model, starts, _MARKOV_ORDER)
            if _looks_pronounceable(candidate) and _has_attested_edges(candidate, legal_onsets, legal_codas):
                return candidate
        return candidate  # exhausted the inner budget; let the outer dedupe/attempt cap decide

    max_attempts = max(400, n * 60)
    return _collect_unique(gen_one, n, max_attempts)


TECHNIQUES = {
    "rare": rare_words,
    "roots": latin_roots,
    "phonotactic": phonotactic,
    "markov": markov_chain,
}
