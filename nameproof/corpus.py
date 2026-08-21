"""What do the names that already won in THIS market look like?

The second thing no other tool does. Availability checkers tell you a name is free. Scorers tell
you it is pretty. Neither tells you that in your particular market, nine of the ten companies
people already pay carry a coined two-syllable word and none of them put the category in the
name. That is a fact about the market, it is cheap to measure, and it beats any general rule
about what a good name is.

Feed it the names your buyer already knows. The output is not a recommendation, it is a
description: here is the shape of the names that got funded, hired, or bookmarked in this space.
Diverging from it is a decision you get to make on purpose instead of by accident.
"""
import re
from collections import Counter

from .phonetics import syllables

# Words that name the CATEGORY rather than the company. Presence of one of these is the single
# most informative bit in a corpus, because it separates the markets where vendors sell a
# product from the markets where they sell a service.
CATEGORY_HINTS = (
    "comply", "compliance", "secure", "security", "risk", "audit", "legal", "law", "tax",
    "pay", "payment", "invoice", "billing", "health", "care", "med", "learn", "school",
    "hire", "recruit", "hr", "crm", "data", "cloud", "dev", "code", "api", "soft", "tech",
    "group", "partners", "solutions", "systems", "labs", "consulting", "advisors", "capital",
)


class CorpusReport:
    def __init__(self, names):
        self.names = [n.strip() for n in names if n.strip()]
        self.n = len(self.names)
        self.one_word = [n for n in self.names if " " not in n]
        self.multi_word = [n for n in self.names if " " in n]
        self.with_category = [n for n in self.names
                              if any(h in n.lower() for h in CATEGORY_HINTS)]
        self.syllables = Counter(syllables(n.split()[0]) for n in self.names)
        lens = sorted(len(n.replace(" ", "")) for n in self.one_word)
        self.len_min = lens[0] if lens else 0
        self.len_med = lens[len(lens) // 2] if lens else 0
        self.len_max = lens[-1] if lens else 0
        self.initials = Counter(n[0].lower() for n in self.names if n)
        # Open final syllable: does the name END on a vowel sound? Measured because the
        # reference set of coined SaaS names (Vanta, Drata, Sprinto, Alessa, Scrut aside) is
        # overwhelmingly vowel-final, and a generator that ignores this produces closed,
        # clattering forms that read as foreign. Approximated on the letter, which is good
        # enough for a final position: English rarely writes a final vowel it does not say,
        # apart from silent e, which is excluded.
        self.open_final = [n for n in self.names
                           if n.rstrip().lower().endswith(("a", "i", "o", "u", "y"))]

    @property
    def category_share(self):
        return len(self.with_category) / self.n if self.n else 0.0

    @property
    def open_final_share(self):
        return len(self.open_final) / self.n if self.n else 0.0

    @property
    def one_word_share(self):
        return len(self.one_word) / self.n if self.n else 0.0

    def dominant_syllables(self):
        return self.syllables.most_common(1)[0][0] if self.syllables else 0

    def verdict(self):
        """The one sentence a person actually acts on."""
        if not self.n:
            return "empty corpus"
        bits = []
        bits.append("{:.0f}% are a single word".format(100 * self.one_word_share))
        bits.append("{:.0f}% name the category".format(100 * self.category_share))
        bits.append("{} syllables dominate".format(self.dominant_syllables()))
        bits.append("median length {}".format(self.len_med))
        return ", ".join(bits)

    def render(self, label="corpus"):
        L = ["{}  ({} names)".format(label, self.n), "-" * 62]
        L.append("  single word            : {}/{}  ({:.0f}%)".format(
            len(self.one_word), self.n, 100 * self.one_word_share))
        L.append("  names the category     : {}/{}  ({:.0f}%){}".format(
            len(self.with_category), self.n, 100 * self.category_share,
            "  -> " + ", ".join(self.with_category[:6]) if self.with_category else ""))
        L.append("  ends on a vowel        : {}/{}  ({:.0f}%)".format(
            len(self.open_final), self.n, 100 * self.open_final_share))
        L.append("  syllables (first word) : {}".format(
            ", ".join("{}syl x{}".format(k, v) for k, v in sorted(self.syllables.items()))))
        if self.one_word:
            L.append("  single-word length     : min {} median {} max {}".format(
                self.len_min, self.len_med, self.len_max))
        L.append("")
        L.append("  read as: {}".format(self.verdict()))
        return "\n".join(L)


def load(path):
    """One name per line. Blank lines and lines starting with # are ignored."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def fits(name, report):
    """How far this candidate sits from the shape of the market, as findings not as a score.

    Deliberately not folded into the quality score. Fitting the market is not always right: a
    name that breaks the pattern on purpose is a positioning choice, and the tool has no
    business overruling it. It just has to be visible.
    """
    from .phonetics import Finding
    out = []
    w = name.strip()
    if " " in w and report.one_word_share > 0.7:
        out.append(Finding("OFF_PATTERN", 1,
                           "{:.0f}% of this market uses a single word, this one has a space"
                           .format(100 * report.one_word_share)))
    if any(h in w.lower() for h in CATEGORY_HINTS) and report.category_share < 0.25:
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
