"""Does any of this actually predict anything? The command that is allowed to answer no.

WHY THIS MODULE EXISTS. Dylan, 2026-08-25: "il faut des stats pour voir ce qui fonctionne."
Every other measurement in this tool describes a name: how it spells, how it sounds, how it sits
against a market's conventions. None of them had ever been checked against an OUTCOME, so none
of them could say whether a name's shape matters at all. That is a real question and it deserves
a real answer rather than a louder version of the same advice.

THE DATASET, and why it is Y Combinator. `nameproof/data/yc_cohort.tsv` carries 6190 companies
with a batch year and a status, built by `tools/build_cohort.py` from the public YC directory.
Crunchbase was the obvious source and is out: the Basic API is discontinued, there is no free
tier, and this tool spends no money. YC is better here anyway, because the outcome and the DATE
travel together, and without the date the outcome is unreadable.

THE CONFOUND, which is the entire methodological problem. Resolution rate falls from about 91%
for the 2007 batches to 0% for 2026. A company from an old batch has had many more years both to
be acquired and to die. Comparing names across batches without stratifying measures age, and
would have produced a confident finding out of nothing. Every test below permutes the outcome
labels WITHIN a batch year and never across.

WHAT IT FOUND, stated here because a module whose result lives only in a README is a module
whose result gets quietly forgotten. Across 1899 resolved companies in 21 batch-year strata,
seven measurable name properties were tested against acquired-or-public versus inactive. One
reached significance under a Bonferroni correction: name LENGTH, at half a letter shorter for
the companies that resolved well. It then dissolved completely when restricted to single-word
names (-0.08 letters, p=0.48). The apparent length effect was multi-word names being both longer
and worse, and "is it one word" was itself only marginal and did not survive the correction.

SO THE ANSWER IS NO, and it is the most useful thing this repository can tell you about naming:
nothing this tool measures predicts whether a company works. That is not a reason to stop
measuring. A `SPELL_AMBIGUOUS` finding is a COST, paid every time somebody says the name on a
call, and a cost is real whether or not it shows up in an acquisition rate that is dominated by
the product, the market and the founders. What the null kills is the other claim, the one no
naming tool should ever have made: that a good name makes you win.

KNOWN LIMITS, because a null result is only worth as much as the honesty around it.

  * "Acquired" is not unambiguously a win. An acqui-hire is a soft landing wearing a success
    label, and this data cannot tell the two apart. "Public" is cleaner and there are only 23 of
    them, which is why the two are pooled.
  * YC is one accelerator with one selection filter. Nothing here generalises to companies that
    never applied.
  * YC's `name` field occasionally carries an alias or a parenthetical rather than a bare brand
    ("Kenota (formerly ExVivo Labs)"), which inflates the length and word count of 12 of the
    1902 resolved rows, 0.6%. They are kept VERBATIM, because editing third-party names is
    editing the evidence, and the effect of not editing them was measured instead of assumed:
    dropping all 12 moves the headline length difference from -0.517 to -0.461 (p 0.0010 to
    0.0015) and leaves the single-word control identical at -0.078, p=0.4708. The conclusion
    does not depend on them.
  * Absence of evidence at n=1899 is not proof of absence. An effect small enough to hide here
    is also small enough to be worthless as naming advice, which is the practical point.

The same discipline as `seo.py` applies here. That module refuses to repeat the 2012 EMD folklore
because the primary source does not exist. This one refuses to sell a naming effect because the
measurement says there is not one.
"""
import os
import random
import re
from collections import defaultdict

from . import corpus
from .phonetics import OPEN_FINAL_LETTERS, analyse, grade, syllables

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yc_cohort.tsv")

# Acquired and Public are counted together as "resolved well" and Inactive as "resolved badly".
# Both halves of that are arguable and the argument is worth having in the open: an acquisition
# can be a soft landing rather than a win, and a company still Active is not a failure, it just
# has not answered yet. Active is therefore EXCLUDED rather than counted as either, because
# folding it into one side would let the batch year decide the result all over again.
WON = ("A", "P")
LOST = ("I",)

# Every trial reuses one permutation across all properties, so the number below buys resolution
# on all seven at once. 2000 puts the smallest reportable p at 0.0005, comfortably below the
# corrected threshold, and keeps a full run under a couple of seconds.
DEFAULT_TRIALS = 2000

# Fixed, because a p-value that changes between two runs of the same command is not evidence.
# Same promise `generate` makes about its seed, for the same reason.
DEFAULT_SEED = 20260825

# The market slices present in the extract, mirroring `tools/build_cohort.py`'s MARKETS. Named
# here so the CLI can list them in `--help` without importing a build script that fetches URLs.
MARKETS_IN_DATA = ("ai", "devtools", "fintech")


def _letters(name):
    return re.sub(r"[^a-z]", "", name.lower())


# (key, one-line label, extractor). Each extractor returns a number; a boolean property returns
# 0 or 1 so its stratified difference reads directly as a percentage-point gap.
PROPERTIES = [
    ("length", "letters in the name", lambda n: len(_letters(n))),
    ("syllables", "syllables in the first word", lambda n: syllables(n.split()[0])),
    ("penalty", "phonetic penalty (this tool's score)", lambda n: grade(analyse(n))[1]),
    ("real_word", "built from real words", lambda n: int(corpus.built_from_real_words(n))),
    ("open_final", "ends on a vowel", lambda n: int(n.lower().endswith(OPEN_FINAL_LETTERS))),
    ("category", "names the category", lambda n: int(bool(corpus.names_category(n)))),
    ("one_word", "is a single word", lambda n: int(" " not in n.strip())),
]


class Row:
    __slots__ = ("name", "year", "outcome", "markets", "won")

    def __init__(self, name, year, outcome, markets):
        self.name = name
        self.year = year
        self.outcome = outcome
        self.markets = markets
        self.won = outcome in WON

    @property
    def resolved(self):
        return self.outcome in WON or self.outcome in LOST


def load(path=DATA_PATH):
    """The cohort, verbatim. Tab separated: name, batch year, outcome code, markets."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            name, year, outcome = parts[0], parts[1], parts[2]
            markets = parts[3].split(",") if len(parts) > 3 and parts[3] else []
            if not name.strip() or not year.isdigit():
                continue
            rows.append(Row(name, int(year), outcome, markets))
    return rows


def select(rows, market=None, resolved_only=True, single_word_only=False):
    out = [r for r in rows if r.resolved] if resolved_only else list(rows)
    if market:
        out = [r for r in out if market in r.markets]
    if single_word_only:
        out = [r for r in out if " " not in r.name.strip()]
    return out


def _strata(rows):
    """Batch year to its rows, keeping only years that contain BOTH outcomes.

    A stratum that is all winners or all losers contributes no information to a within-stratum
    comparison and would make the permutation a no-op there. Dropping it is not cherry-picking:
    it is the arithmetic of a paired comparison that has only one side.
    """
    by = defaultdict(list)
    for r in rows:
        by[r.year].append(r)
    return {y: v for y, v in by.items()
            if any(r.won for r in v) and any(not r.won for r in v)}


def _pooled_difference(values_by_year, won_counts, picks):
    """Size-weighted mean of the within-stratum (won minus lost) difference.

    `picks[y]` is the index list assigned to the winning group for that stratum. The observed
    statistic passes the real winners; a permutation trial passes a random subset of the same
    size, which is what holds the batch year fixed.
    """
    total = 0.0
    n_all = 0
    for year, values in values_by_year.items():
        n_w = won_counts[year]
        n_l = len(values) - n_w
        if not n_w or not n_l:
            continue
        chosen = picks[year]
        s_w = 0.0
        for i in chosen:
            s_w += values[i]
        s_all = sum(values)
        total += len(values) * (s_w / n_w - (s_all - s_w) / n_l)
        n_all += len(values)
    return total / n_all if n_all else 0.0


def test_properties(rows, properties=PROPERTIES, trials=DEFAULT_TRIALS, seed=DEFAULT_SEED):
    """Every property against the outcome, one shared set of permutations.

    Returns a list of dicts: key, label, difference, p_value, n. The permutations are shared
    across properties on purpose, so the seven results describe one null world rather than seven
    unrelated ones, and so a run costs one pass instead of seven.
    """
    strata = _strata(rows)
    if not strata:
        return [], 0, 0

    order = sorted(strata)
    values_by_year = {}
    won_counts = {}
    observed_picks = {}
    for y in order:
        rs = strata[y]
        won_counts[y] = sum(1 for r in rs if r.won)
        observed_picks[y] = [i for i, r in enumerate(rs) if r.won]
    n_total = sum(len(strata[y]) for y in order)

    rng = random.Random(seed)
    permutations = []
    for _ in range(trials):
        permutations.append({y: rng.sample(range(len(strata[y])), won_counts[y]) for y in order})

    results = []
    for key, label, extract in properties:
        for y in order:
            values_by_year[y] = [extract(r.name) for r in strata[y]]
        observed = _pooled_difference(values_by_year, won_counts, observed_picks)
        extreme = 0
        for picks in permutations:
            if abs(_pooled_difference(values_by_year, won_counts, picks)) >= abs(observed):
                extreme += 1
        # The +1 on both sides is the standard guard against reporting p=0 from a finite number
        # of permutations. A run of 2000 cannot distinguish "very unlikely" from "impossible",
        # and printing 0.0000 would claim it could.
        p = (1 + extreme) / (trials + 1)
        results.append({"key": key, "label": label, "difference": observed,
                        "p_value": p, "n": n_total})
    return results, n_total, len(order)


def alpha(n_tests, family=0.05):
    """Bonferroni. Seven tests at 0.05 each is a one-in-three chance of a false positive
    somewhere, and reporting the winner of seven coin flips as a finding is exactly how naming
    folklore gets manufactured."""
    return family / n_tests if n_tests else family


# The known confound, checked automatically instead of left to the reader.
#
# WHY IT IS HARDCODED AND NOT A FLAG. On the first run of this analysis, `length` came back
# significant at p=0.001 and everything else came back null, which reads as a finding: shorter
# names win. Restricting the same test to SINGLE-WORD names collapsed it to -0.08 letters at
# p=0.48. The effect was never about length. Multi-word names are both longer and worse, so
# length was standing in for word count, and "is it one word" was itself only marginal.
#
# A command that printed the first number and not the second would ship the folklore this whole
# repository exists to refuse. So the check runs every time the headline is a length effect, and
# the verdict below reports what it found rather than what the first table implied.
CONFOUND_KEY = "length"


def confound_check(rows, trials=DEFAULT_TRIALS, seed=DEFAULT_SEED):
    """Re-run the length test on single-word names only. Returns the result dict, or None when
    the slice is too small to say anything."""
    subset = select(rows, single_word_only=True)
    props = [p for p in PROPERTIES if p[0] == CONFOUND_KEY]
    results, n, _ = test_properties(subset, properties=props, trials=trials, seed=seed)
    return results[0] if results else None


def verdict(results, threshold, confound=None):
    hits = [r for r in results if r["p_value"] < threshold]
    if not hits:
        return ("Nothing this tool measures predicts the outcome. Every property tested is "
                "indistinguishable from noise once the batch year is held fixed.")
    def listed(rs):
        return ", ".join("{} ({:+.3f}, p={:.4f})".format(r["key"], r["difference"], r["p_value"])
                         for r in rs)

    if confound is not None and any(h["key"] == CONFOUND_KEY for h in hits):
        # `length` was the headline and the control dissolved it. Whatever else survived has to
        # be reported on its own terms rather than swept up in the same sentence: on the AI
        # slice, `one_word` also clears the correction, and saying "nothing predicts the
        # outcome" there would be exactly the overclaim in the other direction.
        others = [h for h in hits if h["key"] != CONFOUND_KEY]
        if confound["p_value"] >= 0.05:
            head = ("The length effect is NOT about length. Restricted to single-word names it "
                    "collapses to {:+.3f} letters at p={:.4f} (n={}), so what the first table "
                    "measured was multi-word names being both longer and worse."
                    .format(confound["difference"], confound["p_value"], confound["n"]))
            if others:
                return "{} Still standing after that: {}. Read the effect size before acting " \
                       "on it.".format(head, listed(others))
            return "{} Nothing this tool measures predicts the outcome.".format(head)
        return ("Length survives the word-count control: {:+.3f} letters among single-word "
                "names alone, p={:.4f} (n={}){}."
                .format(confound["difference"], confound["p_value"], confound["n"],
                        ". Also standing: " + listed(others) if others else ""))
    return "Survives correction: {}. Read the effect size before acting on it.".format(
        listed(hits))


def render(rows, market=None, trials=DEFAULT_TRIALS, seed=DEFAULT_SEED):
    results, n, n_strata = test_properties(rows, trials=trials, seed=seed)
    label = market or "all markets"
    L = ["", "cohort: {}  ({} resolved companies, {} batch-year strata)".format(
        label, n, n_strata), "-" * 74]
    if not results:
        L.append("  not enough resolved companies in this slice to compare anything.")
        return "\n".join(L)

    won = sum(1 for r in rows if r.won)
    lost = sum(1 for r in rows if r.resolved and not r.won)
    L.append("  outcome: {} acquired or public, {} inactive".format(won, lost))
    L.append("  {} permutations, labels shuffled WITHIN each batch year, seed {}".format(
        trials, seed))
    threshold = alpha(len(results))
    L.append("  Bonferroni across {} tests -> significant below p={:.4f}".format(
        len(results), threshold))
    L.append("")
    L.append("  {:<34}{:>10}{:>10}   {}".format("property", "diff", "p", "verdict"))
    for r in sorted(results, key=lambda x: x["p_value"]):
        mark = "SIGNIFICANT" if r["p_value"] < threshold else (
            "marginal" if r["p_value"] < 0.05 else "null")
        L.append("  {:<34}{:>+10.3f}{:>10.4f}   {}".format(
            r["label"], r["difference"], r["p_value"], mark))

    confound = None
    if any(r["key"] == CONFOUND_KEY and r["p_value"] < threshold for r in results):
        confound = confound_check(rows, trials=trials, seed=seed)
        if confound:
            L.append("")
            L.append("  control, same test on SINGLE-WORD names only ({} companies):".format(
                confound["n"]))
            L.append("  {:<34}{:>+10.3f}{:>10.4f}   {}".format(
                "letters in the name", confound["difference"], confound["p_value"],
                "SIGNIFICANT" if confound["p_value"] < threshold else
                ("marginal" if confound["p_value"] < 0.05 else "null")))

    L.append("")
    for line in _wrap("  read as: {}".format(verdict(results, threshold, confound)), 74):
        L.append(line)
    return "\n".join(L)


def _wrap(text, width):
    """A paragraph at `width`, continuation lines aligned under the first word. No textwrap
    import for four lines of output, and this keeps the hanging indent this file's tables use."""
    prefix = text[:len(text) - len(text.lstrip())]
    indent = prefix + " " * 9
    lines, cur = [], prefix
    for word in text.split():
        candidate = (cur + " " + word) if cur.strip() else (cur + word)
        if len(candidate) > width and cur.strip():
            lines.append(cur)
            cur = indent + word
        else:
            cur = candidate
    if cur.strip():
        lines.append(cur)
    return lines
