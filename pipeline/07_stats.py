"""Phase 3: the pre-registered tests (HYPOTHESES.md) plus labelled exploratory
extras. Reads data/companies.json, data/founders.json, data/baseline.json,
data/moon.json, research/school_cutoffs.csv, research/breakups_verified.csv.
Writes data/stats.json. Every verdict sentence is generated from the numbers.
"""
import calendar
import csv
import json
import os
from collections import Counter, defaultdict

import numpy as np

from common import DATA, ROOT, load_json, save_json

RNG = np.random.default_rng(20261029)
N_SIM = 10000
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
# conventional fixed boundaries (start month, start day) in ring order from Aries
STARTS = [(3, 21), (4, 20), (5, 21), (6, 21), (7, 23), (8, 23), (9, 23), (10, 23), (11, 22), (12, 22), (1, 20), (2, 19)]
ELEMENT = {"Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire", "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
           "Gemini": "Air", "Libra": "Air", "Aquarius": "Air", "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"}
MODALITY = {"Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal", "Taurus": "Fixed", "Leo": "Fixed",
            "Scorpio": "Fixed", "Aquarius": "Fixed", "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable"}
ELEMENTS = ["Fire", "Earth", "Air", "Water"]
MODALITIES = ["Cardinal", "Fixed", "Mutable"]
COMPATIBLE = {("Fire", "Air"), ("Air", "Fire"), ("Earth", "Water"), ("Water", "Earth"), ("Fire", "Fire"), ("Earth", "Earth"), ("Air", "Air"), ("Water", "Water")}

# day-of-year (0..364, Feb 29 folded into Feb 28) -> sign index
DOY_SIGN = np.zeros(365, dtype=int)
CUM = [0] + list(np.cumsum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]))


def doy(m, d):
    return CUM[m - 1] + min(d, calendar.monthrange(2001, m)[1]) - 1


for i, (m, d) in enumerate(STARTS):
    start = doy(m, d)
    nxt = doy(*STARTS[(i + 1) % 12])
    if nxt > start:
        DOY_SIGN[start:nxt] = i
    else:
        DOY_SIGN[start:] = i
        DOY_SIGN[:nxt] = i
DOY_MONTH = np.array([m for m in range(12) for _ in range(CUM[m + 1] - CUM[m])])
SIGN_ELEMENT = np.array([ELEMENTS.index(ELEMENT[s]) for s in SIGNS])
SIGN_MODALITY = np.array([MODALITIES.index(MODALITY[s]) for s in SIGNS])

companies = load_json(os.path.join(DATA, "companies.json"))
founders = load_json(os.path.join(DATA, "founders.json"))
baseline = load_json(os.path.join(DATA, "baseline.json"))
moon = load_json(os.path.join(DATA, "moon.json"), {})
company_by_name = {c["name"]: c for c in companies}

# ---- baseline lookup -------------------------------------------------------
OWID_NAME = {"United States of America": "United States", "USA": "United States", "United Kingdom": "England and Wales", "England": "England and Wales",
             "Wales": "England and Wales", "Scotland": "Scotland", "Northern Ireland": "Northern Ireland", "People's Republic of China": None,
             "Republic of China": None, "Taiwan": None, "India": None, "Germany": "Germany", "West Germany": "West Germany", "East Germany": "East Germany",
             "Soviet Union": "Russia", "Russia": "Russia", "Russian Empire": "Russia", "Kingdom of the Netherlands": "Netherlands",
             "Czechoslovakia": "Czechia", "Czech Republic": "Czechia", "Republic of Ireland": "Ireland", "South Korea": "South Korea",
             "Korea": "South Korea", "Hong Kong": "Hong Kong", "British Hong Kong": "Hong Kong"}


def baseline_for(country, year):
    """12 monthly shares for a founder's birth country and year, plus a label of what was used."""
    ent = OWID_NAME.get(country, country)
    if ent and ent in baseline["shares"]:
        years = baseline["shares"][ent]
        if str(year) in years:
            return years[str(year)], f"{ent} {year}"
        ys = sorted(map(int, years))
        near = min(ys, key=lambda y: abs(y - year))
        window = [years[str(y)] for y in ys if abs(y - near) <= 2]
        return list(np.mean(window, axis=0)), f"{ent} {near} (nearest)"
    return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] and [calendar.monthrange(2001, m)[1] / 365 for m in range(1, 13)], "uniform"


def day_probs(monthly):
    p = np.zeros(365)
    for m in range(12):
        n = CUM[m + 1] - CUM[m]
        p[CUM[m]:CUM[m + 1]] = monthly[m] / n
    return p / p.sum()


# ---- founder table ---------------------------------------------------------
F = []
for f in founders:
    if not f.get("birthday"):
        continue
    y, m, d = map(int, f["birthday"].split("-"))
    country = f.get("birthplace_country") or (f["citizenship"][0] if f.get("citizenship") else None)
    monthly, blabel = baseline_for(country, y)
    rings = {company_by_name[c]["ring"] for c in f["companies"] if c in company_by_name}
    F.append({"key": f["qid"] or ("name:" + f["name"]), "name": f["name"], "doy": doy(m, d), "year": y, "country": country,
              "baseline": day_probs(monthly), "baseline_label": blabel, "rings": rings, "companies": f["companies"]})
P = np.array([f["baseline"] for f in F])          # n x 365
OBS_DOY = np.array([f["doy"] for f in F])
N = len(F)


def simulate(idx, n_sim=N_SIM):
    """Draw birthdays for founders idx from their own baselines: returns array (n_sim x len(idx)) of doy."""
    probs = P[idx]
    cum = np.cumsum(probs, axis=1)
    u = RNG.random((n_sim, len(idx)))
    return np.array([np.searchsorted(cum[j], u[:, j]) for j in range(len(idx))]).T.clip(0, 364)


def bin_test(idx, mapper, labels, label):
    """Chi-square + Monte Carlo for a binned view (signs, elements, modalities, months)."""
    k = len(labels)
    obs = np.bincount(mapper[OBS_DOY[idx]], minlength=k)
    exp = np.array([P[idx][:, mapper == b].sum() for b in range(k)])
    chi = float(((obs - exp) ** 2 / exp).sum())
    sims = simulate(idx)
    sim_counts = np.stack([np.bincount(mapper[row], minlength=k) for row in sims])
    sim_chi = ((sim_counts - exp) ** 2 / exp).sum(axis=1)
    p_chi = float((sim_chi >= chi).mean())
    z = (obs - exp) / np.sqrt(exp)
    sim_z = (sim_counts - exp) / np.sqrt(exp)
    maxdev = float(np.abs(z).max())
    p_max = float((np.abs(sim_z).max(axis=1) >= maxdev).mean())
    lo, hi = np.percentile(sim_counts, [2.5, 97.5], axis=0)
    top = int(np.argmax(z))
    ratio = obs[top] / exp[top]
    verdict = (f"The tallest bar, {labels[top]}, has {int(obs[top])} founders against {exp[top]:.1f} expected ({ratio:.2f}x). "
               f"In {N_SIM:,} shuffles of the same founders, a bar at least this far from expectation appeared {100*p_max:.0f}% of the time"
               + (" — well inside chance." if p_max > 0.1 else (" — borderline." if p_max > 0.01 else " — rare under chance.")))
    return {"label": label, "n": int(len(idx)), "bins": labels, "observed": obs.tolist(), "expected": exp.round(2).tolist(),
            "band_lo": lo.round(1).tolist(), "band_hi": hi.round(1).tolist(), "ratio": (obs / exp).round(3).tolist(),
            "z": z.round(2).tolist(), "chi2": round(chi, 2), "p_chi2_mc": p_chi, "max_dev_z": round(maxdev, 2), "p_max_dev": p_max,
            "tallest": labels[top], "verdict": verdict}


def subset(pred):
    return np.array([i for i, f in enumerate(F) if pred(f)], dtype=int)


IDX_ALL = np.arange(N)
IDX_THRIVING = subset(lambda f: f["rings"] & {"giants", "big"})
IDX_GIANTS = subset(lambda f: "giants" in f["rings"])
IDX_FALLEN = subset(lambda f: "fallen" in f["rings"])

stats = {"n_dated": N, "n_sim": N_SIM, "populations": {"all": int(N), "thriving": int(len(IDX_THRIVING)), "giants": int(len(IDX_GIANTS)), "fallen": int(len(IDX_FALLEN))},
         "baseline_use": Counter(f["baseline_label"].split(" (")[0].rsplit(" ", 1)[0] if f["baseline_label"] != "uniform" else "uniform" for f in F).most_common(),
         "tests": {}}
T = stats["tests"]
T["signs"] = bin_test(IDX_THRIVING, DOY_SIGN, SIGNS, "Sun sign, Giants + Big")
T["signs_giants"] = bin_test(IDX_GIANTS, DOY_SIGN, SIGNS, "Sun sign, Giants only")
T["elements"] = bin_test(IDX_THRIVING, SIGN_ELEMENT[DOY_SIGN], ELEMENTS, "Element, Giants + Big")
T["modalities"] = bin_test(IDX_THRIVING, SIGN_MODALITY[DOY_SIGN], MODALITIES, "Modality, Giants + Big")
T["months"] = bin_test(IDX_THRIVING, DOY_MONTH, list(calendar.month_name)[1:], "Birth month, Giants + Big (exploratory)")
if len(IDX_FALLEN) >= 10:
    T["signs_fallen"] = bin_test(IDX_FALLEN, DOY_SIGN, SIGNS, "Sun sign, Fallen")

# ---- cofounder pairings ----------------------------------------------------
teams = defaultdict(list)
for i, f in enumerate(F):
    for c in f["companies"]:
        if c in company_by_name:
            teams[c].append(i)
teams = {c: ids for c, ids in teams.items() if len(ids) >= 2}
pairs = [(a, b) for ids in teams.values() for ai, a in enumerate(ids) for b in ids[ai + 1:]]


def pair_rates(doys):
    s = DOY_SIGN[doys]
    e = SIGN_ELEMENT[s]
    same_sign = np.mean([s[a] == s[b] for a, b in pairs])
    same_el = np.mean([e[a] == e[b] for a, b in pairs])
    compat = np.mean([(ELEMENTS[e[a]], ELEMENTS[e[b]]) in COMPATIBLE for a, b in pairs])
    return same_sign, same_el, compat


if pairs:
    obs_rates = pair_rates(OBS_DOY)
    team_members = np.array(sorted({i for ids in teams.values() for i in ids}))
    sims = []
    for _ in range(N_SIM):
        perm = OBS_DOY.copy()
        perm[team_members] = OBS_DOY[RNG.permutation(team_members)]
        sims.append(pair_rates(perm))
    sims = np.array(sims)
    names = ["same sign", "same element", "traditionally compatible"]
    T["pairs"] = {"label": "Cofounder pairings vs shuffled teams", "n_pairs": len(pairs), "n_teams": len(teams), "measures": []}
    for j, nm in enumerate(names):
        lo, hi = np.percentile(sims[:, j], [2.5, 97.5])
        p_two = float(min(1.0, 2 * min((sims[:, j] >= obs_rates[j]).mean(), (sims[:, j] <= obs_rates[j]).mean())))
        T["pairs"]["measures"].append({"name": nm, "observed": round(float(obs_rates[j]), 4), "null_mean": round(float(sims[:, j].mean()), 4),
                                       "band_lo": round(float(lo), 4), "band_hi": round(float(hi), 4), "p_two_sided": p_two})
    c = T["pairs"]["measures"][2]
    T["pairs"]["verdict"] = (f"{100*c['observed']:.0f}% of the {len(pairs)} cofounder pairs are 'compatible' by the classic element rule, "
                             f"against {100*c['null_mean']:.0f}% when the same founders are shuffled into random teams (95% range {100*c['band_lo']:.0f} to {100*c['band_hi']:.0f}%)"
                             + (". Nothing to see." if c["p_two_sided"] > 0.1 else ". A nudge worth a second look." if c["p_two_sided"] > 0.01 else ". That is unusual under chance."))


# ---- breakup table parser ----------------------------------------------------
# A row's founder_a / founder_b can hold several names ("Peter Thiel; Max Levchin")
# and notes ("Evan Williams (with Jack Dorsey)"). Names inside "(with ...)" count;
# any other parenthetical is a note. Each row yields every a x b pair of dated
# founders who are cofounders of that row's company.
import re as _re
def _names(field):
    field = field or ""
    withs = [w for grp in _re.findall(r"\(with ([^)]*)\)", field) for w in _re.split(r";|,| and ", grp)]
    field = _re.sub(r"\([^)]*\)", "", field)
    return [n.strip().lower() for n in _re.split(r";|,| and ", field) + withs if n.strip()]
def breakup_rows(statuses):
    rows = []
    bp = os.path.join(ROOT, "research", "breakups_verified.csv")
    if not os.path.exists(bp):
        return rows
    for r in csv.DictReader(open(bp)):
        if (r.get("status") or "").strip().lower() in statuses:
            rows.append(r)
    return rows

# ---- sign-pair matrix (exploratory, requested after pre-registration) -------
# every cofounder pair in every ring, by unordered Sun-sign pair: observed count,
# expected count under the same team-shuffle null, and how those companies fared
all_teams = defaultdict(list)
for i, f in enumerate(F):
    for c in f["companies"]:
        if c in company_by_name:
            all_teams[c].append(i)
all_teams = {c: ids for c, ids in all_teams.items() if len(ids) >= 2}
all_pairs = [(a, b, c) for c, ids in all_teams.items() for ai, a in enumerate(ids) for b in ids[ai + 1:]]
SPLIT_ROWS = breakup_rows({"broke up", "board ouster"})
br_names = {}   # frozenset(names) -> row, restricted to the row's company
for r in SPLIT_ROWS:
    for x in _names(r.get("founder_a")):
        for y in _names(r.get("founder_b")):
            if x != y:
                br_names[(r["company"].strip(), frozenset([x, y]))] = r
if all_pairs:
    S_OBS = DOY_SIGN[OBS_DOY]
    def cell(a, b):
        return (min(a, b), max(a, b))
    counts = np.zeros((12, 12)); fallen_c = np.zeros((12, 12)); broke_c = np.zeros((12, 12)); giants_c = np.zeros((12, 12))
    members_cells = defaultdict(list)
    named_pairs = []
    for a, b, c in all_pairs:
        i, j = cell(S_OBS[a], S_OBS[b])
        counts[i, j] += 1
        if company_by_name[c]["ring"] == "fallen":
            fallen_c[i, j] += 1
        if company_by_name[c]["ring"] == "giants":
            giants_c[i, j] += 1
        split_row = br_names.get((c, frozenset([F[a]["name"].lower(), F[b]["name"].lower()])))
        if split_row:
            broke_c[i, j] += 1
        members_cells[(i, j)].append(c)
        named_pairs.append({"a": F[a]["name"], "b": F[b]["name"], "sa": SIGNS[S_OBS[a]], "sb": SIGNS[S_OBS[b]], "company": c,
                            "ring": company_by_name[c]["ring"], "split": (split_row or {}).get("status", ""),
                            "split_year": (split_row or {}).get("year", ""), "what": (split_row or {}).get("what_happened", "")[:220],
                            "src": (split_row or {}).get("source_url", "")})
    team_members_all = np.array(sorted({i for ids in all_teams.values() for i in ids}))
    exp = np.zeros((12, 12))
    N_PAIR_SIM = 4000
    for _ in range(N_PAIR_SIM):
        perm = OBS_DOY.copy()
        perm[team_members_all] = OBS_DOY[RNG.permutation(team_members_all)]
        s = DOY_SIGN[perm]
        for a, b, c in all_pairs:
            i, j = cell(s[a], s[b])
            exp[i, j] += 1
    exp /= N_PAIR_SIM
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(exp > 0, counts / exp, 0)
    T["pair_matrix"] = {"label": "Sun-sign pairs among cofounders (exploratory)", "signs": SIGNS, "n_pairs": len(all_pairs), "n_teams": len(all_teams),
                        "counts": counts.astype(int).tolist(), "expected": exp.round(2).tolist(), "ratio": ratio.round(2).tolist(),
                        "fallen": fallen_c.astype(int).tolist(), "broke_up": broke_c.astype(int).tolist(), "giants": giants_c.astype(int).tolist(),
                        "companies": {f"{i},{j}": sorted(set(v))[:12] for (i, j), v in members_cells.items()},
                        "pairs": named_pairs, "n_split": int(broke_c.sum()), "n_fallen_pairs": int(fallen_c.sum()),
                        "note": "78 cells share a few hundred pairs, so most cells hold a handful of companies; read the ratio with its count, and treat any single bright cell as a story, not a result."}

# ---- relative age ----------------------------------------------------------
cut_path = os.path.join(ROOT, "research", "school_cutoffs.csv")
cutoffs = {}
if os.path.exists(cut_path):
    for r in csv.DictReader(open(cut_path)):
        if r.get("region"):
            continue
        try:
            fr = int(r.get("era_from") or 0)
            to = int(r.get("era_to") or 9999)
            mm, dd = map(int, r["cutoff_month_day"].split("-"))
        except (ValueError, KeyError):
            continue
        cutoffs.setdefault(r["country"].strip(), []).append((fr, to, mm, dd, r.get("certainty", ""), r.get("rule_in_words", "")))
COUNTRY_ALIAS = {"United States of America": "United States", "People's Republic of China": "China", "Republic of China": "Taiwan",
                 "Kingdom of the Netherlands": "Netherlands", "Soviet Union": "Russia", "West Germany": "Germany", "East Germany": "Germany",
                 "Czechoslovakia": "Czechia", "Czech Republic": "Czechia", "Republic of Ireland": "Ireland", "British Hong Kong": "Hong Kong",
                 "England": "United Kingdom", "Wales": "United Kingdom", "Scotland": "United Kingdom", "Northern Ireland": "United Kingdom",
                 "Korea": "South Korea", "Russian Empire": "Russia"}


def cutoff_for(country, year):
    c = COUNTRY_ALIAS.get(country, country)
    for fr, to, mm, dd, cert, words in cutoffs.get(c, []):
        if fr <= year + 6 <= to:          # the rule in force when the child was about 6
            return (mm, dd, cert, words)
    rows = cutoffs.get(c)
    return (rows[0][2], rows[0][3], rows[0][4] + " (nearest era)", rows[0][5]) if rows else None


def rel_age_months(d, cutoff_doy):
    """Months older than the youngest classmate. cutoff_doy is the LAST qualifying
    birthday (inclusive): born on it = youngest in the cohort (0); born the day
    after = oldest of the next cohort (11)."""
    days_after = (d - cutoff_doy - 1) % 365   # 0 on the day after the cutoff
    return 11 - min(11, int(days_after // 30.44))


rel_idx, rel_obs, rel_cut, rel_cert = [], [], [], []
REL_PER = {}
for i in IDX_THRIVING:
    f = F[i]
    co = cutoff_for(f["country"], f["year"]) if f["country"] else None
    if not co:
        continue
    cd = doy(co[0], co[1])
    rel_idx.append(i)
    rel_cut.append(cd)
    rel_cert.append(co[2])
    rel_obs.append(rel_age_months(f["doy"], cd))
    REL_PER[f["key"]] = {"cut": int(cd), "country": COUNTRY_ALIAS.get(f["country"], f["country"]), "rule": co[3]}
if rel_idx:
    rel_idx = np.array(rel_idx)
    rel_obs = np.array(rel_obs)
    rel_cut = np.array(rel_cut)
    sims = simulate(rel_idx)
    sim_rel = np.vectorize(rel_age_months)(sims, rel_cut[None, :])
    obs_mean = float(rel_obs.mean())
    sim_means = sim_rel.mean(axis=1)
    lo, hi = np.percentile(sim_means, [2.5, 97.5])
    p_two = float(min(1.0, 2 * min((sim_means >= obs_mean).mean(), (sim_means <= obs_mean).mean())))
    old = float((rel_obs >= 8).mean())
    young = float((rel_obs <= 3).mean())
    sim_old = (sim_rel >= 8).mean(axis=1)
    sim_young = (sim_rel <= 3).mean(axis=1)
    hist = np.bincount(rel_obs, minlength=12)
    exp_hist = np.stack([np.bincount(row, minlength=12) for row in sim_rel]).mean(axis=0)
    T["relative_age"] = {"label": "Relative age in the school cohort, Giants + Big", "n": int(len(rel_idx)), "mean_months": round(obs_mean, 3),
                         "null_mean": round(float(sim_means.mean()), 3), "band_lo": round(float(lo), 3), "band_hi": round(float(hi), 3), "p_two_sided": p_two,
                         "share_oldest_third": round(old, 4), "share_youngest_third": round(young, 4),
                         "null_oldest_third": round(float(sim_old.mean()), 4), "null_youngest_third": round(float(sim_young.mean()), 4),
                         "hist": hist.tolist(), "expected_hist": exp_hist.round(2).tolist(), "per_founder": REL_PER,
                         "certainty": Counter(rel_cert).most_common(), "countries_covered": sorted({COUNTRY_ALIAS.get(F[i]['country'], F[i]['country']) for i in rel_idx}),
                         "verdict": (f"Founders average {obs_mean:.2f} months older than their youngest classmate; chance says {sim_means.mean():.2f} "
                                     f"(95% range {lo:.2f} to {hi:.2f}). {100*old:.0f}% were among the oldest third of their class vs {100*sim_old.mean():.0f}% expected"
                                     + (". No relative-age effect shows." if p_two > 0.1 else ". A lean toward the older side." if obs_mean > sim_means.mean() else ". A lean toward the younger side."))}
    # does relative age explain the sign result? refit sign deviations after reweighting by cohort position
    # (simple check: sign counts expected under the baseline restricted to the observed relative-age mix)
    top = T["signs"]["tallest"]
    for f in F:
        if f["key"] in REL_PER or not f["country"]:
            continue
        co = cutoff_for(f["country"], f["year"])
        if co:
            REL_PER[f["key"]] = {"cut": int(doy(co[0], co[1])), "country": COUNTRY_ALIAS.get(f["country"], f["country"]), "rule": co[3]}
    T["relative_age"]["sign_check"] = f"Sign test tallest bar is {top}; see 'signs' max-deviation p = {T['signs']['p_max_dev']:.2f} before any cohort adjustment."

# ---- fallen vs thriving ----------------------------------------------------
if len(IDX_FALLEN) >= 10:
    def homog(idx_a, idx_b, mapper, k):
        a = np.bincount(mapper[OBS_DOY[idx_a]], minlength=k)
        b = np.bincount(mapper[OBS_DOY[idx_b]], minlength=k)
        tot = a + b
        ea = tot * a.sum() / tot.sum()
        eb = tot * b.sum() / tot.sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            chi = np.nansum((a - ea) ** 2 / ea) + np.nansum((b - eb) ** 2 / eb)
        pool = np.concatenate([idx_a, idx_b])
        na = len(idx_a)
        sims = []
        for _ in range(N_SIM):
            perm = RNG.permutation(pool)
            pa = np.bincount(mapper[OBS_DOY[perm[:na]]], minlength=k)
            pb = np.bincount(mapper[OBS_DOY[perm[na:]]], minlength=k)
            with np.errstate(divide="ignore", invalid="ignore"):
                sims.append(np.nansum((pa - ea) ** 2 / ea) + np.nansum((pb - eb) ** 2 / eb))
        return float(chi), float((np.array(sims) >= chi).mean()), a.tolist(), b.tolist()
    chi, p, a, b = homog(IDX_FALLEN, IDX_THRIVING, DOY_SIGN, 12)
    chi_e, p_e, ae, be = homog(IDX_FALLEN, IDX_THRIVING, SIGN_ELEMENT[DOY_SIGN], 4)
    share_f = np.array(a) / sum(a)
    share_t = np.array(b) / sum(b)
    gap = int(np.argmax(np.abs(share_f - share_t)))
    T["fallen_vs_thriving"] = {"label": "Fallen founders vs thriving founders", "n_fallen": int(len(IDX_FALLEN)), "n_thriving": int(len(IDX_THRIVING)),
                               "signs_fallen": a, "signs_thriving": b, "chi2": round(chi, 2), "p_perm": p, "elements_fallen": ae, "elements_thriving": be,
                               "chi2_elements": round(chi_e, 2), "p_perm_elements": p_e,
                               "verdict": (f"The sign mix of the {len(IDX_FALLEN)} fallen founders differs most at {SIGNS[gap]} ({100*share_f[gap]:.0f}% vs {100*share_t[gap]:.0f}% among thriving founders). "
                                           f"Shuffling the 'fallen' label {N_SIM:,} times produced a gap this large {100*p:.0f}% of the time"
                                           + (" — no signature of failure in the stars." if p > 0.1 else " — borderline." if p > 0.01 else " — unusual."))}

# ---- breakups --------------------------------------------------------------
def split_test(statuses):
    rows = breakup_rows(statuses)
    keyset = set()
    for r in rows:
        for x in _names(r.get("founder_a")):
            for y in _names(r.get("founder_b")):
                keyset.add((r["company"].strip(), frozenset([x, y])))
    broke = [(a, b) for a, b, c in all_pairs if (c, frozenset([F[a]["name"].lower(), F[b]["name"].lower()])) in keyset]
    intact = [(a, b) for a, b, c in all_pairs if (c, frozenset([F[a]["name"].lower(), F[b]["name"].lower()])) not in keyset]
    if len(broke) < 5 or not intact:
        return None
    e = SIGN_ELEMENT[DOY_SIGN[OBS_DOY]]
    def compat_rate(ps):
        return float(np.mean([(ELEMENTS[e[a]], ELEMENTS[e[b]]) in COMPATIBLE for a, b in ps]))
    obs_b, obs_i = compat_rate(broke), compat_rate(intact)
    allp = broke + intact
    nb = len(broke)
    sims = []
    for _ in range(N_SIM):
        perm = RNG.permutation(len(allp))
        sims.append(compat_rate([allp[i] for i in perm[:nb]]) - compat_rate([allp[i] for i in perm[nb:]]))
    sims = np.array(sims)
    diff = obs_b - obs_i
    p_two = float(min(1.0, 2 * min((sims >= diff).mean(), (sims <= diff).mean())))
    return {"n_broke": nb, "n_intact": len(intact), "compatible_broke": round(obs_b, 4), "compatible_intact": round(obs_i, 4), "diff": round(diff, 4),
            "band_lo": round(float(np.percentile(sims, 2.5)), 4), "band_hi": round(float(np.percentile(sims, 97.5)), 4), "p_two_sided": p_two,
            "split_pairs": [[F[a]["name"], F[b]["name"]] for a, b in broke]}
if all_pairs:
    pre = split_test({"broke up"})
    wide = split_test({"broke up", "board ouster"})
    if pre:
        T["breakups"] = dict(pre, label="Pairs that broke up vs pairs that stayed",
            verdict=(f"{100*pre['compatible_broke']:.0f}% of the {pre['n_broke']} cofounder pairs that fell out were a 'compatible' match, against {100*pre['compatible_intact']:.0f}% of the {pre['n_intact']} pairs that did not"
                     + (". The stars did not see the split coming." if pre["p_two_sided"] > 0.1 else ". A difference, but a small sample." if pre["p_two_sided"] > 0.01 else ". A real gap, worth a closer look.")))
        if wide:
            T["breakups"]["with_ousters"] = wide

# ---- company type by sign (exploratory, asked after pre-registration) -------
SECT = load_json(os.path.join(DATA, "sectors.json"), {})
if SECT:
    SECTORS = ["Software & internet", "Chips & hardware", "Money & finance", "Health & biotech", "Shops & consumer brands", "Energy, cars & industry"]
    def main_company(f):
        cs = [c for c in f["companies"] if c in company_by_name and c in SECT]
        return max(cs, key=lambda c: company_by_name[c]["value_usd"] or 0) if cs else None
    sidx, scomp = [], []
    for i, f in enumerate(F):
        c = main_company(f)
        if c:
            sidx.append(i); scomp.append(c)
    sidx = np.array(sidx)
    comp_names = sorted(set(scomp))
    comp_sector = np.array([SECTORS.index(SECT[c]["sector"]) for c in comp_names])
    comp_of = np.array([comp_names.index(c) for c in scomp])
    sign_of = DOY_SIGN[OBS_DOY[sidx]]
    def table(cs):
        t = np.zeros((12, 6))
        np.add.at(t, (sign_of, cs[comp_of]), 1)
        return t
    obs = table(comp_sector)
    def stat(t):
        e = t.sum(1, keepdims=True) * t.sum(0, keepdims=True) / t.sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.where(e > 0, (t - e) / np.sqrt(np.where(e > 0, e, 1)), 0)
            chi = np.nansum(np.where(e > 0, (t - e) ** 2 / np.where(e > 0, e, 1), 0))
        return chi, z.max(), e, z
    chi, zmax, exp, z = stat(obs)
    sims = []
    for _ in range(N_SIM):   # shuffle company types across companies; each company keeps its founders
        c2, zm2, _, _ = stat(table(RNG.permutation(comp_sector)))
        sims.append((c2, zm2))
    sims = np.array(sims)
    p_chi = float((sims[:, 0] >= chi).mean()); p_max = float((sims[:, 1] >= zmax).mean())
    tops = []
    for k, sec in enumerate(SECTORS):
        i = int(np.argmax(z[:, k]))
        tops.append({"sector": sec, "n": int(obs[:, k].sum()), "n_companies": int((comp_sector == k).sum()), "top_sign": SIGNS[i], "top_obs": int(obs[i, k]), "top_exp": round(float(exp[i, k]), 1)})
    bi, bk = np.unravel_index(np.argmax(z), z.shape)
    T["sectors"] = {"label": "Company type by Sun sign (exploratory)", "sectors": SECTORS, "n": int(len(sidx)), "counts": obs.astype(int).tolist(),
                    "expected": exp.round(2).tolist(), "p_chi2": p_chi, "p_max_cell": p_max, "tops": tops,
                    "verdict": (f"The strongest lean is {SIGNS[bi]} founders in {SECTORS[bk]}: {int(obs[bi, bk])} against {exp[bi, bk]:.1f} if signs and company types were unrelated. "
                                f"Shuffling company types between companies 10,000 times gave a lean at least this strong {100*p_max:.0f}% of the time"
                                + (", so it is luck." if p_max > 0.1 else ", borderline." if p_max > 0.01 else ", which is rare."))}

# ---- company value: which signs and sign pairs built the most (exploratory) --
# A founder's real question is "do matched cofounders build bigger companies?"
# Value = market cap or last private valuation; collapsed companies at peak value.
comp_members = defaultdict(list)
for i, f in enumerate(F):
    for c in f["companies"]:
        if c in company_by_name:
            comp_members[c].append(i)
cn = sorted(comp_members)
cval = np.array([float(company_by_name[c].get("value_usd") or 0) for c in cn])
thr = np.array([company_by_name[c]["ring"] in ("giants", "big") for c in cn])
Mtx = np.zeros((len(cn), N))
for k, c in enumerate(cn):
    Mtx[k, comp_members[c]] = 1
pool = np.array(sorted({i for k, c in enumerate(cn) if thr[k] for i in comp_members[c]}))
def sign_value(doys):
    oh = np.zeros((N, 12)); oh[np.arange(N), DOY_SIGN[doys]] = 1
    pres = (Mtx[thr] @ oh) > 0
    return cval[thr] @ pres
obs_sv = sign_value(OBS_DOY)
sims_sv = []
for _ in range(4000):
    perm = OBS_DOY.copy(); perm[pool] = OBS_DOY[RNG.permutation(pool)]
    sims_sv.append(sign_value(perm))
sims_sv = np.array(sims_sv)
share = obs_sv / obs_sv.sum(); sim_share_max = (sims_sv / sims_sv.sum(1, keepdims=True)).max(1)
top = int(np.argmax(obs_sv))
p_top = float((sim_share_max >= share[top]).mean())
top_cos = {}
for sgi in range(12):
    cs = [(cval[k], cn[k]) for k in range(len(cn)) if thr[k] and any(DOY_SIGN[OBS_DOY[i]] == sgi for i in comp_members[cn[k]])]
    top_cos[SIGNS[sgi]] = [n for v, n in sorted(cs, reverse=True)[:4]]
# pairs: do matched cofounders build bigger companies?
if all_pairs:
    pv = np.array([float(company_by_name[c].get("value_usd") or 0) for a, b, c in all_pairs])
    def matched(doys):
        e = SIGN_ELEMENT[DOY_SIGN[doys]]
        return np.array([(ELEMENTS[e[a]], ELEMENTS[e[b]]) in COMPATIBLE for a, b, c in all_pairs])
    def diff(mk):
        return float(np.median(pv[mk]) - np.median(pv[~mk])) if mk.any() and (~mk).any() else 0.0
    mk0 = matched(OBS_DOY); d0 = diff(mk0)
    sims_d = []
    for _ in range(4000):
        perm = OBS_DOY.copy(); perm[team_members_all] = OBS_DOY[RNG.permutation(team_members_all)]
        sims_d.append(diff(matched(perm)))
    sims_d = np.array(sims_d)
    p_d = float(min(1.0, 2 * min((sims_d >= d0).mean(), (sims_d <= d0).mean())))
    # one vote per company: teams that are mostly matched vs mostly unmatched
    tnames = sorted({c for a, b, c in all_pairs})
    tidx = {c: [k for k, (a, b, cc) in enumerate(all_pairs) if cc == c] for c in tnames}
    tval = np.array([float(company_by_name[c].get("value_usd") or 0) for c in tnames])
    def team_gap(mk):
        sh = np.array([mk[tidx[c]].mean() for c in tnames])
        hi, lo = tval[sh > 0.5], tval[sh < 0.5]
        return (float(np.median(hi)) if len(hi) else 0.0, float(np.median(lo)) if len(lo) else 0.0, int(len(hi)), int(len(lo)))
    tm0 = team_gap(mk0); tg0 = tm0[0] - tm0[1]
    sims_t = []
    for _ in range(4000):
        perm = OBS_DOY.copy(); perm[team_members_all] = OBS_DOY[RNG.permutation(team_members_all)]
        r = team_gap(matched(perm)); sims_t.append(r[0] - r[1])
    sims_t = np.array(sims_t)
    p_t = float(min(1.0, 2 * min((sims_t >= tg0).mean(), (sims_t <= tg0).mean())))
    cellv = np.zeros((12, 12))
    seen = set()
    for (a, b, c) in all_pairs:
        i, j = sorted((DOY_SIGN[OBS_DOY[a]], DOY_SIGN[OBS_DOY[b]]))
        if (i, j, c) not in seen:
            cellv[i, j] += company_by_name[c].get("value_usd") or 0; seen.add((i, j, c))
    # the pair cells behind the most value
    order = np.dstack(np.unravel_index(np.argsort(-cellv, axis=None), cellv.shape))[0][:5]
    T["value"] = {"label": "Company value by sign and by sign pair (exploratory)",
                  "sign_value": obs_sv.round(0).tolist(), "sign_share": share.round(4).tolist(), "top_sign": SIGNS[top], "top_share": round(float(share[top]), 4),
                  "p_top_share": p_top, "expected_top_share": round(float(sim_share_max.mean()), 4), "top_companies": top_cos,
                  "matched_median": float(np.median(pv[mk0])), "unmatched_median": float(np.median(pv[~mk0])), "n_matched": int(mk0.sum()), "n_unmatched": int((~mk0).sum()),
                  "p_median_diff": p_d, "cell_value": cellv.round(0).tolist(),
                  "teams_matched_median": tm0[0], "teams_unmatched_median": tm0[1], "n_teams_matched": tm0[2], "n_teams_unmatched": tm0[3], "p_teams": p_t,
                  "top_cells": [[int(i), int(j), float(cellv[i, j])] for i, j in order],
                  "verdict": (f"{SIGNS[top]} founders are behind {100*share[top]:.0f}% of all the value in the list. Random birthdays put one sign that high {100*p_top:.0f}% of the time, because a few giant companies swing it. "
                              f"Matched cofounder pairs built companies with a median value of ${np.median(pv[mk0])/1e9:.0f}B, unmatched pairs ${np.median(pv[~mk0])/1e9:.0f}B; luck makes a gap that size {100*p_d:.0f}% of the time.")}

# ---- Moon (exploratory) ----------------------------------------------------
if moon:
    idx = [i for i, f in enumerate(F) if f["key"] in moon and ("giants" in f["rings"] or "big" in f["rings"])]
    obs = np.zeros(12)
    for i in idx:
        cands = moon[F[i]["key"]]["moon"]
        for s in cands:
            obs[SIGNS.index(s)] += 1 / len(cands)
    # null: the Moon sign is nearly uniform over any multi-year span; expected = n/12 (the Moon's 27.3-day cycle is independent of the calendar)
    n = len(idx)
    exp = np.full(12, n / 12)
    chi = float(((obs - exp) ** 2 / exp).sum())
    sims = RNG.multinomial(n, np.full(12, 1 / 12), size=N_SIM)
    p = float((((sims - exp) ** 2 / exp).sum(axis=1) >= chi).mean())
    z = (obs - exp) / np.sqrt(exp)
    top = int(np.argmax(z))
    amb = sum(moon[F[i]["key"]]["moon_ambiguous"] for i in idx)
    T["moon"] = {"label": "Moon sign (exploratory, no birth times)", "n": n, "ambiguous": int(amb), "bins": SIGNS, "observed": obs.round(1).tolist(), "expected": exp.round(1).tolist(),
                 "chi2": round(chi, 2), "p_mc": p, "tallest": SIGNS[top],
                 "verdict": f"Moon in {SIGNS[top]} leads with {obs[top]:.0f} founders against {exp[top]:.0f} expected; {amb} of {n} founders could be one of two Moon signs and count half each. Chance produces a spread like this {100*p:.0f}% of the time."}

stats["signs_order"] = SIGNS
stats["sign_starts"] = STARTS
save_json(os.path.join(DATA, "stats.json"), stats)
for k, t in T.items():
    print(f"[{k}] {t.get('verdict', '')}")
