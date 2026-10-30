"""Founder-facing extras, all exploratory: how old founders were when they started,
cofounder age gaps, birthday twins, the clash finding sliced every way we could,
the school year as oldest-vs-youngest, and typical company value for each element
pairing (the simulator's basis). Output: data/extras.json.
"""
import json
import os
from collections import defaultdict
from math import comb

import numpy as np
from scipy.stats import spearmanr

from common import DATA, load_json, save_json

T = load_json(os.path.join(DATA, "stats.json"))["tests"]
F = [f for f in load_json(os.path.join(DATA, "founders.json")) if f.get("birthday")]
C = {c["name"]: c for c in load_json(os.path.join(DATA, "companies.json"))}
SECT = load_json(os.path.join(DATA, "sectors.json"))
EL = {"Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire", "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth", "Gemini": "Air", "Libra": "Air", "Aquarius": "Air", "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"}
REP = {"Fire": "Aries", "Earth": "Taurus", "Air": "Gemini", "Water": "Cancer"}
ok = lambda a, b: EL[a] == EL[b] or {EL[a], EL[b]} in ({"Fire", "Air"}, {"Earth", "Water"})
val = lambda c: float(C[c].get("value_usd") or 0)
med = lambda xs: float(np.median(xs)) if len(xs) else None
X = {}

# ---- how old were they?
ages = []
for f in F:
    by = int(f["birthday"][:4])
    for c in f["companies"]:
        if c in C and C[c].get("founded_year"):
            ages.append({"name": f["name"], "company": c, "age": C[c]["founded_year"] - by, "ring": C[c]["ring"], "value": val(c), "year": C[c]["founded_year"]})
a = np.array([x["age"] for x in ages])
eras = [("1960s and 70s", 1960, 1980), ("1980s and early 90s", 1980, 1995), ("late 90s and early 2000s", 1995, 2005), ("2005 to 2015", 2005, 2015), ("since 2015", 2015, 2100)]
rho, p_age = spearmanr([x["age"] for x in ages], [x["value"] for x in ages])
X["ages"] = {"n": len(ages), "median": med(a), "under25": round(float((a < 25).mean()), 3), "over40": round(float((a >= 40).mean()), 3),
             "giants_median": med([x["age"] for x in ages if x["ring"] == "giants"]), "big_median": med([x["age"] for x in ages if x["ring"] == "big"]),
             "by_era": [{"era": e, "median": med([x["age"] for x in ages if lo <= x["year"] < hi]), "n": sum(1 for x in ages if lo <= x["year"] < hi)} for e, lo, hi in eras],
             "hist": np.histogram(np.clip(a, 15, 69), bins=list(range(15, 75, 5)))[0].tolist(), "hist_edges": list(range(15, 75, 5)),
             "youngest_giants": sorted([x for x in ages if x["ring"] == "giants"], key=lambda x: (x["age"], -x["value"]))[:8],
             "oldest_giants": sorted([x for x in ages if x["ring"] == "giants"], key=lambda x: (-x["age"], -x["value"]))[:5],
             "rho_value": round(float(rho), 3), "p_value": round(float(p_age), 3)}

# ---- teams: matched or clashing, age gaps, slices
P = T["pair_matrix"]["pairs"]
team = defaultdict(list)
for p in P:
    team[p["company"]].append(p)
by_year = {f["name"]: int(f["birthday"][:4]) for f in F}
rows = []
for c, ps in team.items():
    ppl = sorted({n for p in ps for n in (p["a"], p["b"])})
    yrs = [by_year[n] for n in ppl if n in by_year]
    sh = float(np.mean([ok(p["sa"], p["sb"]) for p in ps]))
    rows.append({"company": c, "share": sh, "kind": "clash" if sh < 0.5 else ("match" if sh > 0.5 else "even"), "value": val(c), "year": C[c]["founded_year"],
                 "size": len(ppl), "ring": C[c]["ring"], "sector": SECT.get(c, {}).get("sector"), "gap": (max(yrs) - min(yrs)) if len(yrs) > 1 else 0,
                 "people": ppl, "signs": [next(p["sa"] if p["a"] == n else p["sb"] for p in ps if n in (p["a"], p["b"])) for n in ppl]})
def slice_(label, pred):
    s = [r for r in rows if pred(r)]
    cl, ma = [r["value"] for r in s if r["kind"] == "clash"], [r["value"] for r in s if r["kind"] == "match"]
    return {"label": label, "clash": med(cl), "match": med(ma), "n_clash": len(cl), "n_match": len(ma)}
X["clash"] = {
    "slices": [slice_("All teams", lambda r: True), slice_("Without OpenAI", lambda r: r["company"] != "OpenAI"),
               slice_("Founded before 2000", lambda r: r["year"] < 2000), slice_("Founded 2000 or later", lambda r: r["year"] >= 2000),
               slice_("Software and internet", lambda r: r["sector"] == "Software & internet"), slice_("Every other industry", lambda r: r["sector"] != "Software & internet"),
               slice_("Two-founder teams", lambda r: r["size"] == 2), slice_("Three or more founders", lambda r: r["size"] >= 3)],
    "trillion": [{"company": r["company"], "kind": r["kind"], "value": r["value"], "people": r["people"][:4], "signs": r["signs"][:4]} for r in sorted(rows, key=lambda r: -r["value"]) if r["value"] >= 1e12],
    "collapsed": {"clash": round(float(np.mean([r["ring"] == "fallen" for r in rows if r["kind"] == "clash"])), 3), "match": round(float(np.mean([r["ring"] == "fallen" for r in rows if r["kind"] == "match"])), 3)},
    "giants_share": {"clash": round(float(np.mean([r["ring"] == "giants" for r in rows if r["kind"] == "clash"])), 3), "match": round(float(np.mean([r["ring"] == "giants" for r in rows if r["kind"] == "match"])), 3)},
}
# typical company value for every element pairing (one vote per company per pairing): the simulator's basis
typ = defaultdict(set)
for p in P:
    typ[tuple(sorted((EL[p["sa"]], EL[p["sb"]])))].add(p["company"])
X["pairings"] = sorted([{"elements": list(k), "kind": "match" if ok(REP[k[0]], REP[k[1]]) else "clash", "n": len(cs), "median": med([val(c) for c in cs]),
                         "examples": sorted(cs, key=lambda c: -val(c))[:3]} for k, cs in typ.items()], key=lambda d: -d["median"])
earth = [r["value"] for r in rows if any(EL[s] == "Earth" for s in r["signs"])]
no_earth = [r["value"] for r in rows if not any(EL[s] == "Earth" for s in r["signs"])]
X["earth"] = {"with": med(earth), "without": med(no_earth), "n_with": len(earth), "n_without": len(no_earth)}
g = np.array([r["gap"] for r in rows]); v = np.array([r["value"] for r in rows])
X["gaps"] = {"median": med(g), "buckets": [{"label": l, "median": med(v[(g >= lo) & (g < hi)]), "n": int(((g >= lo) & (g < hi)).sum())} for l, lo, hi in [("0 to 2 years", 0, 3), ("3 to 7 years", 3, 8), ("8 to 14 years", 8, 15), ("15 years or more", 15, 999)]],
             "widest": sorted([{"company": r["company"], "gap": int(r["gap"]), "people": r["people"]} for r in rows], key=lambda d: -d["gap"])[:3]}
X["teams"] = [{k: r[k] for k in ("company", "kind", "value", "year", "size", "gap", "ring", "sector", "people", "signs")} for r in rows]   # the team builder replays these

# ---- birthday twins
md = defaultdict(list)
for f in F:
    best = max((val(c) for c in f["companies"] if c in C), default=0)
    md[f["birthday"][5:]].append((best, f["name"], [c for c in f["companies"] if c in C][:1]))
groups = [{"day": d, "people": [{"name": n, "company": (cs[0] if cs else "")} for v_, n, cs in sorted(v, reverse=True)], "value": sum(x[0] for x in v)} for d, v in md.items() if len(v) >= 2]
X["twins"] = {"n_people": len(F), "pairs": sum(comb(len(g["people"]), 2) for g in groups), "expected_pairs": round(comb(len(F), 2) / 365, 1), "days": len(groups),
              "top": sorted(groups, key=lambda g: -g["value"])[:10]}

# ---- school year as oldest vs youngest
ra = T["relative_age"]
X["school"] = {"oldest_third": int(sum(ra["hist"][8:12])), "youngest_third": int(sum(ra["hist"][0:4])), "n": ra["n"],
               "oldest_third_expected": round(float(sum(ra["expected_hist"][8:12])), 1), "youngest_third_expected": round(float(sum(ra["expected_hist"][0:4])), 1)}
# ---- astrology's job descriptions, checked: each sign's signature trait turned into a question the data can answer
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
import calendar
STARTS = [(3, 21), (4, 20), (5, 21), (6, 21), (7, 23), (8, 23), (9, 23), (10, 23), (11, 22), (12, 22), (1, 20), (2, 19)]
CUMd = [0]
for m_ in range(1, 13):
    CUMd.append(CUMd[-1] + calendar.monthrange(2001, m_)[1])
dd = lambda m_, d_: CUMd[m_ - 1] + min(d_, calendar.monthrange(2001, m_)[1]) - 1
DS = [0] * 365
for i_, (m_, d_) in enumerate(STARTS):
    s_, n_ = dd(m_, d_), dd(*STARTS[(i_ + 1) % 12])
    for k_ in range(365):
        if (n_ > s_ and s_ <= k_ < n_) or (n_ <= s_ and (k_ >= s_ or k_ < n_)):
            DS[k_] = i_
team_n = defaultdict(int)
for f in load_json(os.path.join(DATA, "founders.json")):
    for c in f["companies"]:
        team_n[c] += 1
L = []
for f in F:
    y_, m_, d_ = map(int, f["birthday"].split("-"))
    cs = [c for c in f["companies"] if c in C]
    if not cs:
        continue
    c = max(cs, key=val)
    L.append({"sign": SIGNS[DS[dd(m_, d_)]], "team": team_n[c] >= 2, "age": (C[c]["founded_year"] - y_) if C[c].get("founded_year") else np.nan,
              "sector": str(SECT.get(c, {}).get("sector")), "fallen": C[c]["ring"] == "fallen", "value": val(c)})
signs_ = np.array([x["sign"] for x in L]); teamv = np.array([x["team"] for x in L]); agev = np.array([x["age"] for x in L], float)
fall = np.array([x["fallen"] for x in L]); sec = np.array([x["sector"] for x in L]); vv = np.array([x["value"] for x in L])
LORE = [  # sign, what astrologers say, the question, how to measure it, how to show it
    ("Libra", "the sign of partnership", "Do Libras start companies with a cofounder more often?", lambda m: teamv[m].mean(), "pct", "have a cofounder"),
    ("Leo", "the born leader", "Do Leos go it alone more often?", lambda m: 1 - teamv[m].mean(), "pct", "founded solo"),
    ("Aries", "the pioneer who starts young", "Do Aries start younger?", lambda m: np.nanmedian(agev[m]), "age", "typical age at founding"),
    ("Capricorn", "the patient climber", "Do Capricorns start later?", lambda m: np.nanmedian(agev[m]), "age", "typical age at founding"),
    ("Sagittarius", "the risk-taker", "Do Sagittarians crash more often?", lambda m: fall[m].mean(), "pct", "founded a company that collapsed"),
    ("Taurus", "the sign of money", "Do Taurus founders build more valuable companies?", lambda m: np.median(vv[m]), "money", "typical company value"),
    ("Gemini", "the communicator", "Do Geminis build more software and internet companies?", lambda m: (sec[m] == "Software & internet").mean(), "pct", "in software and internet"),
    ("Aquarius", "the inventor", "Do Aquarians build more tech?", lambda m: np.isin(sec[m], ["Software & internet", "Chips & hardware"]).mean(), "pct", "in software or chips"),
    ("Scorpio", "the sign of power and other people's money", "Do Scorpios build more banks and funds?", lambda m: (sec[m] == "Money & finance").mean(), "pct", "in money and finance"),
    ("Virgo", "the healer with an eye for detail", "Do Virgos build more health companies?", lambda m: (sec[m] == "Health & biotech").mean(), "pct", "in health and biotech"),
]
rng_ = np.random.default_rng(20261029)
lore = []
for sg, says, q, fn, fmt, unit in LORE:
    m = signs_ == sg
    obs, base = float(fn(m)), float(fn(np.ones(len(L), bool)))
    sims = np.array([fn(rng_.permutation(signs_) == sg) for _ in range(4000)])
    p_ = float(np.mean(np.abs(sims - base) >= abs(obs - base) - 1e-12))
    up = {"Libra": 1, "Leo": 1, "Aries": -1, "Capricorn": 1, "Sagittarius": 1, "Taurus": 1, "Gemini": 1, "Aquarius": 1, "Scorpio": 1, "Virgo": 1}[sg]
    close = abs(obs - base) <= (0.03 if fmt == "pct" else (1 if fmt == "age" else 0.1 * base))
    verdict = "no difference" if close else ("as the stars say" if (obs - base) * up > 0 else "the opposite")
    lore.append({"sign": sg, "says": says, "question": q, "value": obs, "all": base, "fmt": fmt, "unit": unit, "n": int(m.sum()), "p": round(p_, 3), "verdict": verdict})
X["lore"] = lore
save_json(os.path.join(DATA, "extras.json"), X)
print(json.dumps({k: X[k] for k in ("school", "earth")}, indent=0))
for l in X["lore"]: print(l["sign"], l["verdict"], round(l["value"], 3), round(l["all"], 3), l["p"])
print("ages", X["ages"]["median"], X["ages"]["giants_median"], X["ages"]["big_median"], X["ages"]["under25"], [e["median"] for e in X["ages"]["by_era"]])
print("twins", X["twins"]["pairs"], "expected", X["twins"]["expected_pairs"])
for s in X["clash"]["slices"]: print(s)
print([(t["company"], t["kind"]) for t in X["clash"]["trillion"]])
