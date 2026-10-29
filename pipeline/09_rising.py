"""Exploratory: Rising (Ascendant) and exact Moon sign for founders whose birth
time is recorded in Astro-Databank (research/adb_raw.json, read page by page
in the in-app browser; each entry keeps the Rodden rating).

AA = birth certificate, A = from memory or news, B = biography, C = caution,
DD = conflicting, X = date without time (no Rising possible).
Writes data/rising.json keyed like founders.json (qid or name:...).
Also writes data/adb_birthday_check.json: Astro-Databank's date vs ours.
"""
import json
import os
import re

import swisseph as swe

from common import DATA, ROOT, load_json, save_json

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"])}
raw = load_json(os.path.join(ROOT, "research", "adb_raw.json"), {})
founders = load_json(os.path.join(DATA, "founders.json"))


def norm(s):
    s = s.lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9 ,.'-]", "", s)
    return re.sub(r"\s+", " ", s).strip()


by_name = {}
for f in founders:
    by_name[norm(f["name"])] = f
    # also "last, first" form
    parts = f["name"].split()
    if len(parts) >= 2:
        by_name[norm(parts[-1] + ", " + " ".join(parts[:-1]))] = f


def parse_coord(s):
    m = re.match(r"(\d+)([nsew])(\d+)", s.strip().lower())
    if not m:
        return None
    v = int(m.group(1)) + int(m.group(3)) / 60
    return -v if m.group(2) in "sw" else v


out, check = {}, []
for slug, e in raw.items():
    if e.get("none") or not e.get("born"):
        continue
    f = by_name.get(norm(slug.split("(")[0]))
    if not f:
        # slug like "Bankman-Fried,_Sam" -> "sam bankman-fried"
        last, _, first = slug.replace("_", " ").partition(",")
        f = by_name.get(norm(first.strip() + " " + last.strip()))
    if not f:
        continue
    key = f["qid"] or ("name:" + f["name"])
    m = re.match(r"(\d{1,2}) (\w+) (\d{4})(?: at (\d{1,2}):(\d{2}))?", e["born"])
    if not m:
        continue
    d, mon, y = int(m.group(1)), MONTHS.get(m.group(2).lower()), int(m.group(3))
    adb_date = f"{y:04d}-{mon:02d}-{d:02d}" if mon else None
    check.append({"name": f["name"], "ours": f.get("birthday"), "astro_databank": adb_date, "rating": e.get("rr"), "match": (adb_date == f.get("birthday")) if f.get("birthday") else None})
    if adb_date != f.get("birthday"):
        continue  # same name, different person (or a date conflict): never borrow their time
    rec = {"rating": e.get("rr"), "adb_slug": slug, "adb_url": "https://www.astro.com/astro-databank/" + slug}
    if m.group(4) and e.get("rr") in ("AA", "A", "B", "C") and e.get("place") and e.get("tz"):
        hh, mm = int(m.group(4)), int(m.group(5))
        coords = re.findall(r"\d+[nsew]\d+", e["place"].lower())
        tzm = re.search(r"h(\d+(?:\.\d+)?)([we])", e["tz"])
        if len(coords) == 2 and tzm:
            lat, lon = parse_coord(coords[0]), parse_coord(coords[1])
            off = float(tzm.group(1)) * (-1 if tzm.group(2) == "w" else 1)
            ut = hh + mm / 60 - off
            jd = swe.julday(y, mon, d, ut)
            asc = swe.houses(jd, lat, lon, b"P")[1][0]
            moon = swe.calc_ut(jd, swe.MOON)[0][0]
            sun = swe.calc_ut(jd, swe.SUN)[0][0]
            rec.update({"rising": SIGNS[int(asc // 30)], "moon": SIGNS[int(moon // 30)], "sun": SIGNS[int(sun // 30)], "time": f"{hh:02d}:{mm:02d} local", "place": e["place"], "tz": e["tz"]})
    out[key] = rec
save_json(os.path.join(DATA, "rising.json"), out)
save_json(os.path.join(DATA, "adb_birthday_check.json"), check)
n_r = sum(1 for v in out.values() if v.get("rising"))
mism = [c for c in check if c["match"] is False]
print(len(out), "founders matched to Astro-Databank;", n_r, "with a Rising sign;", len(check), "birthday cross-checks,", len(mism), "mismatches:", [(c['name'], c['ours'], c['astro_databank']) for c in mism])
