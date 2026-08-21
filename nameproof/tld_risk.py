"""A ccTLD belongs to a country, and countries end.

Nobody checks this. Both comparable tools will happily tell you `yourname.io` is available and
say nothing about the fact that the territory behind `.io` signed itself out of existence in
2025. That is not a hypothetical: four ccTLDs have already been retired after their territory
dissolved, and the registrants had to move.

  .tp   East Timor        retired after independence, traffic moved to .tl
  .zr   Zaire             retired after the country was renamed
  .cs   Czechoslovakia    retired after the split
  .dd   East Germany      retired after reunification

`.su` (Soviet Union) survived, and it is the exception people quote to argue the risk is fake.
One survivor out of five is not a reassurance.

This module reports the risk. It does not refuse the TLD: plenty of good businesses run on .io
and a five year wind-down is survivable if you know it is coming. What is not survivable is
finding out afterwards.
"""

LOW, WATCH, HIGH = "low", "watch", "high"

# Only TLDs with something real to say are listed. An absent TLD is reported as unrated rather
# than as safe, because silence and safety are not the same claim.
RISK = {
    "com": (LOW, "generic, no sovereign attached, the default for a reason"),
    "net": (LOW, "generic"),
    "org": (LOW, "generic"),
    "dev": (LOW, "generic, operated by Google, HSTS preloaded so it is https only"),
    "app": (LOW, "generic, HSTS preloaded so it is https only"),
    "ai": (WATCH,
           "Anguilla. Politically stable, but it is a ccTLD, so the sovereign link exists. "
           "Pricing has moved sharply with demand and renewal costs are not generic-TLD costs."),
    "io": (HIGH,
           "British Indian Ocean Territory. On 22 May 2025 an agreement was signed transferring "
           "the territory to Mauritius. If IANA applies its usual rule for a dissolved "
           "territory, a retirement can follow, historically with a multi-year wind-down. "
           "Nothing is announced and the TLD is fully operational today. Know the exposure."),
    "ly": (WATCH, "Libya. Registry has suspended domains over content rules in the past."),
    "tv": (WATCH, "Tuvalu. Small state, registry operations have changed hands repeatedly."),
    "co": (LOW, "Colombia, but operated at generic scale and treated as generic by users."),
    "me": (LOW, "Montenegro, marketed generically."),
    "sh": (WATCH, "Saint Helena, a British Overseas Territory, same class of sovereign link."),
    "gg": (WATCH, "Guernsey, small jurisdiction."),
    "to": (WATCH, "Tonga."),
    "cc": (WATCH, "Cocos Islands, an Australian external territory."),
}


def rate(tld):
    """(level, why). An unknown TLD is `None`, never `low`."""
    return RISK.get(tld.lower().lstrip("."))


def annotate(tld):
    r = rate(tld)
    if r is None:
        return "unrated"
    level, why = r
    return "{}: {}".format(level, why)
