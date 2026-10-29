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
sectors = load_json(os.path.join(DATA, "sectors.json"), {})
REL = stats["tests"].get("relative_age", {}).get("per_founder", {})

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
                    "team": team_size[cc["name"]], "members": [], "outcome_year": cc.get("outcome_year", ""), "sector": sectors.get(cc["name"], {}).get("sector")})
    if not cos:
        continue
    cos.sort(key=lambda c: -c["value"])
    mk = key_of(f)
    r = rising.get(mk) or {}
    out_f.append({"name": f["name"], "doy": k, "bday": f["birthday"], "bday_h": f"{calendar.month_name[m]} {d}, {y}", "year": y, "sign": SIGNS[DOY_SIGN[k]],
                  "element": ELEMENT[SIGNS[DOY_SIGN[k]]], "companies": cos, "value": cos[0]["value"], "region": REGION.get(country or "", "Elsewhere"),
                  "place": ", ".join(x for x in [f.get("birthplace"), country] if x) or None, "url": f["birth_source_url"] or f["wikipedia_url"] or f["wikidata_url"],
                  "src": f["birth_source"], "base": [round(x, 5) for x in monthly_for(country, y)], "moon": (moon.get(mk) or {}).get("moon"),
                  "rising": r.get("rising"), "rising_rating": r.get("rating"), "key": mk,
                  "cut": (REL.get(mk) or {}).get("cut"), "cut_country": (REL.get(mk) or {}).get("country")})
# cofounder links: indices into out_f (the list the page draws), never into the wider dated list
_mem = defaultdict(list)
for i, f in enumerate(out_f):
    for c in f["companies"]:
        _mem[c["name"]].append(i)
for f in out_f:
    for c in f["companies"]:
        c["members"] = _mem[c["name"]]

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
_chk = load_json(os.path.join(ROOT, "research", "birthday_checks.json"), {"results": []})
_vc = Counter(r["verdict"] for r in _chk["results"])
undated_cos = sorted({c for f in founders if not f.get("birthday") for c in f["companies"]})
base_use = Counter("uniform" if f["base"] == [round(calendar.monthrange(2001, m)[1] / 365, 5) for m in range(1, 13)] else "country-year" for f in out_f)
T = stats["tests"]

sign_names = ", ".join(f"{s} {STARTS[i][0]}/{STARTS[i][1]}" for i, s in enumerate(SIGNS))
methods_table = f"""<table class="t methods">
<tr><th>Which companies</th><td>{ring_counts['giants']} worth $100 billion or more and {ring_counts['big']} worth $20 to $100 billion (stock-market value on 29 October 2026, or the latest private valuation), plus {ring_counts['fallen']} that reached $1 billion and then collapsed. All founded between 1960 and 2023.</td></tr>
<tr><th>Who counts as a founder</th><td>Whoever the company's Wikipedia page or Wikidata names as a founder: {n_people} people. Tesla also counts the three people a 2009 legal settlement lets call themselves cofounders, Elon Musk among them.</td></tr>
<tr><th>Birthdays</th><td>{n_dated} founders have an exact birth date on Wikidata or Wikipedia. The other {n_missing} don't, and we never guessed one. A second reader re-checked the sources: {_vc.get('confirmed',0)} dates confirmed, {_vc.get('wrong',0)} fixed or removed, {_vc.get('found',0)} newly found.</td></tr>
<tr><th>The luck line</th><td>Births aren't spread evenly over the year, and the pattern differs by country and decade. So each founder's chance of landing on any day follows the monthly births of their own country in their own birth year (Human Fertility Database, via Our World in Data). {base_use.get('uniform',0)} founders, mostly from China, India and Taiwan, use an even spread because no monthly data exists. Then we drew random birthdays that way, {stats['n_sim']:,} times.</td></tr>
<tr><th>Written down first</th><td>The tests on this page were written and committed before a single birthday was pulled (HYPOTHESES.md). The match chart, company types, Moon and rising signs came afterwards, because they were fun to ask, and are marked as extras.</td></tr>
<tr><th>Sign dates</th><td>Fixed dates: {sign_names}.</td></tr>
<tr><th>Company types</th><td>From the industry line on each company's Wikipedia page, grouped into six types; {sum(1 for v in sectors.values() if v.get('set_by_hand'))} one-word or missing lines were set by hand, each with its reason in data/sectors.json.</td></tr>
<tr><th>Blind spot</th><td>Missing birthdays lean toward lesser-known cofounders and founders outside the US. Companies missing a cofounder's birthday: {len(undated_cos)}.</td></tr>
</table>"""

meta = {"pulled": "2026-10-29", "regions": REGIONS, "eras": ERAS, "methods_table": methods_table, "n_people": n_people, "n_missing": n_missing,
        "n_companies": len(companies), "ring_counts": dict(ring_counts)}
stats["tests"].get("relative_age", {}).pop("per_founder", None)   # already folded into each founder
whatif = load_json(os.path.join(DATA, "whatif.json"), [])
payload = {"whatif": whatif, "founders": out_f, "companies": [{"name": c["name"], "ring": c["ring"], "value": c["value_usd"], "founded": c["founded_year"], "sector": sectors.get(c["name"], {}).get("sector")} for c in companies], "stats": stats, "meta": meta}

tpl = open(os.path.join(ROOT, "pipeline", "template.html")).read()
html = tpl.replace("/*DATA*/null/*DATA*/", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
dist = os.path.join(ROOT, "dist")
os.makedirs(os.path.join(dist, "data"), exist_ok=True)
# dist/artifact.html = page content only (the claude.ai viewer adds the document skeleton);
# dist/index.html = the same page as a complete document for GitHub and local use
open(os.path.join(dist, "artifact.html"), "w").write(html)
cut = html.index('<div class="wrap">')
open(os.path.join(dist, "index.html"), "w").write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                                                   + html[:cut] + '</head>\n<body>\n' + html[cut:] + '\n</body>\n</html>\n')
for fn in ("founders.json", "companies.csv", "stats.json", "companies.json", "sectors.json"):
    shutil.copy(os.path.join(DATA, fn), os.path.join(dist, "data", fn))
shutil.copy(os.path.join(ROOT, "HYPOTHESES.md"), os.path.join(dist, "HYPOTHESES.md"))
print("dist/index.html", round(os.path.getsize(os.path.join(dist, "index.html")) / 1024), "KB;", len(out_f), "founders inlined;", sum(1 for f in out_f if f["cut"] is not None), "with a school cutoff")
