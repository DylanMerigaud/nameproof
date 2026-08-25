---
name: nameproof
description: Judge, roast, or find a product name. Use when asked to roast this name, whether a name is any good, to name a project, find or generate a name, compare candidate names, check if a name is taken, or check domain, PyPI, npm and GitHub availability. Also fires on the French "nomme", "trouve un nom", "ce nom est bon ?".
---

# nameproof

A deterministic name proofreader. Every verdict names the mechanism that will cost the user
something, so you never have to say "it feels weak". No API key, no model call: `score`,
`market`, `generate` and `gold` are offline; only `check`, and the `--available` flag on
`generate`/`gold`, touch the network.

The command is `nameproof`, already on your PATH. Never `pip install` it, never call `python`
directly, never rewrite its logic in your head.

## Pick the subcommand from the question

| The user asks | Run |
|---|---|
| roast this name / is X any good / X vs Y | `nameproof score X Y` |
| is X free / can I get the domain | `nameproof check X --surfaces com,io,pypi,npm,github` |
| find me a name / nomme ce projet | `nameproof generate --all --score --count 40` then `score` the shortlist |
| what do names in this market look like | `nameproof market <corpus file>` (several files = comparison) |
| find gold names / a revendre / trouve des noms gold | `nameproof gold --available` (multi-seed until enough free .com survive) |
| est-ce que le nom compte / ca change quoi / des stats | `nameproof cohort [--market ai\|fintech\|devtools]` |

Bundled corpora live at `corpora/`: `yc-ai-winners.txt` (145), `yc-fintech-winners.txt` (126)
and `yc-devtools-winners.txt` (116) are every YC company in that market that was acquired or went
public, so they are the biggest and the only ones selected on an OUTCOME rather than on taste.
The curated leader lists are `ai-infra.txt`, `fintech-infra.txt`, `dev-cli.txt`,
`regtech-product.txt`, `aml-fincrime.txt`, `ria-compliance.txt`, `soc2-compliance.txt`, plus
`roots-trust.txt` which is a root lexicon for `--roots`, not a name corpus.

## DEEP ALWAYS: la profondeur minimale d'une recherche de nom (Dylan, 2026-08-24)

Verbatim fondateur: "j'accepte pas ses reponses, cherche deep always. [...] pour moi cest
grosse frustration si on doit rename. si on a un nom golde on pourras le revendre au pire."
Le jour meme, une passe de ~20 candidats d'un seul registre avait ete presentee comme "les
meilleurs", avec "rename plus tard" en plan B. Refuse. Renommer est un ECHEC, pas un plan,
et un bon nom est un ACTIF revendable.

Avant toute recommandation d'achat, une passe de naming couvre AU MOINS:

1. **Trois registres distincts**, jamais un seul:
   - composes descriptifs (msb+renew, plan+remit): disent le job, valeur de revente faible;
   - inventes porteurs de sens (registre praxtrust: racine latine/grecque + racine metier,
     via un fichier --roots ecrit pour le domaine);
   - courts generiques revendables (le registre GOLD: prononcable, 2-3 syllabes, assez
     large pour survivre a un pivot et se revendre).
2. **100+ candidats scores PAR produit** (generate multi-seeds + composes a la main),
   dispo verifiee sur tous les A-grades, `?` rejoue avant d'etre rapporte.
3. **La shortlist marque les picks GOLD** (revendables) a cote des descriptifs, et dit
   pour chaque finaliste ce qu'il vaut en revente, pas seulement en usage.
4. Sur les meilleurs noms PRIS: dire s'ils sont EN USAGE ou PARQUES (un fetch suffit),
   sans jamais engager d'argent (aftermarket = decision et paiement de Dylan).

### Le 10x par defaut: la cible est le gold PERTINENT (Dylan, 2026-08-25)

La cible de toute passe de naming n'est pas le meilleur descriptif, c'est un nom de la classe
normfin/praxtrust: **gold-shaped (court, prononcable, revendable) ET porteur du sens du
projet**. Le registre B est donc le registre PRINCIPAL d'une passe, pas un complement. Mesure
qui le justifie (2026-08-24/25): les gold purs type mot-reel sont squattes a ~100%, les
inventes porteurs de sens restent trouvables (renovfin, Versiota, labprove).

**Ecran de connotation OBLIGATOIRE**: le scoreur est phonetique et aveugle au sens. Mesure:
morbus- (maladie), rectus-, tutus- ("tutu") sont sortis grade A. Chaque finaliste passe un
jugement humain/LLM de connotation (sens des racines, lecture involontaire en EN et FR,
collisions de marque evidentes) AVANT d'entrer dans une shortlist.

**Depuis le 2026-08-25 la moitie mecanique est AUTOMATIQUE et bloquante.** Dylan a cherche un
candidat sorti de cet outil et est tombe sur du porno: "ca c'etait vraiment un no go". `score`,
`generate` et `gold` passent maintenant tout candidat par `safety.is_blocked` sans aucun flag, et
un nom bloque sort en grade `X`, pas `F` ni `C`. Preuve que ca mordait: sur 3840 candidats du
generateur, le gate a attrape `Sanaly`, que la racine integree `sana` + le suffixe `ly` produit
comme `s-anal-y`.

Ca ne remplace PAS l'ecran humain, ca lui enleve les cas evidents. La liste de fragments est
volontairement partielle et ne couvrira jamais une langue que personne ici ne lit. Ce qui reste a
ta charge: le sens des racines, les lectures involontaires que la liste ignore, les collisions de
marque. Sur un finaliste, ajoute `--connotation` (reseau) pour l'avis de Wiktionary.

Une shortlist issue d'un seul registre ne se presente JAMAIS comme "les meilleurs": elle se
presente comme ce qu'elle est, le meilleur du registre explore.

## L'ecran NSFW: deux voies, et la seconde n'est pas optionnelle sur un finaliste

Origine, 2026-08-25. Dylan a cherche `msbrenew`, un candidat sorti de cet outil, et est tombe sur
du porno. Le nom est PROPRE par denotation: aucun fragment obscene, aucune entree Wiktionary. La
page de resultats de Google le corrige vers `msbreewc`, une creatrice adulte a deux editions
d'ecart, 1.4M followers, Pornhub en premier resultat.

**Ne derive JAMAIS de l'autocomplete ce que la recherche va trouver.** Verbatim: "tu peux pas
deriver de l'auto complete ce que la recherche va trouver. exemple wedpalette." Mesure: sur cinq
locales (us, pe, es, fr, mx) l'autocomplete de `msbrenew` n'a JAMAIS produit `msbreewc`, il
proposait "ms renewal" et "msb renov". `search.py` documente deja le meme divorce sur `normfin`.
Une heuristique batie la-dessus fabrique de la confiance, c'est exactement ce que ce repo refuse.

### Voie 1, automatisable: `--serp` (stealth)

```bash
export NAMEPROOF_FETCHER="<python du venv> <chemin>/scrape_url.py"   # skill scrape-stealth
nameproof score <nom> --serp
```

Lit les VRAIS premiers resultats sur Bing et DuckDuckGo via un navigateur stealth, et met un VETO
(grade `X`) si une plateforme adulte y figure. Mesure du jour: `msbreewc` donne onlyfans.com en
4e position sur les deux moteurs. Sans `$NAMEPROOF_FETCHER` la commande repond `SERP_UNCHECKED`,
jamais "clean": tu ne rapportes pas un nom comme sûr sur cette base.

### Voie 2, OBLIGATOIRE sur chaque finaliste: le vrai navigateur (MCP)

Google repond 429 + captcha meme au stealth, et Google est justement le moteur qui REECRIT un nom
en un autre. Donc la voie 1 attrape le nom dont les resultats SONT adultes, et rate le nom que
Google CORRIGE en un nom adulte. C'est exactement le cas `msbrenew`, qui sort `SERP_CLEAN` sur
Bing et DDG.

Sur chaque finaliste, avant de le mettre dans une shortlist, ouvre-le dans le vrai navigateur
(`arc-lane`, lane `nameproof-serp`, ou les outils `mcp__arc-browser__*` si tu es seul dessus):

1. `google.com/search?q=<nom>&safe=off`, avec **SafeSearch OFF**. Sinon Google te cache le
   probleme et tu rapportes un faux propre.
2. Lis les 5 premiers resultats ET la ligne de correction ("Showing results for X", "Did you mean
   X"). Si Google corrige, refais la recherche sur la chaine corrigee: c'est la que le probleme
   vit.
3. Interroge la locale du MARCHE cible, pas seulement la tienne, MAIS ne compte pas dessus pour
   disculper un nom. Teste le 2026-08-25 sur `msbrenew`: l'hypothese "c'est peut etre google
   espagnol" est FAUSSE, avec `gl=us&hl=en&pws=0` Google corrige quand meme vers `msbreewc` et
   sort Pornhub, OnlyFans, xHamster, Fansly et XVideos dans les dix premiers. Et `gl=us` ne
   surcharge PAS la geoloc IP: le pied de page disait toujours "Urubamba, Peru - From your
   device". Un vrai test US demande une sortie reseau US.

Un finaliste qui n'a pas eu cette passe se presente comme "non verifie", jamais comme propre.

## Reading `cohort`, and the answer you must not soften

`nameproof cohort` tests seven measurable name properties against a real outcome: 1899 resolved
Y Combinator companies, acquired or public against inactive, permuted WITHIN each batch year
because resolution rate runs from 91% in 2007 to 0% in 2026.

THE RESULT IS A NULL AND YOU REPORT IT AS ONE. Nothing this tool measures predicts whether a
company works. The one property that reached significance overall was length, and the command's
own control row dissolves it: restricted to single-word names it is -0.078 letters at p=0.4708.
Never quote the length row without the control row. Never let a user leave believing a clean
nameproof score raises their odds.

WHAT THE NULL DOES NOT KILL, and this is the distinction to hand the user: every finding this
tool prints is a COST, not a probability of success. `SPELL_AMBIGUOUS` means they will spell the
name out loud on calls for years. That is real and worth avoiding regardless of what an
acquisition rate says. Use `cohort` to refuse the opposite claim, never to argue that naming does
not matter.

The one exception, reported with its n: on the AI slice (n=314), single-word names run 13.7
points ahead at p=0.0020 and survive the correction. One market, one property.

## Reading `market`

Five conventions per corpus, each printed as `k/n (pct)`: single word, names the category, built
from real words, ends on a vowel, syllable spread, length spread, and the market's own median
phonetic penalty. Quote the `read as:` line, which carries `n`.

`built from real words` is the axis the DEEP ALWAYS rule turns on (real-word golds are squatted
at ~100%, coined meaning-carriers stay findable), so it is the row to read first when choosing a
register. On a machine with no system dictionary that row says it was not measured; do NOT
report it as 0%.

Pass several corpora to get the comparison block, which names the conventions that actually
SPLIT the markets. That is where the findings are: product versus service compliance splits 10%
against 50% on naming the category, and AI infrastructure and fintech infrastructure are both
50% built from real words against 17% for developer CLI tools.

## Reading `score`

Output is one block per name, best first, `GRADE  name  (penalty N)` then one line per finding
as `[weight] CODE  explanation`. The grade bands: `A+` below 0 (a bonus fired), `A` at 0,
`B` 1-2, `C` 3-5, `D` 6-9, `F` above. Lower penalty is better.

`X` IS NOT A BAND, C'EST UN VETO. Il sort des que `NSFW_FRAGMENT`, `NSFW_SENSE` ou `NSFW_SERP`
est present, et
aucun total ne le rachete, y compris un `.com` nu libre. Un `X` ne se presente jamais comme "un
nom moyen": c'est un nom inutilisable, tu le retires de la liste et tu le dis. `NSFW_NEAR` (poids
2) est l'inverse: un avertissement pour l'ecran humain, jamais un blocage.

Quote the finding CODES back to the user. They are the roast, and they are falsifiable:
`SPELL_AMBIGUOUS` means a listener cannot spell it from hearing it, `READING_TRAP` means the
letters can be read two ways. A one-line "it is fine" throws away the only thing the tool
produces.

Useful flags: `--serp` LIT les vrais premiers resultats et met un veto sur une plateforme adulte
(voir l'ecran NSFW ci-dessus), `--connotation` asks Wiktionary what the word MEANS (network;
l'ecran hors-ligne tourne toujours, flag ou pas), `--market corpora/dev-cli.txt` adds fit-against-the-market findings, `--seo
--keywords a,b` adds dictionary-word and collision risk, `--search` asks Google whether it
keeps the spelling or corrects it away (network), `--offline` forbids every lookup.

## Reading `check`

`FREE`, `TAKEN` or `?` per surface. `?` is a real answer, usually a rate limit, and it is never
the same as free. Re-run a `?` before reporting it as free. A taken bare `.com` is not a veto
on its own; a taken `github` for a repo the user wants to publish usually is.

## Generating

`generate` pools every technique and ranks by penalty, so the first line is the best name
whichever technique made it. `--score` keeps only A and B, `--available` checks the bare .com
and pulls a free one UP the ranking as a bonus rather than using it as a filter. It is
deterministic: same `--seed` and `--count`, same names.

For a name that has to mean something in a specific field, write a roots file
(`root meaning` per line) and pass `--technique roots --roots <file>`. The built-in roots are
generic on purpose.

### `--market`: always pass it when the market is known (2026-08-25)

`generate --market <corpus>` and `gold --market <corpus>` shape the candidates AT GENERATION
TIME off the corpus, then fold fit-against-the-market into the ranking. Use it whenever the user
named a market or a competitor set, and write a 15-line corpus if none of the bundled ones fit:
that costs two minutes and changes the register of every candidate.

WHY IT IS NOT OPTIONAL WHEN THE MARKET IS KNOWN. Without it the generator produces one register
whoever the buyer is. Measured at n=200 before the flag existed: `roots` ended on a vowel 56% of
the time and `phonotactic` 46%, against 30% for the SOC 2 corpus, 10% for AML and 0% for
developer CLI tools. A run for a CLI tool was calibrated at the wrong end of the scale entirely,
and no seed and no count could reach the one-syllable register that market lives in.

Three levers come off the corpus: the vowel-final rate, the syllable distribution and the length
band. Report the `shaped by ... (n=N)` line the command prints, because `n` is small on every
bundled corpus and the user is entitled to know the sample the shape came from.

ONE TRAP, and it bites on exactly the deep passes DEEP ALWAYS asks for. `roots` has 20 roots by
15 suffixes, so a market's register is a pool of a few dozen to a few hundred DISTINCT names.
Against a market at 8% vowel-final, `--count 20` lands on target while `--count 150` drifts to
21%, because the register is exhausted and the generator falls back to the other one. When a pass
needs 100+ candidates, get them from MULTIPLE SEEDS and a `--roots` file for the domain, never
from one big `--count`.

## Reading `gold`

`gold` is registre 3 from DEEP ALWAYS above, as a command instead of a hand-run recipe: it pools
`phonotactic`, `markov` and a `roots` pass off its own embedded, wide, positive lexicon
(`nova`, `vera`, `prax`, `norm`, `flux`, `arc`...), never `rare`, because a 2026-08-24/25
measurement across four real products found short real-word candidates almost entirely taken.
Every candidate then has to clear the GOLD profile: 4-9 letters, 2-3 syllables, the same
pronounceability gate `score` uses (grade A or B), no digit, no hyphen, no niche vertical
morpheme (an `msb`/`pama`/`clfs` fragment reads as bought for one specific bet, the opposite of
resellable). Same table format as `generate`, best first; `--available` checks the bare `.com`
and a free one always ranks above a taken one, by construction.

For the harvest itself: run `nameproof gold --available` across several `--seed` values, since
one run rarely clears 30 verified free names on its own; re-check every `?` before counting it,
same rule as `check`. This produces a RESERVE independent of any product, not a recommendation
to buy: registering is still Dylan's call, and a hand-registered coined name is worth more as a
name he can reach for than as something to resell.

## Do not

Do not report a name as available on the strength of `score` alone: scoring is offline and
knows nothing about who owns what. Do not soften a finding into a compliment. Do not invent
finding codes the tool did not print.
