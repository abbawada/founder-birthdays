"""Phase 4: inline the data into dist/index.html (self-contained, no build step
needed to open it) and copy the data files next to it for the footer links.
"""
import calendar
import csv
import json
import os
import shutil
from collections import Counter, defaultdict

from common import DATA, ROOT, load_json

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
STARTS = [(3, 21), (4, 20), (5, 21), (6, 21), (7, 23), (8, 23), (9, 23), (10, 23), (11, 22), (12, 22), (1, 20), (2, 19)]
ELEMENT = {"Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire", "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth", "Gemini": "Air", "Libra": "Air", "Aquarius": "Air", "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"}
CUM = [0]
for m in range(1, 13):
    CUM.append(CUM[-1] + calendar.monthrange(2001, m)[1])


def doy(m, d):
    return CUM[m - 1] + min(d, calendar.monthrange(2001, m)[1]) - 1


DOY_SIGN = [0] * 365
for i, (m, d) in enumerate(STARTS):
    s, n = doy(m, d), doy(*STARTS[(i + 1) % 12])
    for k in range(365):
        if (n > s and s <= k < n) or (n <= s and (k >= s or k < n)):
            DOY_SIGN[k] = i

companies = load_json(os.path.join(DATA, "companies.json"))
founders = load_json(os.path.join(DATA, "founders.json"))
_with = {c for f in founders for c in f["companies"]}
companies = [c for c in companies if c["name"] in _with]   # a company with no resolvable founder is not on the ring
stats = load_json(os.path.join(DATA, "stats.json"))
moon = load_json(os.path.join(DATA, "moon.json"), {})
rising = load_json(os.path.join(DATA, "rising.json"), {})
baseline = load_json(os.path.join(DATA, "baseline.json"))

OWID_NAME = {"United States of America": "United States", "United Kingdom": "England and Wales", "England": "England and Wales", "Wales": "England and Wales",
             "Soviet Union": "Russia", "Russian Empire": "Russia", "Kingdom of the Netherlands": "Netherlands", "Czechoslovakia": "Czechia", "Czech Republic": "Czechia",
             "Republic of Ireland": "Ireland", "Korea": "South Korea", "British Hong Kong": "Hong Kong"}


def monthly_for(country, year):
    ent = OWID_NAME.get(country, country)
    if ent and ent in baseline["shares"]:
        ys = baseline["shares"][ent]
        if str(year) in ys:
            return ys[str(year)]
        yy = sorted(map(int, ys))
        near = min(yy, key=lambda y: abs(y - year))
        return ys[str(near)]
    return [calendar.monthrange(2001, m)[1] / 365 for m in range(1, 13)]


REGION = {}
for c in ["United States of America", "United States", "Canada", "Mexico"]:
    REGION[c] = "North America"
for c in ["United Kingdom", "England", "Scotland", "Wales", "Northern Ireland", "Ireland", "Republic of Ireland", "France", "Germany", "West Germany", "East Germany", "Netherlands", "Kingdom of the Netherlands", "Belgium", "Switzerland", "Austria", "Sweden", "Denmark", "Norway", "Finland", "Spain", "Italy", "Portugal", "Poland", "Russia", "Soviet Union", "Russian Empire", "Ukraine", "Czechia", "Czech Republic", "Czechoslovakia", "Hungary", "Greece", "Luxembourg", "Estonia", "Latvia", "Lithuania", "Romania", "Bulgaria", "Croatia", "Serbia", "Slovakia", "Slovenia", "Belarus", "Iceland", "Monaco", "Cyprus", "Malta"]:
    REGION[c] = "Europe"
for c in ["People's Republic of China", "China", "Japan", "South Korea", "Korea", "Taiwan", "Republic of China", "Hong Kong", "British Hong Kong", "Macau", "Mongolia"]:
    REGION[c] = "East Asia"
for c in ["India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Singapore", "Malaysia", "Indonesia", "Thailand", "Vietnam", "Philippines", "Myanmar"]:
    REGION[c] = "South and Southeast Asia"
REGIONS = ["North America", "Europe", "East Asia", "South and Southeast Asia", "Elsewhere"]
ERAS = ["1960s", "1970s", "1980s", "1990s", "2000s", "2010s+"]


def era(y):
    return "2010s+" if y >= 2010 else f"{(y // 10) * 10}s"


# companies -> members (indices into the dated founder list)
dated = [f for f in founders if f.get("birthday")]
key_of = lambda f: f["qid"] or ("name:" + f["name"])
idx = {key_of(f): i for i, f in enumerate(dated)}
members = defaultdict(list)
for i, f in enumerate(dated):
    for c in f["companies"]:
        members[c].append(i)
team_size = {c["name"]: len([f for f in founders if c["name"] in f["companies"]]) for c in companies}
cmap = {c["name"]: c for c in companies}

out_f = []
for i, f in enumerate(dated):
    y, m, d = map(int, f["birthday"].split("-"))
    k = doy(m, d)
    country = f.get("birthplace_country") or (f["citizenship"][0] if f.get("citizenship") else None)
    cos = []
    for c in f["companies"]:
        cc = cmap.get(c)
        if not cc:
            continue
        cos.append({"name": cc["name"], "ring": cc["ring"], "value": cc["value_usd"], "era": era(cc["founded_year"]), "founded": cc["founded_year"],
                    "team": team_size[cc["name"]], "members": members[c], "outcome_year": cc.get("outcome_year", "")})
    if not cos:
        continue
    cos.sort(key=lambda c: -c["value"])
    mk = key_of(f)
    r = rising.get(mk) or {}
    out_f.append({"name": f["name"], "doy": k, "bday": f["birthday"], "bday_h": f"{calendar.month_name[m]} {d}, {y}", "year": y, "sign": SIGNS[DOY_SIGN[k]],
                  "element": ELEMENT[SIGNS[DOY_SIGN[k]]], "companies": cos, "value": cos[0]["value"], "region": REGION.get(country or "", "Elsewhere"),
                  "place": ", ".join(x for x in [f.get("birthplace"), country] if x) or None, "url": f["birth_source_url"] or f["wikipedia_url"] or f["wikidata_url"],
                  "src": f["birth_source"], "base": [round(x, 5) for x in monthly_for(country, y)], "moon": (moon.get(mk) or {}).get("moon"),
                  "rising": r.get("rising"), "rising_rating": r.get("rating")})

# broke-up pairs (indices into the dated list) for the ring highlight
broke_pairs = []
_bp = os.path.join(ROOT, "research", "breakups_verified.csv")
if os.path.exists(_bp):
    name_idx = {f["name"].lower(): i for i, f in enumerate(dated)}
    for r in csv.DictReader(open(_bp)):
        if (r.get("status") or "").strip().lower() in ("broke up", "board ouster"):
            a = name_idx.get((r.get("founder_a") or "").strip().lower()); b = name_idx.get((r.get("founder_b") or "").strip().lower())
            if a is not None and b is not None and a != b:
                broke_pairs.append([a, b])

# school cutoffs for the lens
cutoffs = []
cp = os.path.join(ROOT, "research", "school_cutoffs.csv")
seen = set()
if os.path.exists(cp):
    rows = [r for r in csv.DictReader(open(cp)) if not (r.get("region") or "").strip()]
    rows.sort(key=lambda r: (r["country"] != "United States", -int(r.get("era_from") or 0)))
    for r in rows:
        try:
            mm, dd = map(int, r["cutoff_month_day"].split("-"))
        except ValueError:
            continue
        if r["country"] in seen:
            continue
        seen.add(r["country"])
        cutoffs.append({"country": r["country"], "m": mm, "d": dd})
if not cutoffs:
    cutoffs = [{"country": "United States", "m": 9, "d": 1}]

# coverage numbers for the methods table and story
n_people = len(founders)
n_dated = len(dated)
n_missing = n_people - n_dated
src_counts = Counter(f["birth_source"] for f in dated)
ring_counts = Counter(c["ring"] for c in companies)
ring_people = {r: len({key_of(f) for f in founders if any(cmap.get(c, {}).get("ring") == r for c in f["companies"])}) for r in ("giants", "big", "fallen")}
ring_dated = {r: len({key_of(f) for f in dated if any(cmap.get(c, {}).get("ring") == r for c in f["companies"])}) for r in ("giants", "big", "fallen")}
undated_cos = sorted({c for f in founders if not f.get("birthday") for c in f["companies"]})
base_use = Counter("uniform" if f["base"] == [round(calendar.monthrange(2001, m)[1] / 365, 5) for m in range(1, 13)] else "country-year" for f in out_f)
T = stats["tests"]

sign_names = ", ".join(f"{s} {STARTS[i][0]}/{STARTS[i][1]}" for i, s in enumerate(SIGNS))
methods_table = f"""<div class="chart"><table class="t">
<tr><th>Universe</th><td>{ring_counts['giants']} Giants ($100B+), {ring_counts['big']} Big ($20B to $100B), {ring_counts['fallen']} Fallen; companies founded 1960 to 2023 with at least one named human founder</td></tr>
<tr><th>Founders found</th><td>{n_people} people ({ring_people['giants']} Giants, {ring_people['big']} Big, {ring_people['fallen']} Fallen)</td></tr>
<tr><th>Day-precision birthdays</th><td>{n_dated} ({src_counts.get('wikidata',0)} from Wikidata, {src_counts.get('wikipedia infobox',0)} from a Wikipedia infobox, {src_counts.get('wikipedia lead',0)} from a Wikipedia lead sentence); {n_missing} missing, never guessed</td></tr>
<tr><th>Dated by ring</th><td>{ring_dated['giants']} of {ring_people['giants']} Giants, {ring_dated['big']} of {ring_people['big']} Big, {ring_dated['fallen']} of {ring_people['fallen']} Fallen</td></tr>
<tr><th>Companies with undated cofounders</th><td>{len(undated_cos)}: {", ".join(undated_cos[:40])}{" and more" if len(undated_cos) > 40 else ""}</td></tr>
<tr><th>Baseline</th><td>{base_use.get('country-year',0)} founders use their birth country's monthly births in their birth year (Human Fertility Database via Our World in Data; nearest year when the exact year is missing); {base_use.get('uniform',0)} use a uniform-by-day baseline because no monthly data exists for their country (mostly China, India, Taiwan)</td></tr>
<tr><th>Sign dates</th><td>Fixed conventional boundaries: {sign_names}</td></tr>
<tr><th>Simulations</th><td>{stats['n_sim']:,} runs per test, seed 20261029; the ring's live bands use 1,500 runs in the browser for whatever is selected</td></tr>
<tr><th>Values</th><td>Market caps from companiesmarketcap.com on 2026-10-29; private valuations from the Crunchbase Unicorn Board (2026-10-28) and multiples.vc (2026-10-23); fallen companies at their peak value with the source on each row of companies.csv</td></tr>
<tr><th>Bias to keep in mind</th><td>Missing birthdays skew toward lesser-known cofounders, non-US founders, and founders of companies outside the English-language press. If, say, Chinese cofounders born in winter were systematically undated, a sign could look under-represented for no astrological reason. The missing list is in founders.json.</td></tr>
</table></div>"""

# breakup and rising tables for the story
breakup_rows = ""
bp = os.path.join(ROOT, "research", "breakups_verified.csv")
if os.path.exists(bp):
    rows = [r for r in csv.DictReader(open(bp)) if (r.get("status") or "").strip().lower() in ("broke up", "board ouster")]
    name_sign = {f["name"].lower(): f["sign"] for f in out_f}
    tr = "".join(f"<tr><td>{r['company']}</td><td>{r['founder_a']} <span class='pill'>{name_sign.get(r['founder_a'].strip().lower(),'?')}</span></td><td>{r['founder_b']} <span class='pill'>{name_sign.get(r['founder_b'].strip().lower(),'?')}</span></td><td>{r.get('year','')}</td><td>{r.get('what_happened','')}{(' <a href=\"' + r['source_url'] + '\" target=\"_blank\">source</a>') if r.get('source_url') else ''}</td></tr>" for r in rows[:40])
    breakup_rows = f"<details style='margin-top:10px'><summary class='mono' style='cursor:pointer'>The documented splits ({len(rows)})</summary><table class='t' style='margin-top:8px'><tr><th>Company</th><th>Founder</th><th>Founder</th><th>Year</th><th>What happened</th></tr>{tr}</table></details>"
rising_rows = ""
if rising:
    rr = [(k, v) for k, v in rising.items() if v.get("rising")]
    name_of = {key_of(f): f["name"] for f in founders}
    tr = "".join(f"<tr><td>{name_of.get(k,k)}</td><td>{v['rising']}</td><td>{v.get('moon','')}</td><td>{v.get('time','')}</td><td>{v.get('rating','')}</td></tr>" for k, v in sorted(rr, key=lambda kv: name_of.get(kv[0], kv[0])))
    rising_rows = f"<details style='margin-top:10px'><summary class='mono' style='cursor:pointer'>Founders with a recorded birth time ({len(rr)}, Astro-Databank)</summary><table class='t' style='margin-top:8px'><tr><th>Founder</th><th>Rising</th><th>Moon</th><th>Time</th><th>Rodden rating</th></tr>{tr}</table></details>"

story = {
    "ring": f"<p>{n_dated} founders of {len(companies)} companies, each placed on the day they were born. The brighter, bigger dots are the Giants, companies worth $100 billion or more today. Blue dots are the Big ring, $20 to $100 billion. Red dots founded companies that reached a billion and then collapsed.</p><p>Around the rim, each wedge shows how many founders were born under that sign against the shaded band of what chance produces. Chance here is not a flat line: every founder's expected birthday follows the monthly birth statistics of their own country in their own birth year, so a Japanese founder born in 1957 is 'expected' to be a January baby more often than an American born in 1984.</p><p>Press <b>Shuffle the universe</b> and watch the same founders land on random birthdays. The tallest bar moves, and it is usually about as tall.</p>",
    "tallest": f"<p>People read a chart by its peak. That is the problem: with twelve signs, one of them is always the tallest, and the question is never 'is this bar high?' but 'how high is the tallest bar in a universe where birthdays mean nothing?'</p><p>So the test statistic is the biggest gap, in standard units, among all twelve signs, compared with the biggest gap in each of {stats['n_sim']:,} simulated universes. A tallest bar that chance matches 40% of the time is not a finding. One that chance matches 1% of the time would be.</p>",
    "elements": "<p>Twelve bins spread the founders thin. Astrology's own groupings, four elements and three modalities, give each bin three or four times as many people, which is where a real effect would show first if one existed. Same baseline, same simulation, same look-elsewhere rule.</p>",
    "pairs": "<p>The folk rule: Fire gets on with Air, Earth with Water, and like with like. If sign compatibility nudged who builds companies together, cofounder pairs should be 'compatible' more often than random pairs of the same people.</p><p>The comparison keeps every team's size and simply deals the founders out again, ten thousand times.</p>",
    "school": "<p>A sign is a birth window, and there is one documented way a birth window changes a life: school entry cutoffs. Children born just after the cutoff are the oldest in their class for a decade, and that early edge shows up in sport, in test scores, and in one study of CEOs: Du, Gao and Levi (2012, <i>Economics Letters</i>) found June and July births under-represented among 375 S&P 500 chief executives. A larger follow-up by Covington, Swidler and Yost (2022, <i>Managerial Finance</i>, S&P 1500) found no effect at all.</p><p>Here each founder is mapped to the cutoff rule of their birth country in the era they started school, then placed in their cohort from oldest to youngest. Switch the ring to the <b>School year</b> lens to see the same founders arranged by class position.</p>",
    "fallen": "<p>If the stars made founders, they might also unmake them. The red dots are founders whose companies reached a billion-dollar valuation and then went bankrupt, shut down, or ended in a fraud conviction. Their sign mix is compared with the thriving founders', with the 'fallen' label shuffled ten thousand times.</p>",
    "breakups": "<p>Cofounder splits are the astrology question people actually ask. Each documented split, an ouster, a lawsuit, or a public feud between two cofounders, is a pair; every other cofounder pair in the data is the comparison group. If compatibility by element kept partners together, the pairs that split should be less 'compatible' than the pairs that stayed.</p>",
    "moon": "<p>Sun signs are what birthdays give you for free. A full chart wants the Moon and the Rising sign, and those need the clock. The Moon moves a sign every two and a half days, so from the date alone it is known for most founders and one-of-two for the rest. The Rising sign changes every two hours and needs a recorded birth time, which exists for only a handful of founders in Astro-Databank's collection of birth certificates and biographies. Both are shown on hover where known; neither was pre-registered.</p>",
    "matrix": "<p>This is the question people actually ask: does a Pisces build better with a Leo than with a Cancer? Every cofounder pair in the data sits in one cell of this grid by the two founders' Sun signs. The first view shows how often each pairing occurs against what chance predicts when the same founders are dealt into random teams; the second shows the raw counts; the third shows how those companies fared, the share whose company collapsed or whose founders split.</p><p>Hover a cell and the ring lights up the pairs inside it. Most cells hold a handful of companies, so this is a map for curiosity, not a verdict: the pre-registered test above already asked the pooled version of this question.</p>",
    "you": "<p>Type a birthday and the ring marks it. You get your sign's wedge, how many founders share it against how many chance expects, and every founder born within three days of you. The default is 25 February, the day after Steve Jobs.</p>",
    "methods": "<p>Everything on this page comes from the pipeline in the repository: companies from a market-cap ranking and the Crunchbase Unicorn Board, founders from Wikipedia infoboxes and Wikidata, birthdays only where a source records the day, baselines from national monthly birth statistics. The hypotheses were written and committed before any birth date was pulled; anything added later says 'exploratory'.</p>",
}
giants_n = ring_counts["giants"]
subtitle = f"{n_dated} founders of the world's biggest companies, each placed on the day they were born. Is there a pattern in the signs? And does it survive contact with chance?"
# one-sentence matrix verdict from the numbers
matrix_verdict = ""
pm = T.get("pair_matrix")
if pm:
    import numpy as _np
    cnt = _np.array(pm["counts"]); ex = _np.array(pm["expected"]); rt = _np.array(pm["ratio"])
    mask = cnt >= 5
    if mask.any():
        z = _np.where(ex > 0, (cnt - ex) / _np.sqrt(_np.where(ex > 0, ex, 1)), 0)
        i, j = _np.unravel_index(_np.argmax(_np.where(mask, z, -9)), z.shape)
        matrix_verdict = (f"The most over-represented pairing with at least five pairs is {SIGNS[i]} with {SIGNS[j]}: {int(cnt[i,j])} pairs against {ex[i,j]:.1f} expected ({rt[i,j]:.1f}x). "
                          f"With 78 cells, the tallest cell in a random deal of the same founders is usually about this tall; the pooled compatibility test is the one to trust.")
meta = {"pulled": "2026-10-29", "subtitle": subtitle, "regions": REGIONS, "eras": ERAS, "cutoffs": cutoffs, "story": story, "methods_table": methods_table, "breakup_rows": breakup_rows, "rising_rows": rising_rows, "broke_pairs": broke_pairs, "matrix_verdict": matrix_verdict}
payload = {"founders": out_f, "companies": [{"name": c["name"], "ring": c["ring"], "value": c["value_usd"], "founded": c["founded_year"]} for c in companies], "stats": stats, "meta": meta}

tpl = open(os.path.join(ROOT, "pipeline", "template.html")).read()
html = tpl.replace("/*DATA*/null/*DATA*/", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
dist = os.path.join(ROOT, "dist")
os.makedirs(os.path.join(dist, "data"), exist_ok=True)
open(os.path.join(dist, "index.html"), "w").write(html)
for fn in ("founders.json", "companies.csv", "stats.json", "companies.json"):
    shutil.copy(os.path.join(DATA, fn), os.path.join(dist, "data", fn))
shutil.copy(os.path.join(ROOT, "HYPOTHESES.md"), os.path.join(dist, "HYPOTHESES.md"))
print("dist/index.html", round(os.path.getsize(os.path.join(dist, "index.html")) / 1024), "KB;", len(out_f), "founders inlined;", len(cutoffs), "cutoffs")
