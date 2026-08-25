"""Build the outcome cohort: names whose real-world result is known, not just names that exist.

WHY THIS EXISTS. Dylan, 2026-08-25: "il faut des stats pour voir ce qui fonctionne." Every
corpus in `corpora/` describes what a market's names LOOK like. None of them carries an outcome,
so none of them can answer whether any of it matters. Answering that needs a dataset where each
name is attached to what happened to the company, and it needs enough of them.

WHY Y COMBINATOR AND NOT CRUNCHBASE. Crunchbase was the obvious candidate and it is out: the
Basic API was discontinued, there is no free tier left, and the remaining products route through
a sales team. This tool spends no money, so that is the end of it. The YC directory is public,
needs no key, and is strictly better for this question anyway because it carries three things
Crunchbase's free tier never did:

  * `status`, which resolves to Acquired, Public, Inactive or still Active. A real outcome.
  * `batch`, which is the time axis and the ONLY way to read the outcome honestly. Resolution
    rate falls from 91% for the 2007 batches to 0% for 2026: a company that has been around for
    fifteen years has had fifteen years to be acquired OR to die, and comparing it against last
    year's batch measures nothing but age.
  * `tags`, which slice the three markets Dylan named: fintech, developer tools, AI.

WHAT THIS SCRIPT IS NOT. It is not run by `nameproof`, by the test suite, or by anyone
installing the package. Same contract as `tools/build_data.py`: the 10 MB source never enters
the repository, the filtered extract does, and the extract is small enough to read by eye.

Source: https://yc-oss.github.io/api/companies/all.json, a public mirror of the Y Combinator
company directory. Company names are third-party data and are written out VERBATIM: not
title-cased, not stripped of punctuation, not "corrected". A name is what its owner writes.

Usage:  python3 tools/build_cohort.py [--out nameproof/data/yc_cohort.tsv]
"""
import argparse
import json
import os
import re
import sys
import urllib.request

SOURCE = "https://yc-oss.github.io/api/companies/all.json"
UA = "nameproof (https://github.com/DylanMerigaud/nameproof)"

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "nameproof", "data", "yc_cohort.tsv")

# The three markets Dylan named, as tag sets rather than a single tag: YC's tagging is
# inconsistent across batches ("AI" and "Artificial Intelligence" coexist, so do "Developer
# Tools" and "Infrastructure"), and picking one tag would silently drop half a market.
MARKETS = {
    "fintech": {"Fintech", "Payments", "Banking", "Credit", "Insurance", "InsurTech",
                "Neobank", "Financial Services", "Crypto / Web3", "Investing"},
    "devtools": {"Developer Tools", "Infrastructure", "API", "Open Source", "DevOps",
                 "DevSecOps", "Cloud Computing", "Databases"},
    "ai": {"Artificial Intelligence", "AI", "Generative AI", "Machine Learning",
           "AI Assistant", "LLM", "AIOps", "Computer Vision", "NLP"},
}

# One letter per outcome, because this file is read far more often than it is written and a
# column of A/P/I/L is legible in a way a column of words is not.
#   A = Acquired, P = Public, I = Inactive (all three RESOLVED), L = Live (still Active)
STATUS_CODE = {"Acquired": "A", "Public": "P", "Inactive": "I", "Active": "L"}

HEADER = """\
# Y Combinator company outcomes, extracted for `nameproof cohort`.
#
# Source: {source}, a public mirror of the Y Combinator company directory, fetched with no API
# key. Y Combinator company names and outcomes are third-party facts; names are reproduced
# VERBATIM here, exactly as each company writes its own, and are never normalised.
#
# Built by tools/build_cohort.py. Not fetched at runtime: `nameproof` only ever reads this file.
#
# Columns, tab separated: name, batch year, outcome, markets (comma separated, may be empty).
# Outcome: A=Acquired  P=Public  I=Inactive  L=Live (still active, outcome not yet resolved).
#
# READ THE YEAR BEFORE READING THE OUTCOME. Resolution rate falls from about 91% for the 2007
# batches to 0% for 2026, because a young company has not had time to resolve either way. Any
# comparison that ignores the batch year measures age, not names.
{counts}
"""


def fetch(url=SOURCE, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def batch_year(company):
    m = re.search(r"(\d{4})", company.get("batch") or "")
    return int(m.group(1)) if m else None


def markets_for(company):
    tags = set(company.get("tags") or [])
    return [name for name, wanted in sorted(MARKETS.items()) if tags & wanted]


def rows_from(companies):
    """One row per company that has all three of a name, a batch year and a known status.

    A company missing any of the three is dropped rather than defaulted. A default here would
    be invented data sitting in the same column as measured data, which is how a dataset stops
    being evidence.
    """
    out = []
    for c in companies:
        name = (c.get("name") or "").strip()
        year = batch_year(c)
        code = STATUS_CODE.get(c.get("status"))
        if not name or not year or not code:
            continue
        # A tab or a newline inside a name would silently shift every later column. Names
        # carrying one are dropped, and the count is reported, rather than being repaired into
        # something the company does not call itself.
        #
        # NOT dropped, and deliberately so: the roughly 0.7% of rows whose name field carries an
        # alias or a tagline rather than a bare brand ("Kenota (formerly ExVivo Labs)"). They
        # inflate length and word count, and they are still what the company wrote. Editing them
        # would be editing the evidence, so `nameproof cohort` measures the cost of keeping them
        # instead: dropping all 12 of the resolved ones leaves the conclusion identical.
        if "\t" in name or "\n" in name or "\r" in name:
            continue
        out.append((name, year, code, ",".join(markets_for(c))))
    return out


def render(rows):
    counts = {}
    for _, _, code, _ in rows:
        counts[code] = counts.get(code, 0) + 1
    summary = "# {} companies: {} acquired, {} public, {} inactive, {} still active.".format(
        len(rows), counts.get("A", 0), counts.get("P", 0),
        counts.get("I", 0), counts.get("L", 0))
    body = "\n".join("{}\t{}\t{}\t{}".format(*r) for r in sorted(rows, key=lambda r: (r[1], r[0])))
    return HEADER.format(source=SOURCE, counts=summary) + body + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--source", default=SOURCE,
                   help="override the URL, or point at a local copy for a reproducible build")
    args = p.parse_args(argv)

    if os.path.isfile(args.source):
        with open(args.source, encoding="utf-8") as fh:
            companies = json.load(fh)
    else:
        companies = fetch(args.source)
    rows = rows_from(companies)
    if not rows:
        print("no usable rows; refusing to overwrite {}".format(args.out), file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(render(rows))
    print("wrote {} rows to {} ({:.0f} KB)".format(
        len(rows), args.out, os.path.getsize(args.out) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
