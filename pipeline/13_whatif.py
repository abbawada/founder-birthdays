"""What-if cofounders (just for fun, exploratory): the ten sign pairs whose real
cofounders built the most company value, each filled with the two best-known
founders of those signs who never built a company together.

Candidates are founders of $100B+ companies, best known first (number of
Wikipedia language editions with an article, from Wikidata sitelinks). Portraits: the person's Wikidata image (P18) from Wikimedia Commons,
with author and licence kept for the credits, redrawn as a two-colour halftone
print (ink over red) to match the page. Output: data/whatif.json.
"""
import base64
import calendar
import html
import os
import re

import cv2
import numpy as np
import requests

from common import DATA, ROOT, UA, load_json, save_json, sparql, chunks, get_json

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

# portraits
IMG = os.path.join(ROOT, "cache", "img")
os.makedirs(IMG, exist_ok=True)
face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
strip = lambda t: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t or ""))).strip()


def portrait(person):
    fname = requests.utils.unquote(person["img"].split("/Special:FilePath/")[-1])
    body = get_json("commons", "https://commons.wikimedia.org/w/api.php", {"action": "query", "titles": "File:" + fname, "prop": "imageinfo",
                    "iiprop": "url|extmetadata|mime", "iiurlwidth": 480, "format": "json"})
    ii = next(iter(body["query"]["pages"].values()))["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    path = os.path.join(IMG, person["qid"] + "_480.img")
    if not os.path.exists(path):
        r = requests.get(ii["thumburl"], headers=UA, timeout=60)
        r.raise_for_status()
        open(path, "wb").write(r.content)
    im = cv2.imread(path)
    if im is None:
        raise RuntimeError(f"could not read {path}")
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    H0, W0 = g.shape
    fs = face.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
    if len(fs):
        x, y, w, h = max(fs, key=lambda r: r[2] * r[3])
        ch = int(h * 2.5); cw = int(ch * 0.8); cx = x + w // 2; top = max(0, y - int(h * 0.55))
    else:
        cw = min(W0, int(H0 * 0.8)); ch = int(cw / 0.8); cx = W0 // 2; top = 0
    x0 = max(0, min(W0 - cw, cx - cw // 2)); crop = g[top:top + ch, x0:x0 + cw]
    crop = cv2.resize(crop, (320, 400), interpolation=cv2.INTER_AREA)
    crop = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(6, 6)).apply(crop).astype(np.float32)   # lift faces in dark photos
    lo, hi = np.percentile(crop, 3), np.percentile(crop, 97)
    crop = np.clip((crop - lo) / max(1, hi - lo), 0, 1)
    crop = 1 / (1 + np.exp(-(crop - 0.47) * 5.0))                            # S-curve: darker shadows, cleaner highlights
    crop = (crop - crop.min()) / max(1e-6, crop.max() - crop.min())
    crop = cv2.GaussianBlur(crop, (3, 3), 0)
    yy, xx = np.mgrid[0:400, 0:320]
    oval = np.clip(1.35 - np.sqrt(((xx - 160) / 132.0) ** 2 + ((yy - 182) / 172.0) ** 2) * 1.35, 0, 1)   # cameo: fade to paper outside a soft oval
    oval = cv2.GaussianBlur(oval.astype(np.float32), (0, 0), 6)
    dark = (1 - crop) * oval
    out = np.zeros((400, 320, 4), np.float32)
    PAD = 60

    def halftone(cell, angle, gain, scale):
        big = cv2.copyMakeBorder(dark, PAD, PAD, PAD, PAD, cv2.BORDER_CONSTANT, value=0)
        hh, ww = big.shape
        M = cv2.getRotationMatrix2D((ww / 2, hh / 2), angle, 1.0)
        rot = cv2.warpAffine(big, M, (ww, hh), borderValue=0)
        canvas = np.zeros((hh, ww), np.uint8)
        for y0 in range(0, hh, cell):
            for x0 in range(0, ww, cell):
                v = float(rot[y0:y0 + cell, x0:x0 + cell].mean()) * gain
                r = cell * scale * np.sqrt(min(1.0, v))
                if v > 0.1 and r > 0.4:
                    cv2.circle(canvas, (x0 + cell // 2, y0 + cell // 2), max(1, int(round(r))), 255, -1, lineType=cv2.LINE_AA)
        Mi = cv2.getRotationMatrix2D((ww / 2, hh / 2), -angle, 1.0)
        back = cv2.warpAffine(canvas, Mi, (ww, hh), borderValue=0)
        return back[PAD:PAD + 400, PAD:PAD + 320].astype(np.float32) / 255.0

    def lay(cov, bgr, dx=0, dy=0):
        cov = np.roll(np.roll(cov, dy, 0), dx, 1)
        for k in range(3):
            out[..., k] = out[..., k] * (1 - cov) + bgr[k] * cov
        out[..., 3] = np.maximum(out[..., 3], cov)
    lay(halftone(5, 15, 0.95, 0.62), (62, 76, 220), dx=2, dy=2)           # red plate, offset like a misregistered print
    lay(halftone(3, 45, 1.05, 0.7), (40, 27, 29))                        # ink plate
    out = np.dstack([out[..., :3], out[..., 3] * 255]).clip(0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".webp", out, [cv2.IMWRITE_WEBP_QUALITY, 82])
    if not ok:
        raise RuntimeError("webp encode failed")
    lic = strip(meta.get("LicenseShortName", {}).get("value"))
    return {"src": "data:image/webp;base64," + base64.b64encode(buf.tobytes()).decode(), "credit": strip(meta.get("Artist", {}).get("value"))[:120],
            "license": lic, "file_url": ii.get("descriptionurl"), "face_found": bool(len(fs))}


out = []
for w in picks:
    row = {k: w[k] for k in ("rank", "cell", "cell_value", "n_real_pairs", "real_examples", "match")}
    for side in ("a", "b"):
        p = w[side]
        row[side] = {k: p[k] for k in ("name", "qid", "sign", "bday", "company", "value", "sl")}
        row[side].update(portrait(p))
    out.append(row)
save_json(os.path.join(DATA, "whatif.json"), out)
for r in out:
    print(r["rank"], f'{r["a"]["name"]} ({r["a"]["sign"]}) + {r["b"]["name"]} ({r["b"]["sign"]})', f'cell ${r["cell_value"]/1e12:.1f}T', "match" if r["match"] else "clash",
          "| faces:", r["a"]["face_found"], r["b"]["face_found"], "|", r["a"]["license"], "/", r["b"]["license"])
