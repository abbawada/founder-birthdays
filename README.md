# Founders by birthday

An interactive single-page data story: every founder of the world's biggest companies on one 365-day ring. Do they cluster by zodiac sign, month, or cofounder pairing, and does any pattern survive contact with chance?

- `dist/index.html` is self-contained (data inlined, no build step; only the Google Fonts stylesheet loads from the network, with system-font fallbacks). Open it locally or serve `dist/` on GitHub Pages. `dist/artifact.html` is the same page without the document skeleton, for publishing as a claude.ai artifact.
- Link straight to a chapter with its id, for example `#chart` (the match chart), `#school` or `#you`. Add `?still` to skip the opening animation (used for screenshots).
- `VIDEO_SCRIPT.md` is the narration for the demo video, generated from the stats by `pipeline/11_script.py`; it follows Play the story chapter by chapter.
- `HYPOTHESES.md` was committed before any birth date was pulled. Anything not in it is labelled "exploratory" on the page.
- `SCOPE.md` explains the universe: companies founded 1960 to 2023 in three rings (Giants $100B+, Big $20B to $100B, Fallen).

## Pipeline

All scripts live in `pipeline/` and cache every raw API response under `cache/`, so reruns are reproducible and offline once cached.

```bash
export PYTHONPATH=pipeline
P=~/.venvs/founders/bin/python     # pyswisseph, requests, numpy, scipy
$P -P pipeline/01_companies.py     # candidates: market-cap ranking + private board  -> data/candidates.json
$P -P pipeline/02_wikipedia.py     # Wikipedia article, infobox founders, Wikidata P112 -> data/companies_raw.json
$P -P pipeline/02b_rings.py        # rings, exclusions, fallen companies            -> data/companies.json, companies.csv
$P -P pipeline/03_founders.py      # founder roster with Wikidata IDs               -> data/founders_raw.json
$P -P pipeline/04_birthdays.py     # day-precision birthdays with source URLs       -> data/founders.json
$P -P pipeline/05_moon.py          # Moon sign candidates (exploratory)             -> data/moon.json
$P -P pipeline/06_baseline.py      # birth seasonality by country and year          -> data/baseline.json
$P -P pipeline/09_rising.py        # Rising sign where Astro-Databank has a time    -> data/rising.json
$P -P pipeline/12_sectors.py       # company type from the Wikipedia industry line  -> data/sectors.json
$P -P pipeline/07_stats.py         # the pre-registered tests and labelled extras   -> data/stats.json
$P -P pipeline/08_build.py         # inline everything                              -> dist/index.html, dist/artifact.html
$P -P pipeline/11_script.py        # narration for the demo video                   -> VIDEO_SCRIPT.md
```

`pipeline/overrides.json` (optional) fixes an article pick, a founding year, or a founder list for a named company, or excludes it with a reason. Tesla lists all five people its 2009 settlement lets call themselves cofounders, with the Wikipedia sentence quoted in the note.

## Changes after the first build (29 October 2026)

- Breakups: the matcher now reads every name in a row ("Peter Thiel; Max Levchin", "Evan Williams (with Jack Dorsey)") and matches pairs within the row's company. Before, rows naming more than one person per side were dropped, which is why only 6 pairs counted. The pre-registered test ("broke up" rows) now has 8 pairs; the page also shows the wider set that includes board ousters (13 pairs), labelled as such. Most famous splits (Twitter, Snap, Tinder, Yahoo, Groupon) are at companies outside the list.
- Company type by sign: new exploratory test (`12_sectors.py`, `T["sectors"]`), shuffling company types between companies 10,000 times.
- The page was rewritten in plain words, with the match chart (click to hold a square), a your-sign view, famous pairs, a share card, and a scripted Play the story.

## Sources

- Market caps: companiesmarketcap.com, 2026-10-29. Private valuations: Crunchbase Unicorn Board (2026-10-28), multiples.vc (2026-10-23).
- Founders: English Wikipedia company infobox, unioned with Wikidata "founded by" (P112), humans only.
- Birthdays: Wikidata P569 at day precision, else the person's Wikipedia infobox; URL stored on every row. Never from memory.
- Birth seasonality: Human Fertility Database monthly births via Our World in Data.
- School cutoffs, fallen companies, breakups: `research/*.csv`, each row with a source URL.
- Birth times: Astro-Databank (astro.com), Rodden-rated, read page by page; only used when its date matches ours.
