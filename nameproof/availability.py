"""Is the name free, on the surfaces that actually block a launch?

WHY THIS EXISTS AT ALL, given that `tldx` already does bulk availability well: because a domain
is only one of four things that can stop you, and it is not the one that stops you most often.
A name whose npm package is taken is a name you cannot ship under, whatever the domain says.

WHY RDAP AND NOT A REGISTRAR SEARCH BOX. RDAP (RFC 7482, the protocol that replaced WHOIS) is
served by the REGISTRY. A registrar's search box is a marketing funnel, and domain front running
(a search leaking to somebody who registers the name before you) has been a live accusation
against that channel for two decades. Querying the registry directly is both the authoritative
answer and the quiet one. 200 means registered, 404 means the registry has no record.

WHY NOT DNS. A DNS lookup is not an availability check. A registered domain with no nameservers
returns NXDOMAIN and looks free. Plenty of tools get this wrong; it is worth stating out loud.
"""
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import tld_risk

UA = "nameproof (https://github.com/nameproof/nameproof)"

TAKEN, FREE, UNKNOWN = "taken", "free", "unknown"


class Check:
    def __init__(self, surface, status, detail=""):
        self.surface = surface
        self.status = status
        self.detail = detail

    def __repr__(self):
        return "Check({}, {})".format(self.surface, self.status)


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def _exists(url, timeout=15):
    """200 means the record exists, 404 means it does not. Anything else is UNKNOWN.

    UNKNOWN is a real answer and it is never silently folded into FREE. A rate limit that reads
    as 'available' is how a tool tells you to go register a name somebody already owns.
    """
    try:
        status, _ = _get(url, timeout)
        return TAKEN if status == 200 else UNKNOWN
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return FREE
        return UNKNOWN
    except Exception:                                        # noqa: BLE001
        return UNKNOWN


def domain(name, tld="com"):
    """Availability, plus the thing nobody reports: whether the TLD itself is a safe bet.

    A ccTLD is leased from a sovereign. Four have already been retired when their territory
    dissolved. Reporting availability without reporting that exposure is half an answer."""
    d = "{}.{}".format(name.lower(), tld)
    st = _exists("https://rdap.org/domain/{}".format(d))
    detail = "RDAP registry lookup"
    risk = tld_risk.rate(tld)
    if risk and risk[0] != tld_risk.LOW:
        detail += "  |  TLD RISK {}".format(tld_risk.annotate(tld))
    return Check("{}".format(d), st, detail)


def pypi(name):
    return Check("pypi", _exists("https://pypi.org/pypi/{}/json".format(name.lower())),
                 "package index")


def npm(name):
    return Check("npm", _exists("https://registry.npmjs.org/{}".format(name.lower())),
                 "package index")


def crates(name):
    return Check("crates.io", _exists("https://crates.io/api/v1/crates/{}".format(name.lower())),
                 "package index")


def github(name):
    """Homonym repos, which is a different question from 'is the org name free'.

    What sinks an OSS project is not that the name is registered, it is that searching for it
    surfaces somebody else. So this reports the number of exact-name repos and the best starred
    one, and leaves the judgement to the caller.
    """
    url = ("https://api.github.com/search/repositories?q={}+in:name&per_page=20".format(
        name.lower()))
    try:
        status, body = _get(url, 25)
        if status != 200:
            return Check("github", UNKNOWN, "search API returned {}".format(status))
        items = json.loads(body).get("items", [])
    except Exception as exc:                                 # noqa: BLE001
        return Check("github", UNKNOWN, str(exc)[:60])
    exact = [i for i in items if i["full_name"].split("/")[-1].lower() == name.lower()]
    if not exact:
        return Check("github", FREE, "no repo carries this exact name")
    top = max(exact, key=lambda i: i["stargazers_count"])
    return Check("github", TAKEN,
                 "{} exact-name repo(s), best is {} at {} stars".format(
                     len(exact), top["full_name"], top["stargazers_count"]))


SURFACES = {"com": lambda n: domain(n, "com"),
            "io": lambda n: domain(n, "io"),
            "dev": lambda n: domain(n, "dev"),
            "pypi": pypi,
            "npm": npm,
            "crates": crates,
            "github": github}


def check(name, surfaces=("com", "pypi", "npm", "github")):
    """All surfaces in parallel. Order of the result follows the order asked for."""
    fns = [SURFACES[s] for s in surfaces if s in SURFACES]
    with ThreadPoolExecutor(max_workers=len(fns) or 1) as ex:
        return list(ex.map(lambda f: f(name), fns))
