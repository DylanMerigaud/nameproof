"""nameproof: proofread a product name before you commit to it.

Five commands, because there are only five questions worth asking about a candidate name:

  score      is it a good name (phonetics, shape, reading traps)
  check      is it free (domain, package registries, GitHub homonyms)
  market     what do the names that already won in this space look like
  generate   produce candidates instead of judging ones you already have
  gold       produce a name that stands on its own, not tied to any product

`score`, `market`, `generate` and `gold` work offline. Only `check` touches the network, and the
`--available` flag on `generate`/`gold` does too, since it is a bare .com RDAP lookup.
"""
import argparse
import sys

from concurrent.futures import ThreadPoolExecutor

from . import availability, corpus, doctor, generate, gold, search, seo
from .phonetics import Finding, analyse, grade as _grade

BAR = "-" * 66


def cmd_score(args):
    market, _ = _market_profile(args.market)
    keywords = args.keywords.split(",") if args.keywords else ()
    rows = []
    for name in args.names:
        findings = analyse(name)
        if market:
            findings = findings + corpus.fits(name, market)
        if args.seo:
            findings = findings + seo.analyse(name, keywords, online=not args.offline)
        if args.search and not args.offline:
            findings = findings + search.hijack(name, gl=args.country)
        findings.sort(key=lambda f: -f.weight)
        grade, total = _grade(findings)
        rows.append((name, grade, total, findings))

    rows.sort(key=lambda r: r[2])
    for name, grade, total, findings in rows:
        print("\n{}  {}  (penalty {})".format(grade, name, total))
        print(BAR)
        if not findings:
            print("  nothing to report. It spells the way it sounds.")
        for f in findings:
            print("  [{}] {:<16} {}".format(f.weight, f.code, f.detail))
    return 0


def cmd_check(args):
    surfaces = args.surfaces.split(",")
    for name in args.names:
        print("\n{}".format(name))
        print(BAR)
        for c in availability.check(name, surfaces):
            mark = {"free": "FREE ", "taken": "TAKEN", "unknown": "  ?  "}[c.status]
            print("  {}  {:<14} {}".format(mark, c.surface, c.detail))
    return 0


def cmd_market(args):
    """One corpus, or several side by side.

    Several, because this tool's best finding was made by hand. The README reports that SOC 2
    compliance sold as a PRODUCT names the category 10% of the time while investment adviser
    compliance sold as a SERVICE does it 50% of the time, and that product companies and service
    firms therefore do not name themselves the same way. A human produced that by running this
    command twice and diffing the output by eye: nothing guarded it, and nobody could reproduce
    it without being told how. `market a.txt b.txt` states it.
    """
    reports = [corpus.CorpusReport(corpus.load(f), label=f) for f in args.files]
    for r in reports:
        print(r.render())
        print()
    if len(reports) > 1:
        print(corpus.compare(reports))
    return 0


def _market_profile(path):
    """The corpus behind `--market`, as both halves: the report that scores fit and the profile
    that shapes generation. Returned together because a run using one without the other would
    either produce market-shaped names ranked by a market-blind rule, or the reverse."""
    if not path:
        return None, None
    report = corpus.CorpusReport(corpus.load(path), label=path)
    return report, corpus.profile(report, path)


def _apply_available_bonus(pool):
    """Bare .com availability, checked LAST because it is the only step that costs network
    time, and applied as a BONUS rather than a gate. Dylan, 2026-08-21: "com nu libre huge
    bonus, pas necessary". Filtering hard on it throws away good names; a free bare .com pulls
    a name UP the list via a negative-weight finding, a taken one costs nothing. Shared by
    `generate` and `gold` so the two commands' rankings agree on what a free .com is worth, and
    because both are also a BONUS by construction the sort below never needs a special case for
    "free first": every GOLD candidate that clears the profile sits at penalty 0-2, and the
    -3 bonus always drops a free one below that floor.
    """
    with ThreadPoolExecutor(max_workers=2) as ex:
        for c, st in zip(pool, ex.map(
                lambda x: availability.domain(x["name"], "com").status, pool)):
            c["com"] = st
            if st == availability.FREE:
                c["findings"] = c["findings"] + [Finding(
                    "BARE_COM_FREE", -3,
                    "the bare .com is free, no prefix and no suffix needed. That is rare "
                    "enough in 2026 to be worth real points.")]
                c["grade"], c["penalty"] = _grade(c["findings"])


def _print_pool(pool, show_available):
    """One ranked table, shared by `generate` and `gold` so a candidate reads the same way
    regardless of which command produced it."""
    print("\n{:<4} {:<16} {:<9} {:<12} {}".format(
        "", "name", "score", "technique", "bare .com" if show_available else ""))
    print(BAR)
    for c in pool:
        print("{:<4} {:<16} {:<9} {:<12} {}".format(
            c["grade"], c["name"], c["penalty"], c["how"],
            c.get("com", "") if show_available else ""))


def cmd_generate(args):
    """Generate, then RANK. Never a list per technique.

    The first version printed one block per technique, which is unreadable: four separate lists
    cannot be compared, and the reader has to do the ranking the tool exists to do. Pooling
    everything and sorting by penalty means the best name is the first line, whichever technique
    produced it, and the technique becomes a label rather than a section heading.
    """
    if not args.all and not args.technique:
        print("generate needs --technique <name> or --all. Techniques: {}".format(
            ", ".join(sorted(generate.TECHNIQUES))))
        return 2
    techniques = (sorted(generate.TECHNIQUES.items()) if args.all
                  else [(args.technique, generate.TECHNIQUES[args.technique])])

    report, profile = _market_profile(args.market)
    if profile:
        print("\n  " + profile.describe())

    pool = []
    seen = set()
    for label, fn in techniques:
        kwargs = {"n": args.count, "seed": args.seed, "profile": profile}
        if label == "roots" and getattr(args, "roots", None):
            kwargs["roots_file"] = args.roots
        for name in fn(**kwargs):
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            findings = analyse(name)
            # `score --market` keeps fit findings OUT of the penalty on purpose: breaking a
            # market's pattern is a positioning choice and the tool has no business overruling
            # a name the user already picked. Here it is the opposite. The user asked for
            # candidates shaped like this market, so distance FROM it is the thing being
            # ranked, and leaving it out would produce market-shaped names ordered by a
            # market-blind rule.
            if report:
                findings = findings + corpus.fits(name, report)
            grade, total = _grade(findings)
            pool.append({"name": name, "how": label, "grade": grade,
                         "penalty": total, "findings": findings})

    if args.score:
        pool = [c for c in pool if c["grade"] in ("A", "B")]

    # Two workers, not four: RDAP throttles above that and the retries then cost more wall
    # clock than the parallelism saved.
    if args.available:
        _apply_available_bonus(pool)

    pool.sort(key=lambda c: (c["penalty"], c["name"].lower()))
    if not pool:
        print("nothing survived the filters. Raise --count or drop a filter.")
        return 0

    _print_pool(pool, args.available)
    print("\n{} candidate(s), best first.".format(len(pool)))
    return 0


def cmd_gold(args):
    """Names as a RESERVE, not a label for a product already picked.

    Dylan, 2026-08-24: renaming a shipped product is a failure, never a plan B, and a name kept
    independent of any one bet is an asset that avoids that failure. So `gold` pools
    `phonotactic`, `markov` and `roots` off `gold.GOLD_ROOTS` (a wide, positive lexicon embedded
    for this command, not the generic `generate.ROOTS`), skipping `rare` on purpose: a
    2026-08-24/25 measurement across four real products found short real-word candidates almost
    entirely taken, so the technique that only ever proposes real words is spending the count
    budget on a register already disqualified.

    Every candidate then has to clear `gold.passes_profile`, a harder gate than `generate
    --score`'s plain grade cut: 4 to 9 letters, 2 to 3 syllables, no digit, no hyphen, no niche
    vertical morpheme, on top of the same phonetic pronounceability gate `score` uses. This is a
    reserve for a bet nobody has named yet, so a fragment that already reads as one vertical
    (compliance jargon, a category word) is exactly what this gate exists to keep out.
    """
    report, profile = _market_profile(args.market)
    if profile:
        print("\n  " + profile.describe())

    pool = []
    seen = set()
    for label, fn in sorted(gold.TECHNIQUES.items()):
        for name in fn(n=args.count, seed=args.seed, profile=profile):
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            if not gold.passes_profile(name, args.min_length, args.max_length):
                continue
            findings = analyse(name)
            # Same reasoning as `generate --market`, with one extra consequence worth naming: a
            # GOLD name is supposed to outlive one bet, so asking for one shaped by a market is
            # a deliberate narrowing. The GOLD gate still runs on top, which means the two can
            # disagree and the strictest wins, and an empty result is the honest outcome when a
            # market's shape and the GOLD profile have no overlap.
            if report:
                findings = findings + corpus.fits(name, report)
            g, total = _grade(findings)
            pool.append({"name": name, "how": label, "grade": g, "penalty": total,
                         "findings": findings})

    if args.available:
        _apply_available_bonus(pool)

    if not pool:
        print("nothing survived the GOLD profile. Raise --count, widen --min-length/"
              "--max-length, or try another --seed.")
        return 0

    # No special "free first" sort needed: every survivor of the profile sits at penalty 0-2
    # (grade A or B), and `_apply_available_bonus` drops a free .com to -3 to -1, always below
    # that floor. Same sort as `generate`, on purpose: same format, same ranking rule.
    pool.sort(key=lambda c: (c["penalty"], c["name"].lower()))
    _print_pool(pool, args.available)
    print("\n{} candidate(s), best first.".format(len(pool)))
    return 0


def cmd_doctor(args):
    return doctor.run(verbose=args.verbose)


def main(argv=None):
    p = argparse.ArgumentParser(prog="nameproof", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="judge a name on phonetics and shape, offline")
    s.add_argument("names", nargs="+")
    s.add_argument("--market", help="a corpus file to compare the shape against")
    s.add_argument("--seo", action="store_true",
                   help="add the SEO findings: dictionary-word risk and brand collision")
    s.add_argument("--keywords", help="comma separated category words, to flag keyword stuffing")
    s.add_argument("--offline", action="store_true",
                   help="skip every network lookup")
    s.add_argument("--search", action="store_true",
                   help="ask Google whether it keeps your spelling or corrects it away")
    s.add_argument("--country", default="us",
                   help="which Google to ask, as a country code. Default us, and it MATTERS: "
                        "the same name gets a completely different answer from Lima and from "
                        "New York")
    s.set_defaults(func=cmd_score)

    c = sub.add_parser("check", help="is the name free on the surfaces that block a launch")
    c.add_argument("names", nargs="+")
    c.add_argument("--surfaces", default="com,pypi,npm,github",
                   help="comma separated: com,io,dev,pypi,npm,crates,github")
    c.set_defaults(func=cmd_check)

    d = sub.add_parser("doctor",
                       help="do the live checks still agree with reality? runs real names "
                            "with known answers against the network")
    d.add_argument("--verbose", action="store_true", help="also list the cases that agreed")
    d.set_defaults(func=cmd_doctor)

    m = sub.add_parser("market", help="describe the naming conventions of a market")
    m.add_argument("files", nargs="+",
                   help="one competitor name per line. Pass several corpora to get the "
                        "comparison as well as the descriptions")
    m.set_defaults(func=cmd_market)

    g_ = sub.add_parser("generate", help="produce candidate names, deterministic and offline")
    g_.add_argument("--technique", choices=sorted(generate.TECHNIQUES),
                    help="one of: {}".format(", ".join(sorted(generate.TECHNIQUES))))
    g_.add_argument("--all", action="store_true", help="run every technique")
    g_.add_argument("--count", type=int, default=20, help="names to generate per technique")
    g_.add_argument("--seed", type=int, default=42,
                    help="same seed and count always produce the same names")
    g_.add_argument("--roots",
                    help="a root lexicon file for the roots technique: 'root meaning' per "
                         "line. The built-in roots are generic on purpose; bring your own "
                         "field's vocabulary and the output starts meaning something")
    g_.add_argument("--available", action="store_true",
                    help="keep only names whose BARE .com is free. No get- or -hq trick: if it "
                         "needs a prefix it does not make the list")
    g_.add_argument("--market", help="{}".format('a corpus file of names that already won in this market. Shapes the candidates AT GENERATION TIME (vowel-final rate, syllable count and length band are taken from the corpus instead of from constants) and folds fit-against-the-market into the ranking'))
    g_.add_argument("--score", action="store_true",
                    help="run each name through phonetics.analyse, keep only grade A or B")
    g_.set_defaults(func=cmd_generate)

    go = sub.add_parser("gold", help="find a name that stands on its own, not tied to any "
                                     "product: short, pronounceable, wide, resellable")
    go.add_argument("--count", type=int, default=30,
                    help="names to generate per technique, before the GOLD profile filter")
    go.add_argument("--seed", type=int, default=42,
                    help="same seed and count always produce the same names")
    go.add_argument("--min-length", type=int, default=4, dest="min_length",
                    help="shortest letter count the GOLD profile keeps")
    go.add_argument("--max-length", type=int, default=9, dest="max_length",
                    help="longest letter count the GOLD profile keeps")
    go.add_argument("--market", help="{}".format('a corpus file of names that already won in this market. Shapes the candidates AT GENERATION TIME (vowel-final rate, syllable count and length band are taken from the corpus instead of from constants) and folds fit-against-the-market into the ranking'))
    go.add_argument("--available", action="store_true",
                    help="check the bare .com and rank a free one to the top (network)")
    go.set_defaults(func=cmd_gold)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
