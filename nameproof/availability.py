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
import time
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


# RDAP rate limits, and it does so exactly when the tool is most useful: checking sixty
# generated names at once. Measured 2026-08-21, four concurrent workers over 61 names returned
# UNKNOWN on most of them, which is honest but useless. Retrying with a backoff turns a
# throttled batch into a real answer, and throttling is precisely the case a retry fixes.
RETRY_CODES = (429, 500, 502, 503, 504)


def _exists(url, timeout=15, attempts=3):
    """200 means the record exists, 404 means it does not. Anything else is UNKNOWN.

    UNKNOWN is a real answer and it is never silently folded into FREE. A rate limit that reads
    as 'available' is how a tool tells you to go register a name somebody already owns. So a
    throttle is RETRIED rather than reinterpreted: the answer stays honest, it just takes longer
    to get.
    """
    delay = 1.0
    for attempt in range(attempts):
        try:
            status, _ = _get(url, timeout)
            return TAKEN if status == 200 else UNKNOWN
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return FREE
            if e.code not in RETRY_CODES or attempt == attempts - 1:
                return UNKNOWN
        except Exception:                                    # noqa: BLE001
            if attempt == attempts - 1:
                return UNKNOWN
        time.sleep(delay)
        delay *= 2
    return UNKNOWN


# The IANA bootstrap maps each TLD to the RDAP base URL of its own REGISTRY. Fetched once,
# cached for the process.
#
# WHY NOT rdap.org, which is what the first version used. rdap.org is a redirector: it reads
# your query, looks up the same bootstrap, and forwards you. It works, and it is one more party
# that sees every name you are considering before you have registered it. The whole reason this
# module avoids a registrar search box is that a name under consideration is worth keeping
# quiet, and routing through a middleman to achieve that is self-defeating. The bootstrap file
# is 100 KB of public data; resolving locally costs one fetch and removes the observer.
BOOTSTRAP = "https://data.iana.org/rdap/dns.json"
_registry_cache = {}


def _registry_base(tld):
    """RDAP base URL for a TLD, straight from IANA. None when the TLD has no RDAP service."""
    if not _registry_cache:
        try:
            _, body = _get(BOOTSTRAP, 30)
            for tlds, urls in json.loads(body).get("services", []):
                for t in tlds:
                    if urls:
                        _registry_cache[t.lower()] = urls[0].rstrip("/")
        except Exception:                                    # noqa: BLE001
            _registry_cache["__failed__"] = True
    return _registry_cache.get(tld.lower())


def domain(name, tld="com"):
    """Availability, plus the thing nobody reports: whether the TLD itself is a safe bet.

    A ccTLD is leased from a sovereign. Four have already been retired when their territory
    dissolved. Reporting availability without reporting that exposure is half an answer."""
    d = "{}.{}".format(name.lower(), tld)
    base = _registry_base(tld)
    if base:
        st = _exists("{}/domain/{}".format(base, d))
        detail = "RDAP, asked {} directly".format(base.split("//")[-1].split("/")[0])
    else:
        # No bootstrap entry, or the bootstrap fetch failed. Falling back to the redirector is
        # better than returning UNKNOWN, but the answer says which path produced it so nobody
        # has to guess whether a third party saw the query.
        st = _exists("https://rdap.org/domain/{}".format(d))
        detail = "RDAP via the rdap.org redirector (no direct registry found)"
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
