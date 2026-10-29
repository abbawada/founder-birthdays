"""Turn the verify-birthdays workflow results into pipeline/birthday_overrides.json.

Input: one or more workflow result files (JSON with result.results and
result.verdicts). A change is applied only when a skeptic accepted it.
Also writes research/birthday_checks.json (every verdict, for the methods note
and the spot-check report).
"""
import json
import os
import re
import sys

from common import ROOT, load_json, save_json

paths = sys.argv[1:]
results, verdicts = [], []
for pth in paths:
    obj = json.load(open(pth))
    res = obj.get("result", obj)
    results += res.get("results", [])
    verdicts += res.get("verdicts", [])
accepted = {v["key"]: v for v in verdicts if v.get("accept")}
rejected = {v["key"]: v for v in verdicts if not v.get("accept")}
overrides = load_json(os.path.join(ROOT, "pipeline", "birthday_overrides.json"), {})
applied, skipped = 0, []
for r in results:
    if r["verdict"] not in ("wrong", "found"):
        continue
    v = accepted.get(r["key"])
    if not v:
        skipped.append((r["name"], r["verdict"], (rejected.get(r["key"]) or {}).get("why", "no skeptic verdict")[:80]))
        continue
    date = v.get("date") or r.get("date")
    if not date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        skipped.append((r["name"], r["verdict"], f"bad date {date}"))
        continue
    overrides[r["key"]] = {"birthday": date, "source_url": v.get("source_url") or r.get("source_url"), "source": "verified: " + (r.get("source_kind") or r["verdict"]), "note": r.get("note", "")[:200]}
    applied += 1
save_json(os.path.join(ROOT, "pipeline", "birthday_overrides.json"), overrides)
save_json(os.path.join(ROOT, "research", "birthday_checks.json"), {"results": results, "verdicts": verdicts})
from collections import Counter
print(Counter(r["verdict"] for r in results), "| applied", applied, "| skipped", len(skipped))
for s in skipped[:20]:
    print("  skipped:", s)
