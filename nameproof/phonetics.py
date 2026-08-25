"""The radio test: can a US English speaker HEAR the name and spell it right?

This is the module the competition does not have. `domainsearcher-app` asks a language model to
score "pronounceability" and returns a number with no reason attached. `tldx` does not score at
all. Both are useful; neither can tell you WHY a name will cost you spellings over the phone.

THE DIRECTION MATTERS AND ALMOST EVERYONE GETS IT BACKWARDS. Most naming advice checks
grapheme to sound: can I read this and say it? That is the easy direction, and it is not where
the money leaks. The expensive direction is sound to grapheme: your prospect hears the name on a
call, then has to type it into a browser. English is famously many-to-one that way. The /k/ sound
alone is spelled c, k, ck, ch and qu, so a name that opens on /k/ is a coin flip every time
somebody says it out loud.

Every rule below is deterministic, explainable, and carries the reason it exists. No model, no
network, no config. A rule you cannot explain to the person choosing the name is a rule that does
not belong in a naming tool.
"""
import re

# Sound to grapheme. The listener hears one sound and has to pick among several spellings.
# `weight` is how much it costs, 0 to 3. The heaviest are the ones that hit the FIRST sound of
# the name, because a wrong first letter means the search does not even autocomplete.
SOUND_TO_SPELLING = [
    # (regex on the lowercased name, sound, the spellings it competes with, weight, where)
    (r"^c[aou]", "/k/", "c, k, ck, qu", 3, "initial"),
    # (?!n) matters: in "knight" the k is SILENT, so there is no /k/ sound to misspell. Without
    # the guard the tool reports a sound the listener never hears, on top of the silent-letter
    # finding that is the real problem. Caught by its own test suite on "Knightly".
    (r"^k(?!n)", "/k/", "c, k, ck, qu", 3, "initial"),
    (r"^qu", "/kw/", "qu, kw, cw", 3, "initial"),
    (r"^ph", "/f/", "f, ph", 3, "initial"),
    (r"^f", "/f/", "f, ph", 2, "initial"),
    (r"^c[eiy]", "/s/", "s, c, ps, sc", 3, "initial"),
    (r"^s[aeiouy]", "/s/", "s, c", 2, "initial"),
    (r"^z", "/z/", "z, s, x", 2, "initial"),
    (r"^j", "/dzh/", "j, g, dg", 2, "initial"),
    (r"^g[eiy]", "/dzh/", "j, g, dg", 3, "initial"),
    (r"^x", "/z/ or /ks/", "x, z, cks", 3, "initial"),
    (r"[^s]ph", "/f/", "f, ph", 2, "inside"),
    (r"ck", "/k/", "c, k, ck", 1, "inside"),
    (r"[aeiou]se\b", "/z/ or /s/", "se, ze, ce", 1, "final"),
]

# Letters that are written and not said. The listener never hears them, so they never type them.
SILENT = [
    (r"^kn", "kn", "the k is silent, listeners write n"),
    (r"^wr", "wr", "the w is silent, listeners write r"),
    (r"^ps", "ps", "the p is silent, listeners write s"),
    (r"^gn", "gn", "the g is silent, listeners write n"),
    (r"^pn", "pn", "the p is silent, listeners write n"),
    (r"^mn", "mn", "the m is silent, listeners write n"),
    (r"mb\b", "mb", "the b is silent, listeners drop it"),
    (r"mn\b", "mn", "the n is silent, listeners drop it"),
    (r"^h[aeiou]", "h", "h is weakly heard, some listeners drop it"),
]

# Vowel teams with more than one common spelling for the same sound. Pure sound to grapheme pain.
VOWEL_TEAMS = [
    (r"ee", "/ee/", "ee, ea, ie, e_e"),
    (r"ea", "/ee/ or /eh/", "ee, ea"),
    (r"ie", "/ee/ or /eye/", "ie, ei, ee, y"),
    (r"ei", "/ee/ or /ay/", "ei, ie, ay"),
    (r"ai", "/ay/", "ai, ay, a_e, ei"),
    (r"ay", "/ay/", "ai, ay, a_e"),
    (r"oo", "/oo/ or /uh/", "oo, ou, u, ew"),
    (r"ou", "/ow/ or /oo/", "ou, ow, oo"),
    (r"ough", "six different sounds", "ough is the worst string in English"),
    (r"au", "/aw/", "au, aw, augh"),
]

# Grapheme to sound: the reader hesitates out loud. Cheaper than the above but still real,
# because a name people mispronounce is a name they avoid saying, which kills word of mouth.
READING_TRAPS = [
    (r"c[eiy]", "c before e, i or y is soft, before a, o, u it is hard", 1),
    (r"g[eiy]", "g before e, i or y may be soft or hard, English is inconsistent here", 2),
    (r"^y[aeiou]", "leading y may read as a consonant or a vowel", 1),
    (r"[aeiou]{3}", "three vowels in a row rarely have one obvious reading", 2),
]

# Onsets English does not allow. A name that opens on one of these is not English shaped, and a
# US speaker will insert a vowel or drop a letter when saying it. Kept deliberately short: the
# full phonotactic set is large, and only the common foreign borrowings matter in practice.
ILLEGAL_ONSETS = ("pf", "ts", "zh", "gz", "vl", "sr", "tl", "dl", "kv", "hr", "mb", "ng", "tk")


# A trailing vowel LETTER, silent "e" excluded because it is not an open SOUND. Lives here
# rather than in `corpus.py` or `generate.py` because BOTH read it and they must agree: the
# corpus measures how often a market ends open, and the generator is now steered by that
# number. Two copies of this tuple drifting apart would make the measurement and the thing it
# calibrates quietly stop meaning the same thing.
OPEN_FINAL_LETTERS = ("a", "i", "o", "u", "y")


class Finding:
    """One thing wrong with a name, with the reason attached.

    The reason is not decoration. A score with no reason cannot be argued with, and the whole
    point of this tool is that the person naming the product gets to disagree with it.
    """

    def __init__(self, code, weight, detail):
        self.code = code
        self.weight = weight
        self.detail = detail

    def __repr__(self):
        return "Finding({}, w={}, {!r})".format(self.code, self.weight, self.detail)


def syllables(name):
    """Vowel-group count, the cheap heuristic.

    Deliberately not a dictionary lookup: a generated name is not in any dictionary, which is
    exactly when you need the number. It over-counts on silent e, so that case is subtracted.
    """
    w = re.sub(r"[^a-z]", "", name.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ye")):
        n -= 1
    return max(1, n)


def spell_risk(name):
    """Findings for the sound to grapheme direction. This is the phone call test."""
    w = re.sub(r"[^a-z]", "", name.lower())
    out = []
    for pattern, sound, competing, weight, where in SOUND_TO_SPELLING:
        if re.search(pattern, w):
            out.append(Finding(
                "SPELL_AMBIGUOUS", weight,
                "the {} sound at the {} can be written {}; a listener has to guess".format(
                    sound, where, competing)))
    for pattern, cluster, why in SILENT:
        if re.search(pattern, w):
            out.append(Finding("SILENT_LETTER", 2, "{}: {}".format(cluster, why)))
    for pattern, sound, competing in VOWEL_TEAMS:
        if re.search(pattern, w):
            weight = 3 if pattern == "ough" else 2
            out.append(Finding(
                "VOWEL_TEAM", weight,
                "{} reads as {} and competes with {}".format(pattern, sound, competing)))
    for m in re.finditer(r"([bcdfglmnprstz])\1", w):
        out.append(Finding(
            "DOUBLED_LETTER", 2,
            "doubled {}: expect 'is that one {} or two' on every call".format(
                m.group(1), m.group(1))))
    return out


def reading_risk(name):
    """Findings for the grapheme to sound direction. Cheaper, still real."""
    w = re.sub(r"[^a-z]", "", name.lower())
    out = []
    for pattern, why, weight in READING_TRAPS:
        if re.search(pattern, w):
            out.append(Finding("READING_TRAP", weight, why))
    for onset in ILLEGAL_ONSETS:
        if w.startswith(onset):
            out.append(Finding(
                "FOREIGN_ONSET", 3,
                "'{}' is not a legal English word opening; US speakers will insert a vowel "
                "or drop a letter".format(onset)))
            break
    return out


def shape_risk(name):
    """Length and syllable findings.

    The thresholds are not folklore: they come from what a name has to survive, an email
    signature, a business card, and being said once on a call. Fifteen characters is where a
    domain stops fitting comfortably in speech; four syllables is where people start shortening
    it for you, and the shortening becomes the real name.
    """
    w = re.sub(r"[^a-z0-9]", "", name.lower())
    out = []
    if len(w) > 15:
        out.append(Finding("TOO_LONG", 2,
                           "{} characters; people will shorten it, and their shortening "
                           "becomes the name".format(len(w))))
    if len(w) < 3:
        out.append(Finding("TOO_SHORT", 3,
                           "under three characters is unsearchable and almost certainly taken"))
    s = syllables(w)
    if s >= 4:
        out.append(Finding("MANY_SYLLABLES", 2,
                           "{} syllables; four or more get abbreviated in conversation".format(s)))
    if re.search(r"\d", name):
        out.append(Finding("CONTAINS_DIGIT", 3,
                           "a digit forces 'is that the number or the word' every single time"))
    if "-" in name:
        out.append(Finding("CONTAINS_HYPHEN", 3,
                           "a hyphen is unsayable; people drop it and land on the wrong domain"))
    return out


def analyse(name):
    """Every phonetic finding for one name, heaviest first."""
    found = spell_risk(name) + reading_risk(name) + shape_risk(name)
    return sorted(found, key=lambda f: -f.weight)


def grade(findings):
    """Total weight to a letter, (grade, total). Shared by `cli.py`'s `score` and `generate.py`'s
    `--score`, so a name graded A or B through one door is graded the same way through the
    other. Weights are additive on purpose: three small problems really are worse than one small
    problem, and a name with six findings is a name you will be spelling out loud for years."""
    total = sum(f.weight for f in findings)
    # A negative total is reachable, and on purpose. A finding can carry a NEGATIVE weight when
    # it is a bonus rather than a flaw, which is how a free bare .com enters the ranking:
    # strongly desirable, never required. Grading it as its own band keeps the reader from
    # reading a bonus as merely "clean".
    if total < 0:
        return "A+", total
    if total == 0:
        return "A", total
    if total <= 2:
        return "B", total
    if total <= 5:
        return "C", total
    if total <= 9:
        return "D", total
    return "F", total
