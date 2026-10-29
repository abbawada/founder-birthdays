"""Phase 1c: assign rings and apply exclusions.

Giants: value >= $100B, Big: $20B to $100B, both founded 1960-2023 with at
least one named human founder. Fallen: research/failed_verified.csv rows with
included = yes. Overrides (pipeline/overrides.json) can exclude a company
("exclude": reason) or fix its founders / founded year.
Output: data/companies.json and data/companies.csv
"""
import csv
import os

from common import DATA, ROOT, load_json, save_json, wp_page

raw = load_json(os.path.join(DATA, "companies_raw.json"))
overrides = load_json(os.path.join(ROOT, "pipeline", "overrides.json"), {})
out = []
excluded = []
for r in raw:
    ov = overrides.get(r["name"], {})
    if ov.get("exclude"):
        excluded.append((r["name"], ov["exclude"]))
        continue
    fy = ov.get("founded_year") or r.get("founded_year")
    founders_wp = ov.get("founders") if ov.get("founders") is not None else r.get("founders_wp", [])
    if not fy or fy < 1960 or fy > 2023:
        excluded.append((r["name"], f"founded {fy}"))
        continue
    if not founders_wp and not r.get("founders_wd"):
        excluded.append((r["name"], "no named founder"))
        continue
    ring = "giants" if r["value_usd"] >= 100e9 else "big"
    out.append({**r, "founded_year": fy, "founders_wp": founders_wp, "ring": ring, "notes": ov.get("note", "")})

fallen_path = os.path.join(ROOT, "research", "failed_verified.csv")
n_fallen = 0
if os.path.exists(fallen_path):
    names_in = {c["name"].lower() for c in out}
    for r in csv.DictReader(open(fallen_path)):
        if (r.get("included") or "").strip().lower() != "yes":
            continue
        try:
            fy = int(r["founded_year"])
            peak = float(r["peak_value_usd_bn"])
        except (ValueError, KeyError):
            continue
        if fy < 1960:
            continue
        title = (r.get("wikipedia_url") or "").split("/wiki/")[-1].replace("_", " ")
        pg = wp_page(title) if title else None
        founders = [x.strip() for x in (r.get("founders") or "").split(";") if x.strip() and x.strip().lower() != "unverified"]
        # a company on the private board that has since collapsed belongs to the fallen ring only
        out = [c for c in out if c["name"].lower() != r["company"].strip().lower()]
        out.append({"name": r["company"].strip(), "ticker": "", "country": "", "value_usd": int(peak * 1e9), "value_kind": f"peak value, {r.get('peak_year','')}",
                    "value_date": r.get("peak_year", ""), "value_source": r.get("peak_source_url", ""), "listing": "fallen",
                    "article": pg["title"] if pg else None, "article_url": pg["url"] if pg else r.get("wikipedia_url"), "qid": pg["qid"] if pg else None,
                    "founded_year": fy, "founders_wp": founders, "founders_wd": {}, "ring": "fallen",
                    "outcome": r.get("outcome", ""), "outcome_year": r.get("outcome_year", ""), "outcome_source": r.get("outcome_source_url", ""), "notes": r.get("notes", "")})
        n_fallen += 1
save_json(os.path.join(DATA, "companies.json"), out)
save_json(os.path.join(DATA, "companies_excluded.json"), excluded)
with open(os.path.join(DATA, "companies.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["name", "ring", "founded_year", "value_usd_bn", "value_kind", "value_date", "value_source", "country", "wikipedia", "founders"])
    for c in sorted(out, key=lambda c: (c["ring"], -c["value_usd"])):
        w.writerow([c["name"], c["ring"], c["founded_year"], round(c["value_usd"] / 1e9, 1), c["value_kind"], c["value_date"], c["value_source"], c["country"],
                    c.get("article_url", ""), "; ".join(c["founders_wp"] or list((c.get("founders_wd") or {}).values()))])
from collections import Counter
print(Counter(c["ring"] for c in out), "| excluded:", Counter(e[1].split(" ")[0] for e in excluded).most_common(5))
