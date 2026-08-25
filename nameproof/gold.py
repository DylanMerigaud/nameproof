"""`gold`: find a name that stands on its own, not a label for a product already picked.

WHY THIS COMMAND EXISTS, and it exists because of a real refusal, not a feature request. Dylan,
2026-08-24, verbatim: "j'accepte pas ses reponses, cherche deep always. [...] pour moi cest
grosse frustration si on doit rename. si on a un nom golde on pourras le revendre au pire."
Renaming a shipped product is a failure, never a plan B, and the way to make that failure rare is
to keep a small reserve of names that are not tied to any bet: short, pronounceable, wide enough
to survive a pivot, free today. `score`, `check`, `market` and `generate` all judge or produce a
name FOR something. `gold` produces a name for NOTHING in particular, on purpose.

THE MEASUREMENT THAT SHAPES WHICH TECHNIQUES RUN HERE. A pass across four real products
(2026-08-24/25) found that short, real-word GOLD candidates, the `rare` technique's whole
premise, are almost all taken: a dictionary word that is also short and pronounceable has had
decades to get registered. What is still reliably free is the COINED register that carries
meaning without being a real word (the Versiota / renovfin / labprove shape). So `gold` pools
`phonotactic`, `markov` and `roots` and skips `rare` on purpose: running it would spend the
count budget on candidates the earlier measurement already disqualified.

THE ROOT LEXICON IS ITS OWN, embedded here rather than reused from `generate.ROOTS` or a
`--roots` file. `generate.ROOTS` is "generic on purpose" for a single naming session; `GOLD_ROOTS`
below is chosen for a narrower property that module never optimizes for: wide and positive enough
to be reused across a bet nobody has picked yet, never a root that names a category, a vertical
or a mechanism (no "audit", no "pay", no "renew"). `generate.latin_roots` grew an optional
`roots=` dict parameter so this module could hand it a lexicon directly, with no temp file and no
`--roots` flag in the loop.

THE GOLD PROFILE is a gate, not a suggestion, and it is stricter than `generate --score`'s plain
grade cut: 4 to 9 letters, 2 to 3 syllables, the SAME phonetic gates `score` uses for
pronounceability (grade A or B, nothing rougher survives), no digit, no hyphen, and no niche
vertical morpheme. That last one is the reason a GOLD name is allowed to exist independently of a
product: a fragment like "msb" (money service business), "pama" or "clfs" (both compliance-code
shaped, and coincidentally recent bet names in this same portfolio) locks a name into the vertical
it was coined for, which is the opposite of resellable. A GOLD name has to survive a pivot, not
describe today's bet.
"""
import re

from . import generate
from .phonetics import analyse, syllables
from .phonetics import grade as _grade

# Wide, positive, meaning-carrying but not category-naming. Every root here is a real Latin or
# Greek word, same discipline as `generate.ROOTS`, chosen for breadth rather than for any one
# field: a root that already means "audit" or "payment" would tie the output to a vertical,
# which is exactly what a GOLD name is supposed to outlive.
GOLD_ROOTS = {
    "nova": "new (Lat. novus)",
    "vera": "true (Lat. verus)",
    "prax": "practice, doing (Gk. praxis)",
    "norm": "rule, standard (Lat. norma)",
    "flux": "flow, change (Lat. fluxus)",
    "arc": "arch, span (Lat. arcus)",
    "luma": "light (Lat. lumen)",
    "apex": "peak, summit (Lat. apex)",
    "mira": "wonder (Lat. mirus)",
    "sana": "health, sound (Lat. sanus)",
    "forma": "shape, form (Lat. forma)",
    "sonus": "sound (Lat. sonus)",
    "omni": "all, every (Lat. omnis)",
    "vela": "swift motion, sail (Lat. velum)",
    "orbis": "world, circle (Lat. orbis)",
    "clara": "clear, bright (Lat. clarus)",
    "axia": "worth, value (Gk. axios)",
    "vigil": "watchful, alert (Lat. vigil)",
    "plexus": "woven, connected (Lat. plexus)",
    "corda": "heart, core (Lat. cor/cordis)",
}

# Fragments that lock a name to one vertical rather than leaving it resellable. `msb` (money
# service business), `pama` and `clfs` are the three named in the request that started this
# module, and they are not hypothetical: they are morphemes from other bets in this same
# portfolio (msbrenew, pamawatch). A GOLD name sharing one reads as bought FOR that bet, which
# defeats the entire point of a name kept independent of one. Matched as a lowercase substring,
# so it also catches a niche fragment landing mid-word through a root+suffix seam.
NICHE_MORPHEMES = ("msb", "pama", "clfs")

MIN_SYLLABLES = 2
MAX_SYLLABLES = 3


def gold_roots(n=20, seed=42):
    """`latin_roots`, pointed at the embedded GOLD lexicon instead of the generic built-in one
    or a `--roots` file. Same call shape as every other entry in `TECHNIQUES` below (`n`, `seed`)
    so the CLI can pool all three without a special case for this one."""
    return generate.latin_roots(n=n, seed=seed, roots=GOLD_ROOTS)


# Deliberately three, not four: `rare` is excluded on purpose, see the module docstring. Sorted
# by the CLI when it iterates, same reason `generate.TECHNIQUES` is sorted before use: a stable
# label order regardless of dict ordering.
TECHNIQUES = {
    "phonotactic": generate.phonotactic,
    "markov": generate.markov_chain,
    "roots": gold_roots,
}


def passes_profile(name, min_length=4, max_length=9):
    """The GOLD gate: everything a candidate has to clear before it is even shown, not just a
    ranking signal. Returns a bool; the caller still runs `phonetics.analyse` itself for the
    grade and findings it prints, this function only decides who gets that far.
    """
    letters = re.sub(r"[^a-z]", "", name.lower())
    if not (min_length <= len(letters) <= max_length):
        return False
    if re.search(r"\d", name) or "-" in name:
        return False
    if any(m in letters for m in NICHE_MORPHEMES):
        return False
    if not (MIN_SYLLABLES <= syllables(name) <= MAX_SYLLABLES):
        return False
    grade, _ = _grade(analyse(name))
    if grade not in ("A", "B"):
        return False
    return True
