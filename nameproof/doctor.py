"""Do the live checks still agree with reality?

WHY THIS EXISTS, and it is the most useful file in the repo. Over one afternoon this tool
shipped six wrong answers in a row: substring instead of whole word, half a fix applied, Google
queried as the wrong country, a ratio read backwards, a redirector contradicting the module's
own premise, and a flag that parsed but changed nothing. **Not one of them crashed.** Every
single one returned confident, plausible, wrong output.

Unit tests did not catch any of them, and could not have: they test the code against the
author's beliefs, and the author's beliefs were the bug. What was missing was GROUND TRUTH, real
names whose verdict is known from the world rather than from this tool.

So `corpora/calibration.jsonl` holds cases with known answers, each carrying the failure it
guards. `doctor` runs them against the live checks and reports disagreement. It talks to the
network on purpose: it is not a unit test, it is a claim that the tool still describes reality.

Run it before trusting a batch of results, and after touching any check.

  nameproof doctor
"""
import json
import os

from . import availability, search, seo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(HERE, "corpora", "calibration.jsonl")


def load_cases(path=CASES):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "_comment" in row:
                continue
            out.append(row)
    return out


def run_case(case):
    """(ok, observed, detail). `ok` is None when the check could not run at all."""
    kind = case["check"]
    name = case["name"]
    expect = case["expect"]

    if kind == "hijack":
        found = search.hijack(name, launched=case.get("launched", False))
        if found and found[0].code == "SEARCH_UNKNOWN":
            return None, "unknown", found[0].detail
        observed = "flag" if found else "clean"
        detail = found[0].detail if found else "no finding"
    elif kind == "dictionary":
        found = seo.dictionary_word(name)
        observed = "flag" if found else "clean"
        detail = found[0].detail if found else "no finding"
    elif kind == "collision":
        found = seo.brand_collision(name)
        if found and found[0].code == "COLLISION_UNKNOWN":
            return None, "unknown", found[0].detail
        observed = "flag" if found else "clean"
        detail = found[0].detail if found else "no finding"
    elif kind == "domain":
        stem, _, tld = name.rpartition(".")
        status = availability.domain(stem, tld).status
        if status == availability.UNKNOWN:
            return None, "unknown", "registry did not answer"
        observed = status
        detail = "registry says {}".format(status)
    else:
        return None, "unknown", "unknown check kind {!r}".format(kind)

    return observed == expect, observed, detail


def run(path=CASES, verbose=False):
    cases = load_cases(path)
    passed, failed, skipped = [], [], []
    for case in cases:
        ok, observed, detail = run_case(case)
        row = (case, observed, detail)
        (skipped if ok is None else passed if ok else failed).append(row)

    print("nameproof doctor: {} live case(s) against known answers".format(len(cases)))
    print("-" * 74)
    for case, observed, detail in failed:
        print("FAIL  {:<10} {:<11} expected {:<7} got {}".format(
            case["check"], case["name"][:11], case["expect"], observed))
        print("      what this case guards: {}".format(case["why"][:150]))
        print("      the tool said: {}".format(detail[:150]))
        print()
    for case, observed, detail in skipped:
        print("SKIP  {:<10} {:<11} could not run: {}".format(
            case["check"], case["name"][:11], detail[:60]))
    if verbose:
        for case, observed, detail in passed:
            print("ok    {:<10} {:<11} {}".format(case["check"], case["name"][:11], observed))

    print("-" * 74)
    print("{} agreed, {} disagreed, {} could not run".format(
        len(passed), len(failed), len(skipped)))
    if failed:
        print()
        print("A disagreement here is not a flaky test. Each case is a real name whose answer")
        print("is known from the world, so a check that no longer reproduces it has drifted,")
        print("and every result it produced since is suspect.")
    return 1 if failed else 0
