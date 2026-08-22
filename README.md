# nameproof

**Every other naming tool tells you a name is free. This one tells you whether it is any good.**

Availability is the easy half and it is already solved twice over. The hard half is the one that
costs you money for years: a name people mishear on the phone, cannot spell back, or will never
find on Google because it is also a dictionary word.

```
$ nameproof score Vanta Knightly Phrasely Cyclr

A  Vanta  (penalty 0)
------------------------------------------------------------------
  nothing to report. It spells the way it sounds.

B  Knightly  (penalty 2)
------------------------------------------------------------------
  [2] SILENT_LETTER    kn: the k is silent, listeners write n

C  Phrasely  (penalty 3)
------------------------------------------------------------------
  [3] SPELL_AMBIGUOUS  the /f/ sound at the initial can be written f, ph; a listener has to guess

C  Cyclr  (penalty 4)
------------------------------------------------------------------
  [3] SPELL_AMBIGUOUS  the /s/ sound at the initial can be written s, c, ps, sc; a listener has to guess
  [1] READING_TRAP     c before e, i or y is soft, before a, o, u it is hard
```

No account, no API key, no language model. `score`, `market` and `generate` run entirely offline.

## Install

```bash
pip install nameproof
```

Python 3.9+, zero runtime dependencies. The whole thing is standard library.

## The four questions worth asking

### 1. Is it a good name?

```bash
nameproof score kestra loomis phraselytics
```

Deterministic rules, each one explained in the output. The scoring is not a black box and it is
not a vibe: every penalty names the mechanism that will cost you.

**The direction that matters, and almost everyone gets it backwards.** Most naming advice checks
*grapheme to sound*: can I read this and say it out loud? That is the easy direction and it is
not where the money leaks. The expensive direction is *sound to grapheme*: your prospect hears
the name on a call, then has to type it into a browser.

English is brutally many-to-one that way. The /k/ sound alone is spelled **c, k, ck, ch, qu**, so
a name that opens on /k/ is a coin flip every single time somebody says it out loud. `nameproof`
weights the initial sound heaviest, because a wrong first letter means the search does not even
autocomplete into a rescue.

What it checks:

| finding | what it costs you |
|---|---|
| `SPELL_AMBIGUOUS` | one heard sound, several possible spellings (the phone call test) |
| `SILENT_LETTER` | `kn`, `wr`, `ps`, `gn`, trailing `mb`: written but never heard |
| `VOWEL_TEAM` | `ee` vs `ea`, `ai` vs `ay`, and `ough`, which has six readings |
| `DOUBLED_LETTER` | "is that one L or two", on every call, forever |
| `READING_TRAP` | soft vs hard c and g, three vowels in a row |
| `FOREIGN_ONSET` | an opening English does not allow, so US speakers insert or drop a letter |
| `TOO_LONG` / `MANY_SYLLABLES` | people shorten it, and their shortening becomes the real name |
| `CONTAINS_HYPHEN` / `CONTAINS_DIGIT` | unsayable, and it sends people to somebody else's domain |

### 2. Is it free where it actually matters?

```bash
nameproof check vanta --surfaces com,io,pypi,npm,crates,github
```

```
vanta
------------------------------------------------------------------
  TAKEN  vanta.com      RDAP registry lookup
  FREE   pypi           package index
  TAKEN  npm            package index
  TAKEN  github         3 exact-name repo(s), best is tengbao/vanta at 6925 stars
```

The domain is one of four things that can stop you, and it is not the one that stops you most
often. A 6,900-star GitHub homonym means every search for your project surfaces somebody else,
and no domain check will ever tell you that.

**Two implementation notes, because plenty of tools get these wrong:**

- **RDAP, straight to the registry, with no middleman.** RDAP
  ([RFC 7482](https://www.rfc-editor.org/rfc/rfc7482)) is served by the *registry itself*. A
  registrar's search field is a marketing funnel, and domain front running has been a live
  accusation against that channel for two decades. `nameproof` resolves the registry endpoint
  from the [IANA bootstrap](https://data.iana.org/rdap/dns.json) and asks it directly, so a
  `.com` lookup goes to `rdap.verisign.com` and nowhere else. The output names the host it
  asked, so you never have to guess who saw the query.

  The first version routed through `rdap.org`, which works and is one more party reading every
  name you are considering. Avoiding a registrar search box and then handing the query to a
  redirector is self-defeating; the bootstrap costs one fetch and removes the observer.

- **The check is quiet. Buying is not.** A silent availability check is wasted if you then paste
  the name into a registrar's search box and think about it for a week. If the name matters,
  keep the gap between deciding and registering short.
- **A DNS lookup is not an availability check.** A registered domain with no nameservers returns
  NXDOMAIN and looks free. `nameproof` never infers availability from DNS.
- **`unknown` is a real answer.** A rate limit is never folded into "free". That is how a tool
  talks you into registering a name somebody already owns.

### 3. What do the names that already won in this market look like?

This is the part no other tool does, and it is usually the most useful output of the three.

```bash
nameproof market corpora/soc2-compliance.txt
nameproof score mycandidate --market corpora/soc2-compliance.txt
```

Feed it the names your buyer already knows. You get a description of the market's conventions,
not a recommendation:

```
corpora/soc2-compliance.txt  (10 names)
--------------------------------------------------------------
  single word            : 8/10  (80%)
  names the category     : 1/10  (10%)  -> Secureframe
  ends on a vowel        : 3/10  (30%)
  syllables (first word) : 1syl x2, 2syl x4, 3syl x2, 4syl x2
  single-word length     : min 5 median 7 max 11

  read as: 80% are a single word, 10% name the category, 2 syllables dominate, median length 7
```

**The finding that pays for the whole feature.** Run it on two markets that sell the same thing
in different ways:

| corpus | names the category |
|---|---|
| SOC 2 compliance, sold as a **product** | **10%** (1 of 10) |
| Investment adviser compliance, sold as a **service** | **50%** (6 of 12) |

Vanta, Drata, Sprinto, Scrut. Then Core Compliance, MyComplianceOffice, Hardin Compliance.
**Product companies and service firms do not name themselves the same way**, and if you pick the
wrong convention your name quietly tells the market you are the other one. Nobody can tell you
that from a general rule about good names. Ten lines of a competitor list can.

Corpora are plain text, one name per line, `#` for comments. Four are bundled; write your own in
two minutes.

### 4. Will you be able to rank for your own name?

Neither comparable tool touches SEO. Every rule here cites a **primary Google source** with the
date it was read, because SEO folklore is enormous and most of it is uncheckable.

```bash
nameproof score anchor --seo --keywords compliance,audit
```

```
D  anchor  (penalty 6)
------------------------------------------------------------------
  [3] DICTIONARY_WORD  'anchor' is an ordinary English word...
  [3] BRAND_COLLISION  4 notable entities on Wikidata already carry this exact name:
                       anchor (mooring device); anchor (heraldic figure);
                       Anchor (village in McLean County, Illinois, USA)...
```

**The rule that matters most is Google describing its own behaviour.** From the
[Site names](https://developers.google.com/search/docs/appearance/site-names) guidance:

> "Avoid using a generic name. A generic name like 'Best Dentists In Iowa' is unlikely to be
> selected by our system as a site name, unless that's an extremely well-recognized brand name."

Read it twice. A generic name is not shown as your site name **until you are already famous**,
and being shown as your site name is part of how you become famous. Pick a dictionary word and
you start inside that loop.

Brand collision uses **Wikidata**, no key and no signup. The instructive case is `Anchor`: the
lookup returns the mooring device, the heraldic figure, an Illinois village, and the podcast
platform now called Spotify for Creators. Four different things a searcher could mean.

**What this deliberately does NOT do, and every omission is a decision:**

| not implemented | why |
|---|---|
| a TLD ranking penalty | Google: "The TLD ... only matters if you're targeting a specific country's users, and even then it's usually a low impact signal." Coding a `.io` penalty would contradict the source. |
| a domain-length rule | No Google page mentions it. The correlation everyone quotes is confounded by domain age and authority. Length stays a usability matter. |
| a hyphen-count coefficient | Google's URL-structure page recommends hyphens for *readability* and says nothing about ranking. A number here would fake precision. |
| a separate AI Overview rule | Plausible deduction, no measurement found. Folding it in would count the same uncertainty twice under a figure that looks harder than it is. |

**And one piece of received wisdom this tool refuses to repeat.** Everyone cites Google's
"September 2012 EMD update". A search of the Wayback CDX index of Google's official webmaster
blog across September and October 2012 returns **no post announcing it**: it is documented only
by third-party SEO press relaying a tweet. What *is* documented and current is the exact-match
domain system listed among Google's active ranking systems, which exists to "ensure we don't
give too much credit for content hosted under domains designed to exactly match particular
queries". A **cap on benefit**, live today, not a one-off penalty in 2012.

**What this check can and cannot see.** Google corrects a query in two places: in
autocomplete while you type, and on the results page after you press enter ("These are results
for X"). This measures the first. On one real name the two disagreed completely: autocomplete
offered a bioinformatics tool, the results page corrected to a Pokemon. The verdict matched, the
culprit did not. Read a finding as *"Google does not think this string is a thing"*, not as
*"this specific competitor takes your traffic"*. Fetching the results page directly returns a
JavaScript shell with no result text, and driving a real browser would break the
zero-dependency promise, so the gap is documented rather than papered over.

### Bonus: is the TLD itself a safe bet?

`check` flags country-code TLDs whose sovereign link is a live risk, which neither comparable
tool does:

```
  FREE   kestra.io   RDAP registry lookup  |  TLD RISK high: British Indian Ocean Territory.
         On 22 May 2025 an agreement was signed transferring the territory to Mauritius...
```

Four ccTLDs have already been retired after their territory dissolved: `.tp`, `.zr`, `.cs`,
`.dd`. `.su` survived, and it is the exception people quote to argue the risk is imaginary. One
survivor out of five is not a reassurance. The tool does not refuse the TLD, it makes sure you
chose it knowing.

## Don't have a name yet? Generate candidates

Everything above judges a name you already picked. `generate` produces candidates instead, four
different ways, all offline and all deterministic: the same seed always produces the same names,
because a generator nobody can rerun is a generator nobody can argue with, which is the same
complaint this whole tool has about a language model score.

```
$ nameproof generate --technique rare --count 8

rare  (8 generated)
------------------------------------------------------------------
  Slapstick
  Castaway
  Animus
  Underpaid
  Forgie
  Existence
  Editor
  Collie
```

**`rare`** is a filter, not a generator: every candidate is a real, attested word pulled out of
the CMU Pronouncing Dictionary, 6 to 9 letters, 3 syllables or fewer, cross-checked against a
general wordlist to drop proper nouns and inflected forms. Pronounceability costs nothing to
guarantee here, because a word already spoken by whoever built the dictionary is pronounceable
by definition. Cheapest technique of the four, and on the numbers the best one.

```
$ nameproof generate --technique roots --count 8

roots  (8 generated)
------------------------------------------------------------------
  Fluxa
  Metaix
  Formaio
  Teleify
  Veraus
  Sonusify
  Autoly
  Fortio
```

**`roots`** combines a Latin or Greek root with a SaaS-shaped suffix, biased about 2 to 1 toward
a vowel-final suffix. That bias is not folklore: it is Vanta, Drata, Sprinto and Alessa's actual
naming mechanism, all four end on a vowel sound, and a flat coin flip across the suffix list
undersells that pattern.

```
$ nameproof generate --technique phonotactic --count 8

phonotactic  (8 generated)
------------------------------------------------------------------
  Awsi
  Ykupahd
  Kerwah
  Sushyn
  Hofechy
  Lobiku
  Kasi
  Kawji
```

**`phonotactic`** builds syllables from consonant clusters that are attested to open or close a
real English word in the CMU dictionary, at their attested frequency. This is the only technique
of the four that guarantees pronounceability BY CONSTRUCTION, and it is also the one with a real
trap in it, worth stating plainly. Deriving that model from LETTERS instead of PHONEMES produces
charabia: a letter scanner sees `ph` and `kn` as two-consonant clusters, and a model trained on
them strings clusters together that no English word actually has, output like `Chescoul` and
`Dookoush`. Scanning the CMU dictionary's phonemes instead of its spelling fixes it, because a
phoneme scanner sees `ph` and `kn` for the single consonant sound each one actually is. As the
sample above shows, "guaranteed pronounceable" is not the same promise as "sounds like a brand":
every one of those eight is sayable, not all eight are pretty, and `--score` (below) is the
honest way to tell the difference instead of eyeballing it.

```
$ nameproof generate --technique markov --count 8

markov  (8 generated)
------------------------------------------------------------------
  Nuvo
  Acus
  Flue
  Five
  Marincapi
  Barcom
  Coin
  Cavaligen
```

**`markov`** trains a character trigram model on cleaned SEC company names, public domain data,
legal suffixes stripped. It is the loosest of the four techniques and needed the strictest
output filter to earn its place: reject on shape first (no triple-repeated letter, no
three-consonant or three-vowel run), then reject anything that opens or closes on a consonant
cluster no real English word opens or closes on, checked against the same attested cluster data
`phonotactic` samples from. Even filtered, this is the one technique here that occasionally
still produces a rough result; it is included because a 15-line algorithm over public data is
worth the honesty cost.

Run every technique at once, and add `--score` to send each candidate through `phonetics.analyse`
and keep only what grades A or B, the same rules and the same grades `score` prints for a name
you already have:

```
$ nameproof generate --all --count 10 --score

markov  (10 generated)
------------------------------------------------------------------
  A  Nuvo  (penalty 0)
  A  Acus  (penalty 0)
  B  Flue  (penalty 2)
  B  Five  (penalty 2)
  B  Marincapi  (penalty 2)
  A  Barcom  (penalty 0)
  A  Usban  (penalty 0)

phonotactic  (10 generated)
------------------------------------------------------------------
  A  Awsi  (penalty 0)
  A  Ykupahd  (penalty 0)
  B  Sushyn  (penalty 2)
  B  Hofechy  (penalty 2)
  A  Lobiku  (penalty 0)
  B  Wumoo  (penalty 2)
  A  Totul  (penalty 0)

rare  (10 generated)
------------------------------------------------------------------
  B  Slapstick  (penalty 1)
  A  Animus  (penalty 0)
  B  Underpaid  (penalty 2)
  B  Existence  (penalty 1)
  A  Editor  (penalty 0)
  A  Twinkle  (penalty 0)

roots  (10 generated)
------------------------------------------------------------------
  B  Fluxa  (penalty 2)
  B  Metaix  (penalty 2)
  B  Teleify  (penalty 2)
  B  Veraus  (penalty 2)
  B  Autoly  (penalty 2)
  B  Fortio  (penalty 2)
  A  Omnita  (penalty 0)
  B  Graphflow  (penalty 2)
```

That `--score` line is the point of shipping generation and scoring in the same tool: generate,
then judge with the exact rules already sitting in `phonetics.py`, instead of eyeballing which
of forty candidates look right.

**On the data.** The CMU Pronouncing Dictionary is 3.6 MB and most of it is not needed here, so
it never enters the repository. `tools/build_data.py` downloads it, extracts a small filtered
attested-cluster table and a rare-word list (the `nameproof/data/` files `generate` actually
reads, well under 200 KB together), and is not run by `generate` or by anyone installing the
package. The CMU dictionary is Copyright (c) 1993-2015 Carnegie Mellon University, redistributed
here under its BSD-style license; the SEC company name list is U.S. federal government data,
public domain in the United States. Full attribution is in the header of each generated data
file and in `tools/build_data.py`.

## What this is not

- **Not a trademark search.** It cannot tell you a name is legally available. Talk to a lawyer.
- **Not a replacement for [`tldx`](https://github.com/brandonyoungdev/tldx).** If what you need
  is bulk availability across permutations and TLDs, tldx is faster and better at exactly that,
  it has an MCP server, and you should use it. `nameproof` answers the other question.

## Prior art, honestly

| tool | what it is good at | what it does not do |
|---|---|---|
| [`tldx`](https://github.com/brandonyoungdev/tldx) | bulk availability, permutations, MCP, Go, fast | does not judge the name |
| [`domainsearcher-app`](https://github.com/vasilytrofimchuk/domainsearcher-app) | generation plus scoring, browser, no signup | pronounceability is scored by a language model, so it cannot tell you *why*; no SEO; no license file on the repo at time of writing |
| `nameproof` | explainable rules, market conventions, sourced SEO, multi-surface availability, deterministic offline generation | no bulk permutation sweep across TLDs, that is `tldx`'s job |

The gap this fills is narrow and specific: **a score you can argue with.** A number from a model
cannot be disagreed with, which makes it useless for the one decision it is supposed to support.

## Contributing

The rules live in [`nameproof/phonetics.py`](nameproof/phonetics.py), each with the reason it
exists written next to it. If a rule is wrong for your accent or your market, open an issue with
the counter-example: the counter-example is the contribution. The generation techniques live in
[`nameproof/generate.py`](nameproof/generate.py); the script that built their data extract from
the CMU dictionary and SEC's company list is [`tools/build_data.py`](tools/build_data.py).

Tests: `python3 -m pytest tests/ -q`.

## License

MIT.
