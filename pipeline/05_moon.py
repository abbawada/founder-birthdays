"""Exploratory: Moon sign (and tropical Sun longitude) from the birth date with
the Swiss Ephemeris. Without a birth time the Moon can be in one of two signs
on about 40% of dates; both candidates are kept and the page shows "A or B".
Local midnight to local 23:59 is approximated from the birthplace longitude
(one hour per 15 degrees); founders without a birthplace use UTC.

Reads data/founders.json, writes data/moon.json {qid_or_name: {...}}.
"""
import os

import swisseph as swe

from common import DATA, load_json, save_json

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
founders = load_json(os.path.join(DATA, "founders.json"))
out = {}
for f in founders:
    if not f.get("birthday"):
        continue
    y, m, d = map(int, f["birthday"].split("-"))
    tz = round(f["lon"] / 15.0) if f.get("lon") is not None else 0
    jd0 = swe.julday(y, m, d, 0.0 - tz)
    jd1 = swe.julday(y, m, d, 23.983 - tz)
    moon0 = swe.calc_ut(jd0, swe.MOON)[0][0]
    moon1 = swe.calc_ut(jd1, swe.MOON)[0][0]
    sun = swe.calc_ut(swe.julday(y, m, d, 12.0 - tz), swe.SUN)[0][0]
    s0, s1 = SIGNS[int(moon0 // 30)], SIGNS[int(moon1 // 30)]
    key = f["qid"] or ("name:" + f["name"])
    out[key] = {
        "moon": [s0] if s0 == s1 else [s0, s1],
        "moon_ambiguous": s0 != s1,
        "sun_tropical": SIGNS[int(sun // 30)],
        "sun_longitude": round(sun, 2),
        "tz_assumed": tz,
    }
save_json(os.path.join(DATA, "moon.json"), out)
n = len(out)
amb = sum(v["moon_ambiguous"] for v in out.values())
print(n, "founders with Moon signs;", amb, f"ambiguous ({100*amb/n:.0f}%)")
