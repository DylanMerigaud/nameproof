"""Will Google send people somewhere else when they type your name?

THE FAILURE MODE THIS MODULE EXISTS FOR, and it is invisible to every other naming tool. A real
product was named `wedpalette`. Ask Google for it and every single suggestion comes back as
"web palette": web palette generator, web palette colors, web design color palette. Fifteen
suggestions, not one of them the actual brand. The name was available, it scored fine on
phonetics, and Google quietly redirects its entire search demand to something else.

Availability checkers cannot see this. Phonetic rules cannot see this. It is a fact about the
index, so it has to be measured against the index.

THE MEASURE. Google's autocomplete endpoint, with `client=chrome`, applies spelling correction.
Feed it a name and count how many of the suggestions actually contain that name. A healthy brand
owns its own suggestion list. A hijacked one does not appear at all.

  wedpalette   0 of 15 suggestions contain it   -> Google offers "web palette"
  recieve      0 of 15                          -> the control, Google offers "receive"
  rectia       0 of 10                          -> Google offers "certiadulto"

This is an UNDOCUMENTED endpoint. It is free, needs no key, and is what every browser address
bar uses, but Google does not promise it and can change or block it. So the module degrades
honestly: a failed lookup returns a finding of weight 0 that says the check did not run, never
an empty list that would read as a pass. And `nameproof` keeps an offline fallback in
`near_miss` for exactly this reason.

THE SAME NUMBER MEANS TWO OPPOSITE THINGS, AND THIS IS THE TRAP. A high share of suggestions
that keep your spelling looks like health. It is health only if the entity behind those
suggestions is YOU. The pattern is identical either way:

  drata login, drata glassdoor, drata trust center      Drata owns the string
  normix medication, normix 200 mg, normix antibiotic   an ANTIBIOTIC owns the string
  tutify login, tutify academy, tutify math             a TUTORING SERVICE owns the string

Same shape, opposite conclusion. So `hijack()` takes `launched`: while you are still choosing a
name, a high ratio is reported as STRING_OCCUPIED and weighs 3, because you would be arriving
into somebody else's results. Once you run the name, a high ratio is the goal.

What an unlaunched name actually wants is a VACUUM: few suggestions, and those few pointing at
nothing with real demand. That is where Drata started.

DOES A HIJACKED NAME EVENTUALLY WIN? Sometimes, and much less often than founders hope. Two
real companies measured on 2026-08-21 answer it better than any argument:

  drata   12 of 15 suggestions are the company: drata login, drata glassdoor, drata trust
          center, drata layoffs, drata ipo, drata ceo, drata vs vanta. The Pokemon `dratini`
          sits at position 4 and loses. So yes, a coined name can own a list.

  vanta    2 of 15. The rest are vantage, vantage west, vantablack, vantaca, vantage data
          centers. This is a company with hundreds of millions raised and a very large brand
          budget, and it still does not own its own name.

The difference is not company size, it is what the string competes with. Nobody was searching
`drata` before Drata existed, so the company filled an empty string rather than displacing
anything. `vanta` is the prefix of `vantage`, a word with permanent search demand that no
marketing budget can outbid.

READ THAT AS A RULE: a hijacked name does not get fixed by blog posts and age when the thing
hijacking it has its own standing demand. It gets fixed when there was nothing there to begin
with, which is the case where it was barely hijacked at all. If Vanta cannot displace `vantage`,
a solo will not displace a franchise or a common word.

Which is why the ratio matters more than the pass or fail. A name at 14 of 15 today needs to win
nothing; a name at 0 of 15 is asking you to fund a displacement campaign as your first act.

TWO MECHANISMS, AND THIS MODULE ONLY SEES ONE. Google corrects a query in two different
places, and they do not agree:

  1. AUTOCOMPLETE, while you type. This is what the module measures.
  2. THE RESULTS PAGE, after you press enter, which says "These are results for X, search
     instead for Y" and silently swaps your query.

Measured on `normfin` on 2026-08-21, the two disagreed completely. Autocomplete offered
`normfinder`, a bioinformatics tool. The results page corrected to `Normifin`, a Pokemon, and
returned dolphin encyclopedia pages. Same name, two different hijackers, and only the first is
visible from here.

The verdict was the same either way, which is the useful part: zero of fifteen suggestions kept
the spelling, and the results page refused the spelling outright. When autocomplete does not
recognise a name, the results page usually will not either. But the module NAMES the culprit it
can see, and that name can be the wrong one. Read the finding as "Google does not think this
string is a thing", not as "this specific competitor will take your traffic".

Fetching the results page directly was tried and does not work: google.com/search answers 200
with a JavaScript shell and no result text for a non-browser client. Driving a real browser
would fix it and would also make this an entirely different kind of tool, one with a headless
Chrome dependency, which the zero-dependency promise rules out. The limitation is documented
rather than hidden.

A NOTE ON WHAT A LOW SCORE MEANS FOR A BRAND-NEW NAME. A coined name nobody has used yet may
legitimately return nothing at all, which is different from being hijacked. Empty results are
reported as UNKNOWN, not as failure: silence is the normal state of a name that does not exist
yet, and punishing it would punish every good coined name.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from .phonetics import Finding

# gl and hl are NOT optional, and leaving them out was a real measurement bug caught on
# 2026-08-21. Run from Lima, the endpoint answered with Peruvian government services: `probia`
# suggested "provias nacional", `rectia` suggested "certiadulto". Forced to the US it answers
# "probiotics" instead, which is a completely different verdict about a name aimed at American
# buyers. THE MARKET YOU SELL TO IS THE MARKET YOU MUST QUERY, and the endpoint silently uses
# the caller's location unless told otherwise.
SUGGEST = ("https://suggestqueries.google.com/complete/search"
           "?client=chrome&gl={gl}&hl={hl}&q={q}")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def suggestions(name, timeout=15, gl="us", hl="en"):
    """Raw suggestion list, or None if the endpoint did not answer.

    `gl` is the country to ask as. Default US because that is where the tool's users mostly
    sell; change it if your buyer is elsewhere. It changes the answer completely, not slightly.
    """
    url = SUGGEST.format(gl=gl, hl=hl, q=urllib.parse.quote(name))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
        data = json.loads(raw)
    except Exception:                                        # noqa: BLE001
        return None
    if not isinstance(data, list) or len(data) < 2:
        return None
    return [s for s in data[1] if isinstance(s, str)]


def hijack(name, timeout=15, gl="us", hl="en", launched=False):
    """Does Google keep your name, replace it, or hand it to somebody else?

    `launched` flips the reading of a HIGH ratio, and nothing else. Set it True to
    audit a name you already run, where owning your suggestion list is the goal. Leave
    it False while choosing a name, where a string somebody else already owns is the
    thing you are trying to avoid."""
    sug = suggestions(name, timeout, gl, hl)
    if sug is None:
        return [Finding("SEARCH_UNKNOWN", 0,
                        "Google suggest did not answer; search hijack not checked. "
                        "This is not a pass.")]
    if not sug:
        # Normal for a freshly coined name. Reporting it as a problem would penalise exactly
        # the kind of name the rest of the tool is trying to find.
        return [Finding("SEARCH_UNKNOWN", 0,
                        "Google returns no suggestions at all, which is the normal state of a "
                        "name nobody has used yet. Nothing to conclude either way.")]
    # WHOLE WORD, not substring, and the difference is the whole check. The first version asked
    # `name in suggestion`, which passes `normfin` on `normfinder` and reports a clean name.
    # NormFinder is an established bioinformatics tool with an R package and a download page, so
    # every search for the brand would have landed there, and the tool said it was fine.
    # Caught 2026-08-21 on a name this repo had itself recommended.
    low = name.lower()
    whole = re.compile(r"(?<![a-z]){}(?![a-z])".format(re.escape(low)))
    kept = [s for s in sug if whole.search(s.lower())]
    ratio = len(kept) / len(sug)
    if ratio >= 0.5:
        # HIGH IS NOT GOOD FOR A NAME YOU HAVE NOT LAUNCHED, and reading it as good was this
        # module's worst bug. `drata login`, `drata glassdoor`, `drata trust center`: that
        # pattern, name plus qualifier, means an ENTITY OWNS THE STRING. For Drata the entity is
        # Drata, which is why it looks like success. For a name you are still choosing, the
        # entity is somebody else.
        #
        # Caught 2026-08-21 on four names this tool had just recommended. Every one came back
        # above 50 percent and every one was already taken: `normix` is an antibiotic (normix
        # medication, normix 200 mg), `aptura` is a company (aptura group, aptura careers),
        # `nomio` is a drink, `tutify` is a tutoring service. The metric was right and the
        # reading was inverted.
        #
        # So the same measurement now returns opposite verdicts depending on `launched`.
        if launched:
            return []
        return [Finding(
            "STRING_OCCUPIED", 3,
            "{} of {} suggestions are this exact word plus a qualifier ({}), which is the "
            "signature of an entity that already owns the string. For a name you have not "
            "launched, that entity is not you: you would be arriving into somebody else's "
            "search results.".format(len(kept), len(sug), "; ".join(repr(k) for k in kept[:3]))
        )]
    # Same whole-word test as `kept`, and fixing only one of the two was its own bug: the
    # culprit list stayed on substring matching, so it came back EMPTY exactly when the hijack
    # was by a longer word (probero -> proberos, intego -> identogo). The message then said a
    # name was hijacked and named nobody, which is the least useful possible output for the
    # most important case.
    others = [s for s in sug if not whole.search(s.lower())][:3]
    weight = 3 if ratio == 0 else 2
    return [Finding(
        "SEARCH_HIJACK", weight,
        "{} of {} Google suggestions keep this spelling. Google steers typers toward: "
        "{}. People who hear your name on a call will land on somebody else. (asked as {})".format(
            len(kept), len(sug), "; ".join(repr(o) for o in others), gl.upper())
    )]


def near_miss(name, words):
    """Offline twin of `hijack`: is the name one edit away from two ordinary words?

    This is the mechanism behind the wedpalette case, reproduced without the network.
    `wedpalette` is one substitution from `webpalette`, which splits cleanly into `web` and
    `palette`. Google corrects toward frequent strings, and two common words joined are far more
    frequent than any new coinage, so the correction is close to guaranteed.

    Deliberately strict about what counts as a word: both halves must be at least three
    characters and both must be in the supplied list. Loosening either turns every name into a
    false positive, which is worse than not checking.
    """
    w = "".join(c for c in name.lower() if c.isalpha())
    if len(w) < 6:
        return []
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    variants = {w}
    for i in range(len(w)):
        for c in alphabet:
            if c != w[i]:
                variants.add(w[:i] + c + w[i + 1:])
    for v in sorted(variants):
        for cut in range(3, len(v) - 2):
            left, right = v[:cut], v[cut:]
            if left in words and right in words:
                how = "is" if v == w else "is one letter away from"
                return [Finding(
                    "SPLIT_RISK", 3,
                    "'{}' {} '{} {}', two ordinary words. Google corrects toward frequent "
                    "strings, and a two-word phrase beats a new coinage every time. This is "
                    "the mechanism that sends every search for 'wedpalette' to 'web "
                    "palette'.".format(w, how, left, right))]
    return []
