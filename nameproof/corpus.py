"""What do the names that already won in THIS market look like?

The second thing no other tool does. Availability checkers tell you a name is free. Scorers tell
you it is pretty. Neither tells you that in your particular market, nine of the ten companies
people already pay carry a coined two-syllable word and none of them put the category in the
name. That is a fact about the market, it is cheap to measure, and it beats any general rule
about what a good name is.

Feed it the names your buyer already knows. The output is not a recommendation, it is a
description: here is the shape of the names that got funded, hired, or bookmarked in this space.
Diverging from it is a decision you get to make on purpose instead of by accident.

WHAT THIS MODULE IS FOR, SINCE 2026-08-25, and it is a bigger job than printing a table. A
`CorpusReport` is also the input to `MarketProfile`, which is what `generate --market` and `gold
--market` read to shape the candidates they produce. Before that wire existed, three of the
generator's constants were hard-coded off a four-name cherry-pick (Vanta, Drata, Sprinto,
Alessa) and admitted in their own comments to be "chosen, not measured", while the corpora that
could measure them sat in the same repository. Measured the day the wire was built: the `roots`
technique ended on a vowel 56% of the time and `phonotactic` 46%, against 30% for the SOC 2
corpus, 10% for AML, and 0% for developer CLI tools. The generator was not wrong, it was
uncalibrated, and it produced one register regardless of who the buyer was.

SO EVERY STATISTIC HERE HAS TWO READERS: a person deciding whether to break the pattern, and a
generator that has to reproduce it. Anything measured for the first reader alone stays a table
row; anything the generator can consume goes through `MarketProfile`.
"""
import re
import statistics
from collections import Counter

from . import seo
from .phonetics import OPEN_FINAL_LETTERS, analyse, grade, syllables

# Words that name the CATEGORY rather than the company. Presence of one of these is the single
# most informative bit in a corpus, because it separates the markets where vendors sell a
# product from the markets where they sell a service.
CATEGORY_HINTS = (
    "comply", "compliance", "secure", "security", "risk", "audit", "legal", "law", "tax",
    "pay", "payment", "invoice", "billing", "health", "care", "med", "learn", "school",
    "hire", "recruit", "hr", "crm", "data", "cloud", "dev", "code", "api", "soft", "tech",
    "group", "partners", "solutions", "systems", "labs", "consulting", "advisors", "capital",
)


def tokens(name):
    """A name split into the word-shaped pieces a reader actually sees.

    Splits on non-letters AND on a camel-case seam, so `MyComplianceOffice` becomes
    my/compliance/office and `Strike Graph` becomes strike/graph. Lowercased last, because the
    capital IS the boundary signal and destroying it before the split throws the seam away.
    """
    out = []
    for chunk in re.split(r"[^A-Za-z]+", name):
        if not chunk:
            continue
        # An all-caps chunk (COMPLY, ACA) has no camel seam to find; splitting it would produce
        # one token per letter.
        if chunk.isupper():
            out.append(chunk.lower())
            continue
        out.extend(p.lower() for p in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", chunk))
    return out


def names_category(name):
    """Does this name put the CATEGORY in it, matched at a word edge rather than anywhere?

    THE BUG THIS EXISTS TO CLOSE, and it is the one `corpora/calibration.jsonl` already carries
    for the search check, shipped a second time in a different module. A plain `in` test against
    the lowercased name fires inside unrelated words: probed against 40 real startup names on
    2026-08-25 it reported `api` for **Rapid7** (r-API-d), and `hr` for **Anthropic** and
    **Threads**. None of the bundled corpora happened to trigger it, which is exactly why it
    survived: it returns a confident, plausible, wrong answer only on names nobody fed it yet.

    A hint has to sit at the START or the END of a token. Both edges are needed and neither is
    enough alone: `Datadog` and `Secureframe` carry the hint as a prefix, `Fintech` and
    `Coinbase`-shaped names carry it as a suffix, and requiring a whole-token match would miss
    every compound, which is most of how a category word actually shows up in a brand.
    """
    parts = tokens(name)
    return sorted({h for h in CATEGORY_HINTS
                   for t in parts if t.startswith(h) or t.endswith(h)})


def built_from_real_words(name):
    """Is every token of this name an ordinary English word?

    THE AXIS THE NAMING RULE TURNS ON, and until 2026-08-25 the one axis this module could not
    report. The skill's rule of that date sets the target at a name that is gold-shaped AND
    meaning-carrying, justified by the measurement that real-word golds are squatted at ~100%
    while coined meaning-carriers stay findable. A market's split between the two registers is
    therefore the most decision-relevant thing about it, and it was missing.

    EVERY token, not the name as a whole: `Strike Graph` and `ComplyAdvantage` are both built
    entirely out of real words, and both sit in a different register from `Vanta` even though
    neither is a dictionary entry itself. The lookup is `seo.is_real_word`, shared rather than
    reimplemented, so "ordinary English word" means the same thing here and in the SEO check.
    """
    parts = tokens(name)
    return bool(parts) and all(seo.is_real_word(t) for t in parts)


class CorpusReport:
    def __init__(self, names, label="corpus"):
        # `label` defaults so every existing caller keeps working; `compare` and `render` both
        # need a name for the column and the heading, and passing it at construction is what
        # keeps those two from disagreeing about what this corpus is called.
        self.label = label
        self.names = [n.strip() for n in names if n.strip()]
        self.n = len(self.names)
        self.one_word = [n for n in self.names if " " not in n]
        self.multi_word = [n for n in self.names if " " in n]
        self.with_category = [n for n in self.names if names_category(n)]
        self.syllables = Counter(syllables(n.split()[0]) for n in self.names)
        lens = sorted(len(n.replace(" ", "")) for n in self.one_word)
        self.len_min = lens[0] if lens else 0
        self.len_med = lens[len(lens) // 2] if lens else 0
        self.len_max = lens[-1] if lens else 0
        # Open final syllable: does the name END on a vowel sound? Measured because the
        # generator is steered by it (see `MarketProfile`), and because the reference set of
        # coined SaaS names this tool's README cites is overwhelmingly vowel-final while most
        # real markets are not. Approximated on the letter, which is good enough for a final
        # position: English rarely writes a final vowel it does not say, apart from silent e,
        # which `OPEN_FINAL_LETTERS` excludes.
        self.open_final = [n for n in self.names
                           if n.rstrip().lower().endswith(OPEN_FINAL_LETTERS)]
        self.real_word = [n for n in self.names if built_from_real_words(n)]
        # Whether the real-word share above was measured against a real dictionary or against
        # the 52-word embedded fallback. Reported rather than hidden: a share is not a share
        # when the reference set is a stub, and silently printing "0% real words" off a missing
        # dictionary is precisely the confident-plausible-wrong failure `doctor` exists for.
        self.dictionary_available = seo.has_system_dict()
        self.penalties = [grade(analyse(n))[1] for n in self.names]

    @property
    def category_share(self):
        return len(self.with_category) / self.n if self.n else 0.0

    @property
    def open_final_share(self):
        return len(self.open_final) / self.n if self.n else 0.0

    @property
    def one_word_share(self):
        return len(self.one_word) / self.n if self.n else 0.0

    @property
    def real_word_share(self):
        return len(self.real_word) / self.n if self.n else 0.0

    @property
    def median_penalty(self):
        """The market's own phonetic bar, in the tool's own units.

        Worth knowing before you reject a candidate at penalty 3: if the names people already
        pay for sit at a median of 4, the bar you are holding your candidate to is one the
        market never had to clear.
        """
        return statistics.median(self.penalties) if self.penalties else 0

    def dominant_syllables(self):
        return self.syllables.most_common(1)[0][0] if self.syllables else 0

    def verdict(self):
        """The one sentence a person actually acts on.

        Carries `n`, because every corpus in this repository is between 10 and 21 names and a
        share computed on 10 read exactly like a share computed on 1000 until the day somebody
        acted on one.
        """
        if not self.n:
            return "empty corpus"
        bits = ["{:.0f}% are a single word".format(100 * self.one_word_share),
                "{:.0f}% name the category".format(100 * self.category_share)]
        if self.dictionary_available:
            bits.append("{:.0f}% are built from real words".format(100 * self.real_word_share))
        bits.append("{} syllables dominate".format(self.dominant_syllables()))
        bits.append("median length {}".format(self.len_med))
        return "{}  (n={})".format(", ".join(bits), self.n)

    def render(self, label=None):
        L = ["{}  ({} names)".format(label or self.label, self.n), "-" * 62]
        L.append("  single word            : {}/{}  ({:.0f}%)".format(
            len(self.one_word), self.n, 100 * self.one_word_share))
        L.append("  names the category     : {}/{}  ({:.0f}%){}".format(
            len(self.with_category), self.n, 100 * self.category_share,
            "  -> " + ", ".join(self.with_category[:6]) if self.with_category else ""))
        if self.dictionary_available:
            L.append("  built from real words  : {}/{}  ({:.0f}%){}".format(
                len(self.real_word), self.n, 100 * self.real_word_share,
                "  -> " + ", ".join(self.real_word[:6]) if self.real_word else ""))
        else:
            L.append("  built from real words  : not measured, no system dictionary on this "
                     "machine")
        L.append("  ends on a vowel        : {}/{}  ({:.0f}%)".format(
            len(self.open_final), self.n, 100 * self.open_final_share))
        L.append("  syllables (first word) : {}".format(
            ", ".join("{}syl x{}".format(k, v) for k, v in sorted(self.syllables.items()))))
        if self.one_word:
            L.append("  single-word length     : min {} median {} max {}".format(
                self.len_min, self.len_med, self.len_max))
        L.append("  phonetic penalty       : median {}, worst {}".format(
            _num(self.median_penalty), max(self.penalties) if self.penalties else 0))
        L.append("")
        L.append("  read as: {}".format(self.verdict()))
        return "\n".join(L)


def _num(x):
    """2.0 prints as 2, 2.5 prints as 2.5. `statistics.median` returns a float on an even count,
    and a penalty of "2.0" in a table of integers reads as a precision the scale does not have."""
    return int(x) if float(x).is_integer() else x


def load(path):
    """One name per line. Blank lines and lines starting with # are ignored."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


# ---------------------------------------------------------------------------
# The generator's view of a market
# ---------------------------------------------------------------------------

# Widest band the phonotactic builder can actually assemble a name in. Not a taste judgement:
# below 3 letters `phonetics.shape_risk` calls a name unsearchable, and above 15 it calls it
# too long, so a profile asking for either would only ever produce candidates the tool's own
# scorer rejects. A corpus that genuinely sits outside this (`dev-cli` has `jq` and `fd` at 2
# letters) gets clamped, and the clamp is reported by `MarketProfile.describe`.
_MIN_LETTERS = 3
_MAX_LETTERS = 15
_MIN_SYLLABLES = 1
_MAX_SYLLABLES = 4


class MarketProfile:
    """What a generator needs from a market, as numbers instead of a table.

    Deliberately a SEPARATE type from `CorpusReport` rather than more properties on it. A report
    is a description for a person and may grow any row that is interesting; a profile is a
    contract with `generate.py` and holds only what a technique can actually act on. Keeping
    them apart is what stops an interesting new statistic from silently changing the names the
    tool produces.

    THE THREE LEVERS, and each one replaces a constant that used to be hard-coded:

      `open_final`        replaces the 2-to-1 vowel-final suffix bias in `latin_roots` and the
                          0.25 closed-final chance in `phonotactic`.
      `syllable_weights`  replaces the flat 80/20 draw over 2 and 3 syllables in `phonotactic`.
      `len_min`/`len_max` replaces nothing, because nothing filtered by length before: `rare`
                          and `markov` draw from fixed pools and could not be steered at all,
                          so the band is how they get pointed at a market.
    """

    def __init__(self, report, label="market"):
        self.label = label
        self.n = report.n
        self.open_final = report.open_final_share
        self.median_penalty = report.median_penalty
        raw = {k: v for k, v in report.syllables.items()
               if _MIN_SYLLABLES <= k <= _MAX_SYLLABLES}
        # An empty dict here means every name in the corpus sits outside the buildable range.
        # Falling back to the report's own dominant count would reproduce the unbuildable
        # number; falling back to 2 and 3 reproduces the pre-profile behaviour, which is the
        # honest default when the corpus cannot answer.
        self.syllable_weights = raw or {2: 80, 3: 20}
        self.len_min = max(_MIN_LETTERS, report.len_min or _MIN_LETTERS)
        self.len_max = min(_MAX_LETTERS, report.len_max or _MAX_LETTERS)
        if self.len_max < self.len_min:
            self.len_min, self.len_max = _MIN_LETTERS, _MAX_LETTERS
        self.clamped = (report.len_min or 0) < _MIN_LETTERS or (report.len_max or 0) > _MAX_LETTERS

    def fits_shape(self, name):
        """The band filter every technique applies, including the two that cannot be steered."""
        letters = re.sub(r"[^a-z]", "", name.lower())
        if not (self.len_min <= len(letters) <= self.len_max):
            return False
        return _MIN_SYLLABLES <= syllables(name) <= _MAX_SYLLABLES

    def describe(self):
        syl = ", ".join("{}syl x{}".format(k, v)
                        for k, v in sorted(self.syllable_weights.items()))
        line = ("shaped by {} (n={}): {:.0f}% vowel-final, {} letters, {}"
                .format(self.label, self.n, 100 * self.open_final,
                        "{}-{}".format(self.len_min, self.len_max), syl))
        if self.clamped:
            line += "\n  (length band clamped to what the scorer will not reject out of hand)"
        return line


def profile(report, label="market"):
    return MarketProfile(report, label)


def fits(name, report):
    """How far this candidate sits from the shape of the market, as findings not as a score.

    Deliberately not folded into the quality score by `score`. Fitting the market is not always
    right: a name that breaks the pattern on purpose is a positioning choice, and the tool has
    no business overruling it. It just has to be visible.

    `generate --market` and `gold --market` DO fold these into the ranking, and that is not a
    contradiction: there, the user asked for names shaped like this market, so the distance
    from it is the thing being ranked on rather than an opinion imposed on a name they already
    chose.
    """
    from .phonetics import Finding
    out = []
    w = name.strip()
    if not w:
        return out
    if " " in w and report.one_word_share > 0.7:
        out.append(Finding("OFF_PATTERN", 1,
                           "{:.0f}% of this market uses a single word, this one has a space"
                           .format(100 * report.one_word_share)))
    if names_category(w) and report.category_share < 0.25:
        out.append(Finding("OFF_PATTERN", 2,
                           "only {:.0f}% of this market puts the category in the name; doing it "
                           "reads as a service firm rather than a product".format(
                               100 * report.category_share)))
    s = syllables(w.split()[0])
    dom = report.dominant_syllables()
    if dom and abs(s - dom) >= 2:
        out.append(Finding("OFF_PATTERN", 1,
                           "{} syllables against a market that clusters at {}".format(s, dom)))
    return out


def compare(reports):
    """Two or more markets side by side, which is how this tool's best finding was made.

    THE REASON THIS FUNCTION EXISTS. The README's flagship result is that SOC 2 compliance sold
    as a PRODUCT names the category 10% of the time while investment adviser compliance sold as
    a SERVICE does it 50% of the time, and that product companies and service firms therefore do
    not name themselves the same way. That finding was produced by a human running `market`
    twice and diffing the output by eye. The tool could not state its own headline result, which
    means nothing guarded it and nobody could reproduce it without being told how.
    """
    rows = [("names the category", lambda r: r.category_share),
            ("single word", lambda r: r.one_word_share),
            ("ends on a vowel", lambda r: r.open_final_share)]
    if all(r.dictionary_available for r in reports):
        rows.append(("built from real words", lambda r: r.real_word_share))

    width = max(22, max(len(r.label) for r in reports) + 2)
    L = ["", "comparison", "-" * 62]
    L.append("  {:<22}{}".format("", "".join("{:<{w}}".format(r.label, w=width)
                                             for r in reports)))
    for title, fn in rows:
        L.append("  {:<22}{}".format(title, "".join(
            "{:<{w}}".format("{:.0f}%  (n={})".format(100 * fn(r), r.n), w=width)
            for r in reports)))
    L.append("  {:<22}{}".format("median penalty", "".join(
        "{:<{w}}".format(_num(r.median_penalty), w=width) for r in reports)))

    L.append("")
    for title, fn in rows:
        vals = [(fn(r), r.label) for r in reports]
        lo, hi = min(vals), max(vals)
        if hi[0] - lo[0] >= 0.25:
            L.append("  {} splits these markets: {:.0f}% for {} against {:.0f}% for {}".format(
                title, 100 * hi[0], hi[1], 100 * lo[0], lo[1]))
    return "\n".join(L)
