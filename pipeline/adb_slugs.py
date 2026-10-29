"""Print Astro-Databank page slugs ("Last,_First") for founders not yet looked
up in research/adb_raw.json, Giants and Fallen rings first. Output is pasted
into the in-app browser fetch loop. Chinese, Korean, Japanese, and Vietnamese
names on Wikipedia are usually family-name first, so both orders are emitted.
"""
import json
import os
import re
import sys

from common import DATA, ROOT, load_json

founders = load_json(os.path.join(DATA, "founders.json"))
companies = {c["name"]: c for c in load_json(os.path.join(DATA, "companies.json"))}
raw = load_json(os.path.join(ROOT, "research", "adb_raw.json"), {})
rings = sys.argv[1].split(",") if len(sys.argv) > 1 else ["giants", "fallen"]
EAST = {"People's Republic of China", "China", "Taiwan", "Republic of China", "Hong Kong", "South Korea", "Japan", "Vietnam", "Singapore"}
out = []
for f in founders:
    if not f.get("birthday"):
        continue
    if not any(companies.get(c, {}).get("ring") in rings for c in f["companies"]):
        continue
    name = re.sub(r"\s*\(.*?\)", "", f["name"]).strip()
    parts = [p for p in name.split() if not re.fullmatch(r"[A-Z]\.?", p)]  # drop middle initials
    if len(parts) < 2:
        continue
    east = (f.get("birthplace_country") in EAST) or any(c in EAST for c in f.get("citizenship", []))
    cands = [parts[-1] + ",_" + "_".join(parts[:-1])]
    if east:
        cands.append(parts[0] + ",_" + "_".join(parts[1:]))
    if len(parts) > 2:
        cands.append(parts[-1] + ",_" + parts[0])
    for c in cands:
        if c not in raw and c not in out:
            out.append(c)
print(json.dumps(out, ensure_ascii=False))
print(len(out), "slugs", file=sys.stderr)
