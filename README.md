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

No account, no API key, no language model. `score`, `market`, `generate`, `gold` and `cohort`
run entirely offline.

## Install

As a Claude Code plugin, which is the only install that needs nothing on your machine:

```bash
claude plugin marketplace add DylanMerigaud/nameproof
claude plugin install nameproof@nameproof
```

Claude then reaches for `nameproof` on its own when you ask it to roast a name, and the
`nameproof` command is on the PATH of its Bash tool. Nothing is pip-installed: the plugin
ships the package and puts it on `PYTHONPATH`.

As a plain CLI, clone and run it. There is no PyPI package, so `pip install nameproof` does
not work and never did:

```bash
git clone https://github.com/DylanMerigaud/nameproof
nameproof/bin/nameproof score kestra loomis
```

Python 3.9+, zero runtime dependencies. The whole thing is standard library.

## The five questions worth asking

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
nameproof market corpora/soc2-compliance.txt corpora/ria-compliance.txt   # and compare them
nameproof score mycandidate --market corpora/soc2-compliance.txt
```

Feed it the names your buyer already knows. You get a description of the market's conventions,
not a recommendation:

```
corpora/soc2-compliance.txt  (10 names)
--------------------------------------------------------------
  single word            : 8/10  (80%)
  names the category     : 1/10  (10%)  -> Secureframe
  built from real words  : 2/10  (20%)  -> Strike Graph, Tugboat Logic
  ends on a vowel        : 3/10  (30%)
  syllables (first word) : 1syl x2, 2syl x4, 3syl x2, 4syl x2
  single-word length     : min 5 median 7 max 11
  phonetic penalty       : median 2, worst 4

  read as: 80% are a single word, 10% name the category, 20% are built from real words,
           2 syllables dominate, median length 7  (n=10)
```

Every share carries its `n`, because every corpus in this repository is between 10 and 26 names
and a share computed on 10 reads exactly like one computed on 1000 until somebody acts on it.

**Real word or coined** is the axis most naming decisions actually turn on, and it is measured
against your system dictionary. On a machine without one the row says it was not measured rather
than printing a share off the 52-word embedded fallback: a stub reference set would report
almost everything as coined, confidently and wrongly.

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

That finding used to be made by hand, by running the command twice and diffing the output by eye.
Pass several corpora and the tool states it:

```
$ nameproof market corpora/ai-infra.txt corpora/fintech-infra.txt corpora/dev-cli.txt

comparison
--------------------------------------------------------------
                        ai-infra      fintech-infra   dev-cli
  names the category    0%  (n=26)    0%  (n=24)      0%  (n=12)
  single word           100% (n=26)   96% (n=24)      100% (n=12)
  ends on a vowel       19%  (n=26)   25% (n=24)      0%  (n=12)
  built from real words 50%  (n=26)   50% (n=24)      17% (n=12)

  built from real words splits these markets: 50% for fintech-infra against 17% for dev-cli
```

Read that last row. Half of AI infrastructure and half of fintech infrastructure are ordinary
English words (Stripe, Column, Increase, Modal, Together, Cursor). Developer CLI tools are not:
they are `ripgrep`, `fzf`, `zoxide`, `hadolint`. Same buyer persona, opposite convention.

Corpora are plain text, one name per line, `#` for comments. Six name corpora ship with the
tool (`soc2-compliance`, `ria-compliance`, `regtech-product`, `aml-fincrime`, `dev-cli`,
`ai-infra`, `fintech-infra`); write your own in two minutes.

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

### 5. Does the name MEAN something you cannot put on an invoice?

```bash
nameproof score mycandidate --connotation
```

Every other check in this tool looks at how a name spells, sounds and ranks. None of them looked
at what it **means**, and that gap had a cost: a candidate this tool helped produce scored clean,
was available, and its search results were pornography.

**The mechanism that let it through is worse than the missing check.** Google's autocomplete
endpoint, the one `--search` reads, *suppresses* adult terms:

```
ripgrep      15 suggestions
creampie      0 suggestions
bukkake       0 suggestions
fleshlight    0 suggestions
```

Zero suggestions is also the normal state of a freshly coined name nobody has typed. From that
endpoint the best possible name and the worst possible name look **identical**, and the finding
used to say "nothing to conclude either way", which reads as a pass.

**This does not scrape the results page, and both doors were tried rather than assumed shut.**
`google.com/search` answers 200 with a JavaScript shell and no result text. DuckDuckGo's `html.`
and `lite.` endpoints now answer 202 with an anti-bot challenge. A headless browser would fix
both and would break the zero-dependency promise. So the question is answered from what the name
**denotes** instead, which is the more durable signal anyway: a term is not pornographic because
of today's ranking.

Two layers, and only one of them blocks:

| layer | when | what it does |
|---|---|---|
| `connotation` | offline, **always**, no flag | fragment list, EN and FR. A hard hit is a **veto** |
| `sense_labels` | `--connotation`, network | Wiktionary's own usage labels, so the verdict cites a dictionary |

**A veto is not a bad score.** A blocked name grades **`X`**, not `F` and not `C`. At weight 5 it
used to total into band C, which reads as "mediocre but usable", and that is not what this is. No
bonus buys it back either: a free bare `.com` does not make a pornographic reading acceptable, so
the veto is checked before any total.

```
$ nameproof score Analfin Vanta Cultura --offline

A  Vanta  (penalty 0)
  nothing to report. It spells the way it sounds.

X  Analfin  (penalty 5)
  [5] NSFW_FRAGMENT    contains 'anal'. On a coined name there is no other reading available...

C  Cultura  (penalty 5)
  [2] NSFW_NEAR        contains 'cul', which is obscene in French and also sits inside ordinary
                       words. Not a block, a line for the human screen.
```

**The two tiers are the whole design, and the second one exists because of measured false
positives.** The first version of the fragment list blocked `Cultura` on `cul`, `Bitewave` on
`bite` and `Computix` on `pute`. A gate that does that gets switched off within a week, and a
gate nobody runs protects nothing. So productive fragments **warn** and never block, and the
annotation next to each one in `safety.py` names the ordinary word that demoted it.

The Scunthorpe problem is handled explicitly: an ordinary English word carries its own meaning,
so `Analytics` passes and `Analfin` does not. With one subtlety that is easy to get backwards,
`anal` is in the dictionary too, so a token only suppresses a fragment when it is a real word
**and strictly longer** than the fragment. Otherwise the fragment suppresses itself and the gate
never fires on the bare term.

**`generate` and `gold` run the gate with no flag**, and it is not theoretical: scanning 3,840
candidates from the tool's own generator, it caught `Sanaly`, which the built-in root `sana`
(health) plus the suffix `ly` produces as `s-anal-y`. The tool was manufacturing them.

**The list is deliberately partial**, and that is the operating instruction rather than an
apology. It cannot be complete in any language and will never catch a collision in a language
nobody here reads. It exists to make the obvious failure automatic so the judgement left to a
person is a real one. One residual false positive is stated rather than hidden: a proper noun
missing from the system dictionary gets no suppression, so `Scunthorpe` and the surname `Semenza`
are flagged. Separating those needs a gazetteer, which is a bigger dependency than the problem
deserves.

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

### `--market`: generate names shaped like the ones that already won

The two halves above were built separately and, until 2026-08-25, had never been connected.
`market` measured a market's conventions; `generate` ignored them. Three of the generator's
shaping constants were set against **four cherry-picked names** (Vanta, Drata, Sprinto, Alessa)
and said so in their own comments, while the corpora that could measure them sat in the same
repository. Measured at n=200 per technique:

| source | ends on a vowel |
|---|---|
| generator `roots` | **56%** |
| generator `phonotactic` | **46%** |
| corpus soc2-compliance | 30% |
| corpus aml-fincrime | 10% |
| corpus dev-cli | **0%** |

The generator was not wrong, it was **uncalibrated**: it produced one register regardless of who
the buyer was, and for a CLI-tool market it was calibrated at the wrong end of the scale
entirely. `--market` replaces those constants with the corpus's own numbers, at generation time:

```
$ nameproof generate --technique phonotactic --count 10 --seed 11
A  Boype     A  Emo       A  Pipaw     A  Pita      A  Triduda
A  Tryshol   B  Hukel     B  Moomaho   B  Stikoo    C  Sootan

$ nameproof generate --technique phonotactic --count 10 --seed 11 --market corpora/dev-cli.txt

  shaped by corpora/dev-cli.txt (n=12): 0% vowel-final, 3-10 letters, 1syl x7, 2syl x3, ...

A  Bles      A  Lol       A  Mod       A  Owk       A  Pal
A  Rang      A  Slol      A  Swyd      B  Mawzood   C  Tayoos
```

Three things come off the corpus and one comes back into the ranking:

| lever | what it replaces |
|---|---|
| vowel-final rate | the 2-to-1 suffix bias in `roots` and the 0.25 closed-final chance in `phonotactic` |
| syllable distribution | the flat 80/20 draw over 2 and 3 syllables |
| length band | nothing. `rare` and `markov` draw from fixed pools and could not be steered at all; the band is how they get pointed at a market |
| `corpus.fits` findings | nothing. Distance from the market now enters the penalty, so the ranking is market-aware too |

Measured after the wire, `phonotactic` at n=40: dev-cli **0%** against a 0% target,
soc2-compliance **30%** against 30%, ria-compliance **10%** against 8%. And the one-syllable
register became reachable for the first time: `dev-cli` is 7 of 12 one-syllable names and the
builder previously drew only from {2, 3}, so no seed and no count could ever produce it.

**One limit, stated rather than hidden.** `roots` has a vocabulary of 20 roots by 15 suffixes, so
the register a market asks for is a pool of a few dozen to a few hundred *distinct* names, not an
infinite stream. Against the RIA corpus (8% vowel-final), `--count 20` realises 7.1% across 40
seeds; `--count 150` drifts to 21%, because the closed pool holds 136 combinations and
`_collect_unique` has nowhere else to go. **Ask for more names than a register contains and you
get the other register.** The fix is more roots (a `--roots` file for your own field), never a
bigger `--count`.

`--market` works on `gold` too, with one consequence worth naming: a GOLD name is meant to
outlive one bet, so shaping it to a market is a deliberate narrowing. The GOLD gate still runs on
top, the strictest of the two wins, and an empty result is the honest answer when a market's
shape and the GOLD profile do not overlap.

**On the data.** The CMU Pronouncing Dictionary is 3.6 MB and most of it is not needed here, so
it never enters the repository. `tools/build_data.py` downloads it, extracts a small filtered
attested-cluster table and a rare-word list (the `nameproof/data/` files `generate` actually
reads, well under 200 KB together), and is not run by `generate` or by anyone installing the
package. The CMU dictionary is Copyright (c) 1993-2015 Carnegie Mellon University, redistributed
here under its BSD-style license; the SEC company name list is U.S. federal government data,
public domain in the United States. Full attribution is in the header of each generated data
file and in `tools/build_data.py`.

## `nameproof cohort`: does any of this actually predict anything?

```bash
nameproof cohort
nameproof cohort --market ai
```

Every other command in this tool describes a name. This one checks the descriptions against what
happened to the companies, and it is the only command here whose useful answer is usually **no**.

**The dataset.** `nameproof/data/yc_cohort.tsv`, 6190 Y Combinator companies with a batch year
and a status, built by `tools/build_cohort.py` from the public YC directory with no API key.
Crunchbase was the obvious source and is out: the Basic API is discontinued, there is no free
tier, and this tool spends no money. YC is better for this question anyway, because the outcome
and the **date** travel together.

**The confound, which is the whole methodological problem.** Resolution rate falls from about 91%
for the 2007 batches to 0% for 2026, because a young company has not had time to resolve either
way. Comparing names across batches measures age, not names. So every test permutes the outcome
labels **within** a batch year and never across, 2000 times, on a fixed seed.

```
$ nameproof cohort

cohort: all markets  (1899 resolved companies, 21 batch-year strata)
--------------------------------------------------------------------------
  outcome: 832 acquired or public, 1070 inactive
  2000 permutations, labels shuffled WITHIN each batch year, seed 20260825
  Bonferroni across 7 tests -> significant below p=0.0071

  property                                diff         p   verdict
  letters in the name                   -0.517    0.0010   SIGNIFICANT
  is a single word                      +0.046    0.0135   marginal
  phonetic penalty (this tool's score)  -0.198    0.0590   null
  syllables in the first word           -0.068    0.0860   null
  built from real words                 +0.033    0.1409   null
  ends on a vowel                       -0.006    0.7486   null
  names the category                    -0.001    0.9450   null

  control, same test on SINGLE-WORD names only (1537 companies):
  letters in the name                   -0.078    0.4708   null
```

**Read the control row, because it is the finding.** Length looks like a real effect at
p=0.001. Restricted to single-word names it collapses to noise. The apparent length effect was
multi-word names being both longer and worse; length was standing in for word count, and word
count itself was only marginal and did not survive the correction. The command runs that control
automatically and says so in words, because printing the first table without the second would
ship exactly the folklore this repository exists to refuse.

**So: nothing this tool measures predicts whether a company works.** That is not a reason to stop
measuring, and it is worth being precise about what it does and does not kill. A
`SPELL_AMBIGUOUS` finding is a **cost**, paid every time somebody says your name on a call, and a
cost is real whether or not it moves an acquisition rate dominated by the product, the market and
the founders. What the null kills is the claim no naming tool should have made: that a good name
makes you win.

**One market-specific exception, and it is reported the same careful way.** On the AI slice
(n=314), single-word names come in **13.7 points** ahead of multi-word ones at p=0.0020, which
does survive the correction after the length effect dissolves. One property, one market, with its
n attached.

**Known limits**, because a null is only worth the honesty around it. "Acquired" is not
unambiguously a win and this data cannot separate an acqui-hire from a success. YC is one
accelerator with one selection filter. About 0.6% of resolved rows carry an alias or tagline in
the name field ("Kenota (formerly ExVivo Labs)"); they are kept verbatim because editing
third-party names is editing the evidence, and dropping all 12 moves the headline from -0.517 to
-0.461 and leaves the control identical at -0.078. And absence of evidence at n=1899 is not proof
of absence, though an effect small enough to hide at that size is also small enough to be
worthless as advice.

## `nameproof doctor`: does the tool still describe reality?

```bash
nameproof doctor
```

```
nameproof doctor: 12 live case(s) against known answers
--------------------------------------------------------------------------
12 agreed, 0 disagreed, 0 could not run
```

**Why this is the most important command in the repo.** Over one afternoon this tool shipped six
wrong answers in a row: a substring test where it needed whole words, half a fix applied, Google
queried as the wrong country, a ratio read backwards, a redirector that contradicted the
module's own premise, and a CLI flag that parsed without wiring anything. **Not one of them
crashed.** Every single one returned confident, plausible, wrong output.

Unit tests caught none of them and could not have. They test the code against the author's
beliefs, and the author's belief *was* the bug.

So `corpora/calibration.jsonl` holds real names whose verdict is known from the world rather
than from this tool, each carrying the failure it guards:

| case | what it guards |
|---|---|
| `drata` | a launched brand that owns its suggestion list. The only positive control. |
| `vanta` | a very large company that still does **not** own its name. If this goes clean, the threshold has been loosened too far. |
| `wedpalette` | the case the search check was built for: available, phonetically fine, and entirely redirected. |
| `normfin` | the substring bug. `normfin` *is* inside `normfinder`, so a naive test called it healthy. |
| `normix`, `tutify` | the inverted reading. Both scored high because an antibiotic and a tutoring service already own those strings. |
| `google.com` / a nonsense domain | the registry path, in both directions. With only one, a client that answers the same thing to everything still passes. |

**And the harness is proved by breaking it.** Re-introducing each shipped bug into a scratch copy
makes `doctor` fail, which is the only evidence that a passing suite means anything:

```
substring instead of whole word            CAUGHT   11 agreed, 1 disagreed
high ratio read as good on an unlaunched   CAUGHT   10 agreed, 2 disagreed
Google queried without forcing a country   CAUGHT   11 agreed, 1 disagreed
```

Run it before trusting a batch of results, and after touching any check. A disagreement is not a
flaky test: each case is a real name whose answer is known, so a check that stops reproducing it
has drifted, and everything it produced since is suspect.

**Contributing a counter-example is the most valuable contribution to this repo.** If a check is
wrong for your market or your accent, the fix is a line in `calibration.jsonl` with the name and
why, not an argument.

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
