"""Does the name mean something you cannot put on an invoice?

WHY THIS MODULE EXISTS, and it is a real miss rather than a feature idea. Dylan, 2026-08-25, on
searching a candidate this tool had helped produce: "ca c'etait vraiment un no go, ajoute un gate
que les premiers resultat de la search ne doivent pas etre du NSFW." The name scored clean, was
available, and its search results were pornography. Every check in this repository looked at how
a name SPELLS, SOUNDS and RANKS. Not one looked at what it MEANS.

THE MECHANISM THAT LET IT THROUGH IS WORSE THAN THE MISSING CHECK, and it was measured here on
2026-08-25 before writing a line of this module. Google's autocomplete endpoint, the one
`search.py` reads, SUPPRESSES adult terms outright:

    ripgrep      15 suggestions
    creampie      0 suggestions
    bukkake       0 suggestions
    fleshlight    0 suggestions

And `search.hijack` reads zero suggestions as "the normal state of a name nobody has used yet,
nothing to conclude either way", which is correct for a fresh coinage and exactly backwards for a
pornographic term. The two cases are indistinguishable from that endpoint. So the worst possible
name and the best possible name produced the SAME clean output, and the tool said nothing.

WHY THIS DOES NOT READ THE RESULTS PAGE, since that is literally what was asked. It cannot, and
both doors were tried on 2026-08-25 rather than assumed shut. `google.com/search` answers 200
with a JavaScript shell and no result text for a non-browser client, which `search.py` already
documents. DuckDuckGo's `html.` and `lite.` endpoints now answer 202 with an anti-bot challenge
page and no results. Driving a real browser would fix both and would break the zero-dependency
promise. So the question "will the first results be NSFW" is answered from what the name MEANS
instead of from what a scraper can see, which is the more durable signal anyway: a term is not
pornographic because of today's ranking, it is pornographic because of what it denotes.

TWO LAYERS, AND ONLY ONE OF THEM IS A GATE.

  `connotation()` is OFFLINE, runs on every candidate, and is a HARD GATE. It has to be offline
  because `gold` and `generate` produce hundreds of candidates and a network call per candidate
  is not a filter, it is a rate limit. It is a fragment list, deliberately partial, and partial
  is stated rather than implied.

  `sense_labels()` is ONLINE, runs on finalists, and is sourced. It reads Wiktionary's own usage
  labels out of the page wikitext, so the verdict cites a dictionary rather than this file's
  opinion. It catches what the fragment list cannot: an ordinary-looking word whose dominant
  sense is sexual.

THE CALIBRATION THAT SHAPES `sense_labels`, and it is the reason plain "slang" is not a trigger.
Measured against Wiktionary on 2026-08-25:

    creampie   pornography, slang, vulgar    -> flag
    bareback   sex, slang                     -> flag
    cum        slang, vulgar                  -> flag
    dick       derogatory, offensive, vulgar  -> flag
    stripe     computing, informal, SLANG     -> must NOT flag
    nova       astronomy                      -> must not flag

`stripe` is the negative control and it is not hypothetical: it is one of the most successful
company names in software, and a check that fires on the bare "slang" label would reject it. The
trigger set below is therefore the sexual and abusive labels only.

THE CLASS THIS MODULE CANNOT CATCH, AND IT IS THE ONE THAT STARTED IT. `msbrenew`, a real
candidate from this portfolio, is clean by denotation: no obscene fragment, no Wiktionary entry,
nothing for either layer below to find. Its search results are a pornography site anyway, because
Google's RESULTS PAGE corrects it to `msbreewc`, an adult creator handle two edits away with over
a million followers. Measured 2026-08-25: autocomplete never once produced that handle from that
name, in any of five locales (us, pe, es, fr, mx). It offered "ms renewal" and "msb renov".

DO NOT TRY TO DERIVE THE RESULTS PAGE FROM AUTOCOMPLETE. Dylan, 2026-08-25, killing exactly that
idea while it was being built here: "tu peux pas deriver de l'auto complete ce que la recherche va
trouver. exemple wedpalette." A neighbourhood scan over autocomplete DID surface the handle for
this one string, and that is a coincidence of this string rather than a method: `search.py`
already documents `normfin`, where autocomplete blamed a bioinformatics tool and the results page
blamed a Pokemon. A heuristic built on that inference would manufacture confidence, which is the
one thing this repository refuses to ship.

AND THE RESULTS PAGE CANNOT BE READ FROM HERE. Four doors were tried on 2026-08-25 rather than
assumed shut: `google.com/search` answers 200 with a JavaScript shell, DuckDuckGo's `html.` and
`lite.` endpoints answer 202 with an anti-bot challenge, and Mojeek answers 403. A real browser
reads all of them and is a dependency this package does not take.

SO THIS MODULE DECLARES ITS BLIND SPOT INSTEAD OF COVERING IT. `serp_unchecked()` returns a
weight-0 finding on every name, `score` prints it as a standing footer, and the skill turns it
into a mandatory browser step on every finalist. A blind spot written in a docstring is a blind
spot nobody reads; a blind spot in the output is one the caller has to answer for.

THE SCUNTHORPE PROBLEM IS HANDLED EXPLICITLY, because a fragment matcher that does not handle it
is worse than no matcher. `analytics` contains a fragment; it is also an ordinary English word,
and an ordinary English word carries its own meaning that the fragment does not override. So a
fragment hit is SUPPRESSED when the name is a real word, and kept when the name is coined, which
is precisely the case `gold` and `generate` produce and precisely where the risk lives.
`Analytics` passes. `Analfin` does not.
"""
import json
import re
import urllib.parse
import urllib.request

from . import corpus, seo
from .phonetics import Finding

UA = "nameproof (https://github.com/DylanMerigaud/nameproof)"

WIKTIONARY = ("https://en.wiktionary.org/w/api.php?action=parse&page={page}"
              "&prop=wikitext&format=json&formatversion=2")

# Wiktionary usage labels that make a name unusable on a product. SEXUAL AND ABUSIVE ONLY: the
# bare "slang" and "informal" labels are NOT here, and leaving them out is the whole calibration.
# `stripe` carries "slang"; so do most good short brand names, because a short English word that
# has been around long enough to be a brand has usually picked up a colloquial sense somewhere.
TRIGGER_LABELS = frozenset({
    "vulgar", "obscene", "pornography", "pornographic", "sex", "sexuality", "sexual",
    "ethnic slur", "religious slur", "slur", "offensive", "derogatory", "profanity",
    "swear word", "coarse",
})

# TWO TIERS, and the split is what keeps the gate credible. A gate that blocks `Cultura` on
# `cul`, `Bitewave` on `bite` and `Computix` on `pute` is a gate somebody turns off within a
# week, and a gate nobody runs protects nothing. All three of those were produced by the first
# version of this list on 2026-08-25, which is why there are two lists now.
#
# HARD: fragments with no clean coinage behind them. These BLOCK.
# SOFT: fragments that are also productive inside ordinary morphology. These WARN and never
#       block, because the cost of a false block here is that the whole check gets disabled.
#
# DELIBERATELY PARTIAL, and that is the operating instruction rather than an apology. This list
# cannot be complete in any language and will never catch a collision in a language nobody here
# reads. It exists to make the OBVIOUS failure automatic and blocking, so the judgement left to
# a person is a real one. The skill's connotation screen (Dylan, 2026-08-25) stays mandatory on
# every finalist; this only removes what nobody should have to look at twice.
#
# English and French both, because the skill's rule asks for "lecture involontaire en EN et FR"
# and a name that is clean in one and obscene in the other is the classic expensive mistake.
HARD_FRAGMENTS = (
    "anal", "arse", "asshol", "bdsm", "boob", "bukkak", "butthol", "clit", "cock", "creampie",
    "cunn", "cunt", "dildo", "erotic", "fellat", "femdom", "fetish", "fuck", "gangbang",
    "hentai", "incest", "jerkoff", "milf", "nsfw", "orgasm", "orgy", "penis", "porn", "pussy",
    "queef", "rimjob", "sex", "shemale", "slut", "sperm", "titfuck", "twat",
    "upskirt", "vagin", "viagra", "whore", "xxx",
    # French stems, not French words: a coinage drops the final vowel, so `salope` misses
    # `Salopix` and `foutre` misses `Foutrix`. Each stem below was checked against the system
    # dictionary first, and each returns 0 or 1 ordinary words (`salopian`, itself suppressed).
    "bais", "conass", "connard", "encul", "foutr", "nichon", "salop",
)

# Each one here is annotated with the ordinary word that put it in this tier rather than the
# other. Every annotation is a real false positive this list produced before the split.
SOFT_FRAGMENTS = (
    "bite",    # arbiter, orbiter, bitewing. French for penis.
    "chatte",  # chatter, chatterbox. Fatal for a chat product if it blocked.
    "cul",     # culture, calculus, oculus. Oculus is a real and successful brand.
    "cum",     # cumulative, document, circumference.
    "pute",    # compute, dispute, reputation. Fatal for a devtools name if it blocked.
    "scat",    # scatter, scattergram.
    "semen",   # advertisement, chastisement, affranchisement: the "-isement" ending contains it
               # outright, 75 dictionary words in all. Also Latin for "seed", so this tool's own
               # roots generator can legitimately reach for it. A warning, never a block.
    "squirt",  # ordinary word on its own.
    "zizi",
)


def _hits(name, fragments):
    """Fragments present in the name, after the Scunthorpe suppression.

    THE SUPPRESSION, and the subtlety that makes it correct. An ordinary English word carries
    its own meaning, so a fragment inside it is a coincidence of spelling rather than a reading
    anybody performs: `analytics` is not a risky name. But the suppression must NOT fire when
    the real word IS the fragment, or `anal` suppresses itself, since `anal` is in the
    dictionary too. So a token only suppresses a fragment when it is a real word AND strictly
    longer than the fragment.

    Checked per TOKEN rather than on the whole string, so `Scunthorpe Analytics` is clean while
    `Analfin` is not: a coined token is where the fragment becomes the only thing to read, and
    coined tokens are exactly what `gold` and `generate` produce.
    """
    parts = corpus.tokens(name) or [re.sub(r"[^a-z]", "", name.lower())]
    out = set()
    for token in parts:
        if not token:
            continue
        for f in fragments:
            if f not in token:
                continue
            if seo.is_real_word(token) and len(token) > len(f):
                continue
            out.add(f)
    return sorted(out)


def connotation(name):
    """The offline gate plus the offline warning. Returns findings, heaviest first.

    A HARD hit weighs 5, above every phonetic finding in the tool, because this is not a cost to
    weigh against other costs. A name whose search results are pornography is not a name with a
    drawback, it is a name you cannot use, and a weight that let it rank alongside a
    DOUBLED_LETTER would be lying about the size of the problem.

    A SOFT hit weighs 2 and never blocks. It is a note for the human screen, not a verdict.
    """
    out = []
    hard = _hits(name, HARD_FRAGMENTS)
    if hard:
        out.append(Finding(
            "NSFW_FRAGMENT", 5,
            "contains {}. On a coined name there is no other reading available, so this is "
            "what the name says and what its search results will be about. Not a drawback to "
            "weigh, a name you cannot put on an invoice.".format(
                ", ".join(repr(h) for h in hard))))
    soft = _hits(name, SOFT_FRAGMENTS)
    if soft:
        out.append(Finding(
            "NSFW_NEAR", 2,
            "contains {}, which is obscene in English or French on its own but also sits "
            "inside ordinary words. Not a block, a line for the human connotation screen: read "
            "the name out loud in both languages before shortlisting it.".format(
                ", ".join(repr(h) for h in soft))))
    return out


class _NoEntry(Exception):
    """Wiktionary has no page for this word. NOT a failure, and the distinction is the whole
    reliability of this check: every good coined name is missing from the dictionary, so
    treating a missing page as "could not check" would attach a scary weight-0 warning to
    exactly the names this tool exists to produce."""


def _wikitext(page, timeout=15):
    url = WIKTIONARY.format(page=urllib.parse.quote(page))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    # The API answers HTTP 200 with an error object for a page that does not exist, so the
    # missing case has to be read out of the body rather than off the status line.
    if "error" in data:
        if data["error"].get("code") == "missingtitle":
            raise _NoEntry(page)
        raise ValueError(data["error"].get("code", "wiktionary error"))
    return data["parse"]["wikitext"]


def labels_for(name, timeout=15):
    """Wiktionary's own usage labels for this word, or None if it has no entry or did not answer.

    Read out of the page WIKITEXT and not out of the REST definition endpoint, because the REST
    endpoint returns the label span EMPTY: `usage-label-sense` arrives as an unexpanded
    transclusion with no content, so the one field worth having is the one it drops. The
    wikitext carries `{{lb|en|vulgar|slang}}` intact.

    Case matters and costs one extra request at most: `milf` has no entry, `MILF` does. A lookup
    that only tried the lowercase form reported the single most predictable collision in this
    whole list as clean.
    """
    seen = set()
    found = None
    missing = 0
    pages = [name.lower(), name.upper(), name.capitalize()]
    for page in pages:
        if page in seen:
            continue
        seen.add(page)
        try:
            text = _wikitext(page, timeout)
        except _NoEntry:
            missing += 1
            continue
        except Exception:                                    # noqa: BLE001
            continue
        out = set()
        for m in re.finditer(r"\{\{(?:lb|label|lbl)\|en\|([^}]*)\}\}", text):
            for part in m.group(1).split("|"):
                part = part.strip().lower()
                if part and not part.startswith("_"):
                    out.add(part)
        found = out if found is None else (found | out)
        if out & TRIGGER_LABELS:
            break
    if found is None and missing == len(seen):
        # Every case variant came back missing, which is a real answer: this word is not in the
        # dictionary, so it has no sense that could be obscene. Clean, not unknown.
        return set()
    return found


def sense_labels(name, timeout=15):
    """The online check, sourced to Wiktionary. Findings, weight 5 on a trigger.

    A word with no Wiktionary entry is the NORMAL state of a good coined name and returns
    nothing, not a pass and not a failure. A lookup that fails outright returns a weight-0
    finding saying so, same contract as `search.py` and `seo.py`: a check that did not run is
    never folded into a clean result.
    """
    labels = labels_for(name, timeout)
    if labels is None:
        return [Finding("CONNOTATION_UNKNOWN", 0,
                        "Wiktionary did not answer; the meaning of this name was not checked. "
                        "This is not a pass.")]
    if not labels:
        return []
    hits = sorted(labels & TRIGGER_LABELS)
    if not hits:
        return []
    return [Finding(
        "NSFW_SENSE", 5,
        "Wiktionary labels this word {}. That is what a searcher gets, whatever you intend it "
        "to mean, and it is the whole first page rather than a footnote.".format(
            ", ".join(hits)))]


def serp_unchecked(name=None):
    """The dimension this package structurally cannot measure, as a finding rather than prose.

    Weight 0, so it never moves a grade: an unverified dimension is not a defect, and the same
    contract already governs `SEARCH_UNKNOWN` and `COLLISION_UNKNOWN`. What it does is make the
    gap impossible to mistake for a clean result, which is precisely how `msbrenew` reached a
    shortlist: every check that ran said fine, and the check that mattered was never run.
    """
    return [Finding(
        "SERP_UNCHECKED", 0,
        "what a real search actually returns for this name has NOT been checked, and cannot be "
        "from here: autocomplete does not predict the results page (wedpalette, normfin, "
        "msbrenew) and no results page is readable without a browser. Open the name in one "
        "before shortlisting it, with SafeSearch off, and look at what the first results are.")]


def analyse(name, online=True, timeout=15):
    """Both layers. Offline always, Wiktionary only when the caller allows the network."""
    out = connotation(name)
    if online:
        out = out + sense_labels(name, timeout)
    return sorted(out, key=lambda f: -f.weight)


def is_blocked(name):
    """The GATE, as a bool, offline only, and HARD hits only.

    Separate from `connotation` returning findings because a gate and a report are different
    jobs: `gold.passes_profile` needs a yes or no on hundreds of candidates and must never make
    a network call to get it, while `score` needs the reason printed.

    Reading `connotation()` truthiness instead would fold the SOFT tier into the gate and block
    `Cultura`, `Bitewave` and `Chattera`, which is the exact failure the two tiers exist to
    avoid. The warning is for a person to read; only the hard tier stops a name.

    RESIDUAL FALSE POSITIVE, stated because it is real and not fixable here: a proper noun that
    is not in the system dictionary gets no suppression, so `Scunthorpe` and the surname
    `Semenza` are blocked. Separating those needs a gazetteer of place and family names, which
    is a bigger data dependency than the problem deserves. For a tool whose job is judging
    COINED product names, blocking a coinage that contains the fragment is the right side to
    err on, and a person who genuinely wants to name a product after that town can see the
    finding and overrule it.
    """
    return bool(_hits(name, HARD_FRAGMENTS))
