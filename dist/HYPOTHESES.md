# Pre-registered tests

Written and committed 2026-10-29 before any founder birth date was pulled into the dataset. Anything not listed here is labelled "exploratory" on the page.

## Universe
Founders (per Wikipedia infobox or Wikidata "founded by", humans only) of companies founded 1960 to 2023 in three rings: Giants ($100B+ today), Big ($20B to $100B), Fallen (reached $1B, then bankruptcy, liquidation, shutdown, or founder fraud conviction). Only day-precision birth dates count. See SCOPE.md.

## Sign dates
Conventional fixed boundaries, used for every founder regardless of birth year:
Aries Mar 21 to Apr 19, Taurus Apr 20 to May 20, Gemini May 21 to Jun 20, Cancer Jun 21 to Jul 22, Leo Jul 23 to Aug 22, Virgo Aug 23 to Sep 22, Libra Sep 23 to Oct 22, Scorpio Oct 23 to Nov 21, Sagittarius Nov 22 to Dec 21, Capricorn Dec 22 to Jan 19, Aquarius Jan 20 to Feb 18, Pisces Feb 19 to Mar 20.
Elements: Fire (Aries, Leo, Sagittarius), Earth (Taurus, Virgo, Capricorn), Air (Gemini, Libra, Aquarius), Water (Cancer, Scorpio, Pisces). Modalities: Cardinal (Aries, Cancer, Libra, Capricorn), Fixed (Taurus, Leo, Scorpio, Aquarius), Mutable (Gemini, Virgo, Sagittarius, Pisces).

## Baseline
Expected probability of each birthday for each founder = the monthly birth distribution of their birth country in their birth year (Human Fertility Database births-by-month, or Our World in Data's mirror of it; US years before coverage from CDC/NCHS vital statistics), spread evenly across the days of each month, so unequal sign lengths and birth seasonality are both built in. Founders whose country-year has no monthly data get a uniform-by-day baseline, and the page says how many.

## Tests (primary population: Giants + Big, all rings shown separately as well)
1. Sun-sign counts vs expected. Chi-square (11 df) and a 10,000-run Monte Carlo that draws each founder's birthday from their own baseline. Report observed/expected per sign with 95% simulation bands.
2. Look-elsewhere correction. The test statistic is the largest absolute deviation (observed minus expected, in standard units) across the 12 signs; its p-value is the share of simulations whose maximum deviation is at least as large.
3. Elements (4 bins) and modalities (3 bins): chi-square plus the same Monte Carlo, with the same max-deviation correction.
4. Cofounder pairings. Among companies with 2+ dated founders, the share of same-sign, same-element, and traditionally "compatible" pairs (Fire with Air, Earth with Water, plus same element) versus a permutation null that shuffles founders across teams 10,000 times while keeping team sizes fixed.
5. Relative age. Each founder is mapped to their birth country's school-entry cutoff (sourced per country, uncertain ones flagged) and given a relative age in months within their school cohort (0 = youngest, 11 = oldest). Test: mean relative age vs the baseline expectation under the country-year birth distribution, Monte Carlo as above; also the share born in the oldest third vs youngest third of the cohort. If any sign deviates in test 1 or 2, refit with relative age as a covariate and report whether the sign deviation shrinks.
6. Fallen vs thriving. Sign, element, and modality distributions of Fallen-ring founders vs Giants + Big founders: chi-square test of homogeneity plus permutation (10,000 label shuffles).
7. Breakups. Among cofounder pairs tagged "broke up" vs intact pairs: share of "compatible" element pairings, permutation test over the broke-up label (10,000 shuffles).

## Reporting rule
Every test reports an effect size (ratio of observed to expected, or difference in shares), a 95% interval from the simulation, and a one-sentence verdict generated from the numbers by the pipeline, never written in advance. Exploratory extras (Moon sign, Rising sign, month and weekday views, "Find yourself") carry an "exploratory" label.
