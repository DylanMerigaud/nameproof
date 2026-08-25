---
name: nameproof
description: Judge, roast, or find a product name. Use when asked to roast this name, whether a name is any good, to name a project, find or generate a name, compare candidate names, check if a name is taken, or check domain, PyPI, npm and GitHub availability. Also fires on the French "nomme", "trouve un nom", "ce nom est bon ?".
---

# nameproof

A deterministic name proofreader. Every verdict names the mechanism that will cost the user
something, so you never have to say "it feels weak". No API key, no model call: `score`,
`market` and `generate` are offline, only `check` touches the network.

The command is `nameproof`, already on your PATH. Never `pip install` it, never call `python`
directly, never rewrite its logic in your head.

## Pick the subcommand from the question

| The user asks | Run |
|---|---|
| roast this name / is X any good / X vs Y | `nameproof score X Y` |
| is X free / can I get the domain | `nameproof check X --surfaces com,io,pypi,npm,github` |
| find me a name / nomme ce projet | `nameproof generate --all --score --count 40` then `score` the shortlist |
| what do names in this market look like | `nameproof market <corpus file>` |

Bundled corpora live at `corpora/`: `dev-cli.txt`, `regtech-product.txt`, `roots-trust.txt`,
`aml-fincrime.txt`, `ria-compliance.txt`, `soc2-compliance.txt`.

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

Une shortlist issue d'un seul registre ne se presente JAMAIS comme "les meilleurs": elle se
presente comme ce qu'elle est, le meilleur du registre explore.

## Reading `score`

Output is one block per name, best first, `GRADE  name  (penalty N)` then one line per finding
as `[weight] CODE  explanation`. The grade bands: `A+` below 0 (a bonus fired), `A` at 0,
`B` 1-2, `C` 3-5, `D` 6-9, `F` above. Lower penalty is better.

Quote the finding CODES back to the user. They are the roast, and they are falsifiable:
`SPELL_AMBIGUOUS` means a listener cannot spell it from hearing it, `READING_TRAP` means the
letters can be read two ways. A one-line "it is fine" throws away the only thing the tool
produces.

Useful flags: `--market corpora/dev-cli.txt` adds fit-against-the-market findings, `--seo
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

## Do not

Do not report a name as available on the strength of `score` alone: scoring is offline and
knows nothing about who owns what. Do not soften a finding into a compliment. Do not invent
finding codes the tool did not print.
