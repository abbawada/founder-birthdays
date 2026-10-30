"""What-if cofounders (just for fun, exploratory): the ten sign pairs whose real
cofounders built the most company value, each filled with the two best-known
founders of those signs who never built a company together.

Candidates are founders of $100B+ companies, best known first (number of
Wikipedia language editions with an article, from Wikidata sitelinks). Portraits: the person's Wikidata image (P18) from Wikimedia Commons,
with author and licence kept for the credits, redrawn as a two-colour halftone
print (ink over red) to match the page. Output: data/whatif.json.
"""
import calendar
import os

from common import DATA, ROOT, load_json, save_json, sparql, chunks
from portraits import portrait

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
STARTS = [(3, 21), (4, 20), (5, 21), (6, 21), (7, 23), (8, 23), (9, 23), (10, 23), (11, 22), (12, 22), (1, 20), (2, 19)]
ELEMENT = {"Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire", "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth", "Gemini": "Air", "Libra": "Air", "Aquarius": "Air", "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"}
CUM = [0]
for m in range(1, 13):
    CUM.append(CUM[-1] + calendar.monthrange(2001, m)[1])
doy = lambda m, d: CUM[m - 1] + min(d, calendar.monthrange(2001, m)[1]) - 1
DOY_SIGN = [0] * 365
for i, (m, d) in enumerate(STARTS):
    s, n = doy(m, d), doy(*STARTS[(i + 1) % 12])
    for k in range(365):
        if (n > s and s <= k < n) or (n <= s and (k >= s or k < n)):
            DOY_SIGN[k] = i
compatible = lambda a, b: ELEMENT[a] == ELEMENT[b] or {ELEMENT[a], ELEMENT[b]} in ({"Fire", "Air"}, {"Earth", "Water"})

founders = load_json(os.path.join(DATA, "founders.json"))
companies = {c["name"]: c for c in load_json(os.path.join(DATA, "companies.json"))}
T = load_json(os.path.join(DATA, "stats.json"))["tests"]
pm, V = T["pair_matrix"], T["value"]

people = []
for f in founders:
    if not f.get("birthday") or not f.get("qid"):
        continue
    cos = [companies[c] for c in f["companies"] if c in companies and companies[c]["ring"] in ("giants", "big")]
    if not cos:
        continue
    y, m, d = map(int, f["birthday"].split("-"))
    best = max(cos, key=lambda c: c["value_usd"] or 0)
    people.append({"name": f["name"], "qid": f["qid"], "sign": SIGNS[DOY_SIGN[doy(m, d)]], "bday": f"{calendar.month_name[m]} {d}, {y}",
                   "company": best["name"], "value": best["value_usd"], "companies": set(f["companies"])})
info = {}
for ch in chunks([p["qid"] for p in people], 30):
    vals = " ".join("wd:" + q for q in ch)
    for b in sparql(f"SELECT ?p ?sl ?img WHERE {{ VALUES ?p {{ {vals} }} ?p wikibase:sitelinks ?sl . OPTIONAL {{ ?p wdt:P18 ?img }} }}"):
        q = b["p"]["value"].split("/")[-1]
        cur = info.setdefault(q, {"sl": int(b["sl"]["value"]), "img": None})
        if "img" in b and not cur["img"]:
            cur["img"] = b["img"]["value"]
for p in people:
    p.update(info.get(p["qid"], {"sl": 0, "img": None}))
pool = sorted([p for p in people if p["img"] and (p["value"] or 0) >= 1e11], key=lambda p: -p["sl"])   # founders of $100B+ companies, best known first

cells = sorted(((V["cell_value"][i][j], i, j) for i in range(12) for j in range(i, 12) if V["cell_value"][i][j] > 0), reverse=True)
pairs_by_cell = {}
for p in pm["pairs"]:
    i, j = sorted((SIGNS.index(p["sa"]), SIGNS.index(p["sb"])))
    pairs_by_cell.setdefault((i, j), []).append(p)
used, picks = set(), []
for val, i, j in cells:
    ci = [p for p in pool if p["sign"] == SIGNS[i] and p["name"] not in used][:10]
    cj = [p for p in pool if p["sign"] == SIGNS[j] and p["name"] not in used][:10]
    best = None
    for a in ci:
        for b in cj:
            if a["name"] == b["name"] or a["companies"] & b["companies"]:
                continue
            score = a["sl"] + b["sl"]
            if not best or score > best[0]:
                best = (score, a, b)
    if not best:
        continue
    _, a, b = best
    used |= {a["name"], b["name"]}
    real = sorted(pairs_by_cell.get((i, j), []), key=lambda p: -(companies.get(p["company"], {}).get("value_usd") or 0))
    seen, examples = set(), []
    for p in real:
        if p["company"] not in seen:
            seen.add(p["company"]); examples.append({"a": p["a"], "b": p["b"], "company": p["company"]})
    picks.append({"rank": len(picks) + 1, "a": a, "b": b, "cell": [i, j], "cell_value": val, "n_real_pairs": len(real), "real_examples": examples[:3],
                  "match": compatible(SIGNS[i], SIGNS[j])})
    if len(picks) == 10:
        break

IDEAS = load_json(os.path.join(ROOT, "pipeline", "whatif_ideas.json"), {})   # imagined companies, written by hand, just for fun
EXTRA = ["Phil Knight", "Ted Arison", "Masayoshi Son", "Frederick W. Smith", "John Collison"]   # birthday twins and the youngest giant founder
out = []
for w in picks:
    row = {k: w[k] for k in ("rank", "cell", "cell_value", "n_real_pairs", "real_examples", "match")}
    for side in ("a", "b"):
        p = w[side]
        row[side] = {k: p[k] for k in ("name", "qid", "sign", "bday", "company", "value", "sl")}
        row[side].update(portrait(p))
    row["idea"] = IDEAS.get(f'{row["a"]["name"]}|{row["b"]["name"]}') or IDEAS.get(f'{row["b"]["name"]}|{row["a"]["name"]}')
    out.append(row)
save_json(os.path.join(DATA, "whatif.json"), out)
extra = {}
for name in EXTRA:
    p = next((q for q in people if q["name"] == name and q.get("img")), None)
    if p:
        pr = portrait(p)
        if not pr["face_found"]:   # profile shots and distant figures don't read as a face: show a name card instead
            print("  no clear face for", name); continue
        extra[name] = {k: p[k] for k in ("name", "qid", "sign", "bday", "company")}
        extra[name].update(pr)
    else:
        print("  no portrait for", name)
save_json(os.path.join(DATA, "portraits.json"), extra)
print("ideas attached:", sum(1 for r in out if r.get("idea")), "of", len(out), "| extra portraits:", list(extra))
for r in out:
    print(r["rank"], f'{r["a"]["name"]} ({r["a"]["sign"]}) + {r["b"]["name"]} ({r["b"]["sign"]})', f'cell ${r["cell_value"]/1e12:.1f}T', "match" if r["match"] else "clash",
          "| faces:", r["a"]["face_found"], r["b"]["face_found"], "|", r["a"]["license"], "/", r["b"]["license"])
