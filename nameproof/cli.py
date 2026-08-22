"""nameproof: proofread a product name before you commit to it.

Four commands, because there are only four questions worth asking about a candidate name:

  score      is it a good name (phonetics, shape, reading traps)
  check      is it free (domain, package registries, GitHub homonyms)
  market     what do the names that already won in this space look like
  generate   produce candidates instead of judging ones you already have

`score`, `market` and `generate` work offline. Only `check` touches the network.
"""
import argparse
import sys

from concurrent.futures import ThreadPoolExecutor

from . import availability, corpus, doctor, generate, search, seo
from .phonetics import Finding, analyse, grade as _grade

BAR = "-" * 66


def cmd_score(args):
    market = None
    if args.market:
        market = corpus.CorpusReport(corpus.load(args.market))
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
    names = corpus.load(args.file)
    print(corpus.CorpusReport(names).render(args.file))
    return 0


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

    pool = []
    seen = set()
    for label, fn in techniques:
        kwargs = {"n": args.count, "seed": args.seed}
        if label == "roots" and getattr(args, "roots", None):
            kwargs["roots_file"] = args.roots
        for name in fn(**kwargs):
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            findings = analyse(name)
            grade, total = _grade(findings)
            pool.append({"name": name, "how": label, "grade": grade,
                         "penalty": total, "findings": findings})

    if args.score:
        pool = [c for c in pool if c["grade"] in ("A", "B")]

    # Availability LAST, because it is the only step that costs network time, and as a BONUS
    # rather than a gate. Dylan, 2026-08-21: "com nu libre huge bonus, pas necessary". Filtering
    # hard on it throws away good names, and the whole tool is a ranking with reasons rather
    # than a set of binary doors. So a free bare .com pulls a name UP the list by carrying a
    # negative weight, and a taken one costs nothing at all: plenty of good products live at
    # getsomething.com.
    if args.available:
        # Two workers, not four: RDAP throttles above that and the retries then cost
        # more wall clock than the parallelism saved.
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

    pool.sort(key=lambda c: (c["penalty"], c["name"].lower()))
    if not pool:
        print("nothing survived the filters. Raise --count or drop a filter.")
        return 0

    print("\n{:<4} {:<16} {:<9} {:<12} {}".format(
        "", "name", "score", "technique", "bare .com" if args.available else ""))
    print(BAR)
    for c in pool:
        print("{:<4} {:<16} {:<9} {:<12} {}".format(
            c["grade"], c["name"], c["penalty"], c["how"],
            c.get("com", "") if args.available else ""))
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
    m.add_argument("file", help="one competitor name per line")
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
    g_.add_argument("--score", action="store_true",
                    help="run each name through phonetics.analyse, keep only grade A or B")
    g_.set_defaults(func=cmd_generate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
