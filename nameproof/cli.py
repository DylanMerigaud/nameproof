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

from . import availability, corpus, generate, seo
from .phonetics import analyse, grade as _grade

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
    if not args.all and not args.technique:
        print("generate needs --technique <name> or --all. Techniques: {}".format(
            ", ".join(sorted(generate.TECHNIQUES))))
        return 2
    techniques = (sorted(generate.TECHNIQUES.items()) if args.all
                 else [(args.technique, generate.TECHNIQUES[args.technique])])
    for label, fn in techniques:
        names = fn(n=args.count, seed=args.seed)
        print("\n{}  ({} generated)".format(label, len(names)))
        print(BAR)
        shown = 0
        for name in names:
            if not args.score:
                print("  {}".format(name))
                shown += 1
                continue
            g, total = _grade(analyse(name))
            if g in ("A", "B"):
                print("  {}  {}  (penalty {})".format(g, name, total))
                shown += 1
        if shown == 0:
            print("  nothing to show" + (" at grade A or B" if args.score else ""))
    return 0


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
                   help="with --seo, skip the Wikidata brand-collision lookup")
    s.set_defaults(func=cmd_score)

    c = sub.add_parser("check", help="is the name free on the surfaces that block a launch")
    c.add_argument("names", nargs="+")
    c.add_argument("--surfaces", default="com,pypi,npm,github",
                   help="comma separated: com,io,dev,pypi,npm,crates,github")
    c.set_defaults(func=cmd_check)

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
    g_.add_argument("--score", action="store_true",
                    help="run each name through phonetics.analyse, keep only grade A or B")
    g_.set_defaults(func=cmd_generate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
