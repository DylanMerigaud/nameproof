"""What do the FIRST RESULTS actually say? The check that reads a real page.

WHY THIS EXISTS. Dylan, 2026-08-25: "ajoute un gate que les premiers resultat de la search ne
doivent pas etre du NSFW", then, when the first attempt tried to infer it from autocomplete: "tu
peux pas deriver de l'auto complete ce que la recherche va trouver. exemple wedpalette." He is
right and the repo already carries the proof: `normfin` had autocomplete blaming a bioinformatics
tool and the results page blaming a Pokemon. Autocomplete and the results page are two different
mechanisms that routinely disagree, so the only honest way to know what the first results are is
to read them.

WHAT IS READABLE, MEASURED 2026-08-25 RATHER THAN ASSUMED. With a plain stdlib client every door
is shut: google.com/search answers 200 with a JavaScript shell, DuckDuckGo's html. and lite.
endpoints answer 202 with an anti-bot challenge, Mojeek answers 403. With a stealth headless
browser the picture changes and not uniformly:

    Google    429 plus a /sorry/ captcha, even stealth. Still shut.
    Bing      200, ten results, domain in the `aria-label` of each `a.tilk`.
    DuckDuckGo 200, ten results, real URL inside the `uddg=` parameter.

So this module reads Bing and DuckDuckGo and never pretends to have read Google.

THE BOUNDARY THAT MATTERS, and it is exactly the case that started this. `msbrenew` comes back
CLEAN here: fincen.gov, fintrac-canafe.canada.ca, msrenewal.com, complyfactor.com. Both engines
read it as what it means, MSB renewal. Google does not: its results page corrects to `msbreewc`,
an adult creator two edits away, which is what Dylan actually hit. Query that corrected string
and this module fires immediately, onlyfans.com sitting fourth on both engines.

THE CORRECTION IS VERIFIED, NOT INFERRED, and it is not a locale artifact. Read through a real
browser on 2026-08-25 with `gl=us&hl=en&pws=0&safe=off`, Google answers the query `msbrenew`
with the line "These are results for msbreewc / Search instead for msbrenew" and then returns
Instagram, Pornhub, OnlyFans, X, TikTok, Famous Birthdays, xHamster, t.co, Fansly and XVideos.
Five adult platforms in the first ten. The first hypothesis on seeing `es.pornhub.com` in the
original screenshot was that a Spanish Google was to blame; forcing English and US parameters
disproves it, the rewrite happens either way. One caveat worth keeping: the page footer still
read "Urubamba, Peru - From your device", so `gl=us` sets the market parameter and does NOT
override IP geolocation. A true US read needs a US exit address.

READ THAT AS THE LIMIT: this catches a name whose results ARE adult. It does not catch a name
that Google CORRECTS INTO one, because the engine that does the correcting is the one that cannot
be read. That residue is why the skill still requires a human browser pass on every finalist, and
why `safety.serp_unchecked` keeps firing when this module cannot run.

NO NEW DEPENDENCY. The package promise is zero runtime dependencies, and a stealth browser is a
large one. So the fetcher is called as an EXTERNAL COMMAND when the machine has one and reported
as unavailable when it does not, the same way `seo.py` uses /usr/share/dict/words when present.
An absent fetcher degrades to "not checked", never to "clean".
"""
import json
import os
import re
import shutil
import subprocess
import urllib.parse

from .phonetics import Finding

# Where the stealth fetcher lives. An env var first because the path is machine-specific and
# this is a public repository: hardcoding one person's home directory would make the feature
# look broken for everybody else.
FETCHER_ENV = "NAMEPROOF_FETCHER"

ENGINES = {
    "bing": "https://www.bing.com/search?q={q}&count=15&setlang=en&cc=US",
    "duckduckgo": "https://html.duckduckgo.com/html/?q={q}&kp=-2",
}

# Adult platforms, matched on the REGISTRABLE DOMAIN and never on a substring of the page text.
# A domain is a fact about where the result points; a word in a snippet is an argument about what
# it means, and this check does not need to have that argument. Deliberately short: these are the
# destinations that actually rank for a name collision.
ADULT_DOMAINS = frozenset({
    "pornhub.com", "xvideos.com", "xnxx.com", "xhamster.com", "redtube.com", "youporn.com",
    "spankbang.com", "eporner.com", "motherless.com", "brazzers.com", "bangbros.com",
    "onlyfans.com", "fansly.com", "manyvids.com", "chaturbate.com", "stripchat.com",
    "bongacams.com", "cam4.com", "myfreecams.com", "livejasmin.com", "camsoda.com",
    "rule34.xxx", "nhentai.net", "e-hentai.org", "hanime.tv", "adultwork.com",
    "erome.com", "coomer.su", "kemono.su", "fapello.com", "thothub.to",
})

# TLDs whose entire purpose is adult content. A result on one of these needs no further argument.
ADULT_TLDS = ("xxx", "adult", "porn", "sex", "cam", "tube")


class Unavailable(Exception):
    """No stealth fetcher on this machine. A distinct type because the caller must be able to
    tell "there is nothing adult here" from "nothing was looked at", and those two collapsing
    into one another is the exact failure that let `msbrenew` reach a shortlist."""


def fetcher_path():
    """The stealth fetcher command, or None.

    `NAMEPROOF_FETCHER` should hold the full command, interpreter included, for example
    `/path/to/venv/bin/python /path/to/scrape_url.py`. Split on whitespace so a bare executable
    on PATH also works.
    """
    raw = os.environ.get(FETCHER_ENV, "").strip()
    if not raw:
        return None
    parts = raw.split()
    exe = parts[0]
    if os.path.isfile(exe) or shutil.which(exe):
        return parts
    return None


def _registrable(netloc):
    """Last two labels of the host, lowercased, port and userinfo stripped.

    Not a public-suffix implementation and does not need to be: every entry in `ADULT_DOMAINS`
    is a two-label domain, so `es.pornhub.com` and `www.onlyfans.com` both reduce correctly. A
    real PSL would be a data dependency for no gain here.
    """
    host = netloc.split("@")[-1].split(":")[0].lower().strip(".")
    parts = [p for p in host.split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def parse_bing(html_text):
    """Result domains from a Bing page.

    Bing wraps every result href in a `bing.com/ck/a?` redirect, so the destination is not in the
    link at all. The domain sits in the `aria-label` of the `a.tilk` title anchor, which is why
    this parser reads an accessibility attribute rather than an href.
    """
    return [m.lower() for m in re.findall(r'<a class="tilk" aria-label="([^"]+)"', html_text)]


def parse_duckduckgo(html_text):
    """Result domains from a DuckDuckGo html page. The real URL is inside the `uddg` parameter
    of the redirect, percent-encoded."""
    out = []
    for href in re.findall(r'class="result__a"[^>]*href="([^"]+)"', html_text):
        href = href.replace("&amp;", "&")
        if "uddg=" in href:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            href = qs.get("uddg", [href])[0]
        out.append(urllib.parse.urlparse(href).netloc)
    return [h for h in out if h]


PARSERS = {"bing": parse_bing, "duckduckgo": parse_duckduckgo}


def fetch(url, timeout=120):
    cmd = fetcher_path()
    if not cmd:
        raise Unavailable(
            "no stealth fetcher configured. Set {} to the command that renders a page, for "
            "example '/path/to/venv/bin/python /path/to/scrape_url.py'".format(FETCHER_ENV))
    proc = subprocess.run(cmd + [url, "--html"], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise Unavailable("fetcher failed on {}: {}".format(
            url, (proc.stderr or "no output").strip()[:120]))
    return proc.stdout


def results(name, engines=("bing", "duckduckgo"), timeout=120):
    """{engine: [domain, ...]} for the first page. Raises `Unavailable` if nothing could run."""
    out = {}
    errors = []
    for engine in engines:
        url = ENGINES[engine].format(q=urllib.parse.quote(name))
        try:
            out[engine] = PARSERS[engine](fetch(url, timeout))
        except Exception as exc:                             # noqa: BLE001
            errors.append("{}: {}".format(engine, exc))
    if not out:
        raise Unavailable("; ".join(errors) or "no engine answered")
    return out


def adult_hits(domains):
    hits = []
    for host in domains:
        reg = _registrable(host)
        if reg in ADULT_DOMAINS or reg.rsplit(".", 1)[-1] in ADULT_TLDS:
            hits.append(host)
    return hits


def analyse(name, engines=("bing", "duckduckgo"), timeout=120):
    """The gate, on what a real search actually returns.

    Weight 5 and code `NSFW_SERP`, which `phonetics.VETO_CODES` treats as a veto: a name whose
    first page of results is an adult platform is not a name with a drawback.
    """
    try:
        found = results(name, engines, timeout)
    except Unavailable as exc:
        return [Finding("SERP_UNCHECKED", 0,
                        "the first results were NOT read ({}). Not a pass: this is the one "
                        "dimension that cannot be inferred from anything else.".format(exc))]

    hits = {}
    for engine, domains in found.items():
        got = adult_hits(domains)
        if got:
            hits[engine] = got
    if not hits:
        checked = ", ".join("{} ({} results)".format(e, len(d)) for e, d in sorted(found.items()))
        return [Finding("SERP_CLEAN", 0,
                        "first results read and no adult platform among them: {}. Note this is "
                        "Bing and DuckDuckGo; Google cannot be read and is the engine that "
                        "rewrites a near-miss name into somebody else's.".format(checked))]
    return [Finding(
        "NSFW_SERP", 5,
        "the first page of results carries an adult platform: {}. This is not what the name "
        "means, it is what a person searching it actually gets.".format(
            "; ".join("{} -> {}".format(e, ", ".join(sorted(set(d))))
                      for e, d in sorted(hits.items()))))]
