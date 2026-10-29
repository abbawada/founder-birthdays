# Founder birthdays: scope proposal (for approval)

Date: 2026-10-29. Nothing below is built yet except the probes that produced the counts.

## The question
Do the founders of the world's greatest companies cluster by birthday, zodiac sign, or cofounder sign pairing, and does any pattern survive contact with chance? Same question, in a second colour, for founders whose companies collapsed, and for cofounder pairs that broke up.

## Time frame: companies founded 1960 to 2023
- 1960 rather than 1970 so the founder era's first wave is in: Walmart (1962), Nike (1964), Intel (1968), AMD and Samsung Electronics (1969). Founders born before about 1930 become rare after this cut, which keeps birth-month baselines and school cutoffs meaningful.
- 2023 as the last year so a company has had time to be valued.
- The page gets a founding-era filter (1960s, 70s, 80s, 90s, 2000s, 2010s+), so the stricter 1970+ view is one click.

## Founder scope: three rings, one rule
A person counts as a founder if English Wikipedia's company infobox or Wikidata's "founded by" names them. No founder is added from memory. Each founder keeps a Wikidata ID and a source URL for the birthday.

| Ring | Rule | Size (probe estimate) |
|---|---|---|
| 1. Giants | Worth $100B or more today, public market cap or last private valuation, global | ~85 founder-built companies, ~185 founders |
| 2. Big | $20B to $100B, same rule | ~400 companies, ~700 founders |
| 3. Fallen | Reached $1B+ (valuation or market cap) and then went bankrupt, was liquidated, shut down, or ended in a founder's fraud conviction | ~50 companies, ~90 founders (seed list in research/failed_seed.csv) |

Why Ring 2: Ring 1 alone gives about 15 founders per sign. A spike of 25 Pisces would look dramatic and mean nothing. With ~900 founders in Rings 1 and 2, a real 20% excess in one sign would show up as significant; without it, only huge effects would.

Cofounder breakups: pairs with a documented ouster, lawsuit, or acrimonious departure (Zuckerberg and Saverin, Dorsey and Glass, Eberhard and Musk, Kalanick and his board, Snap and Reggie Brown, and so on) get a "broke up" tag; intact pairs are the comparison group. Seed list in research/breakups_seed.csv, each to be sourced.

Exclusions (automatic): state-owned companies, mergers of equals with no living founder (RTX, Chubb, Novartis), spin-offs and subsidiaries (Waymo, Reliance Retail, Ant Group unless its founders are attributed), and holding-company reorganisations are dated to the original founding (Alphabet to Google 1998, Meta to Facebook 2004).

## What the probe found (2026-10-29)
- companiesmarketcap.com lists 232 public companies at $100B+ today. 120 were founded 1960 or later; 67 of those have named founders in their Wikipedia infobox, and a dozen more will after fixing parse misses (Nvidia, Tesla, Google, Spotify, Micron, Amgen, Snowflake, MediaTek). Draft in research/ring1_draft.csv.
- Private $100B+ (Crunchbase Unicorn Board, updated 2026-10-28): Anthropic $965B, OpenAI $852B, ByteDance $480B, Databricks $190B, Stripe $159B, Ant Group $150B, Waymo $126B, Revolut $115B. multiples.vc (2026-10-23) adds Tether $500B and Blue Origin $140B. SpaceX is public since 12 June 2026 (Nasdaq: SPCX) and enters through the market-cap list.
- Wikidata alone is too thin: Netflix, Amgen, ASML, Spotify's holding entity show zero founders there. The pipeline will union Wikipedia infobox founders with Wikidata, resolve each person to a Wikidata ID, then take the birthday from Wikidata (day precision only) or the person's Wikipedia infobox, storing the URL.

## Moon and Rising
- Sun sign: from the birth date, conventional fixed dates (listed in the methods note).
- Moon sign: computable for everyone with the Swiss Ephemeris (installed and tested: Steve Jobs, 24 Feb 1955 7:15 PM San Francisco, gives Sun Pisces, Moon Aries, Rising Virgo, which matches his published chart). The Moon changes sign every ~2.5 days, so on about 40% of birth dates it is one of two signs without a birth time. Those founders get both candidates and half a count each in the Moon test; the page shows "Aries or Taurus" for them. Labelled exploratory.
- Rising sign: needs the birth time to within about two hours. Astro-Databank (astro.com) has rated birth times for 1,346 entrepreneurs, Jobs, Bezos, Altman, both Amodeis and Bankman-Fried among them. I can read those pages in the in-app browser, one per founder. Rising will be shown on hover for founders with an A or AA-rated time, with no statistics unless at least 30 founders qualify. This adds a day of browser reading, no other obstacle.

## Citations checked today
- Du, Gao and Levi (2012), "The relative-age effect and career success: Evidence from corporate CEOs", Economics Letters 117(3), 660-662: confirmed. 375 S&P 500 CEOs; June and July births under-represented.
- "Pegah and Bigus (2024)" does not exist under that name. The real follow-up is Covington, Swidler and Yost (2022), "Reexamining the relative-age effect and career success: new evidence from S&P 1500 CEOs", Managerial Finance 48(1), 49-56: no relative-age effect found. The site will cite this one.

## Birth-seasonality baseline
Human Fertility Database "births by month" files by country and year (free registration), US pre-1960 from CDC vital statistics, and a uniform-by-day fallback labelled as such. Each founder's expected sign probability uses their birth country and birth year.

## Where it lives
~/Projects/founder-birthdays (git initialised, nothing committed): pipeline/ (Python, cached API responses), data/ (companies.csv, founders.json, stats.json), dist/index.html (self-contained, GitHub Pages ready), research/ (seed lists, memo).

## Open decisions for you
1. 1960 start (recommended) or 1970 as in the prompt.
2. Ring 2 at $20B (recommended), $50B (about 350 founders), or Ring 1 only.
3. Moon as an exploratory lens, Rising on hover only (recommended), or skip both.
4. Project folder location: ~/Projects/founder-birthdays (recommended) or somewhere else.
