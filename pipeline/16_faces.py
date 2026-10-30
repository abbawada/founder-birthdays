"""Small faces for the team builder: the best-known founders (most Wikipedia
language editions, from Wikidata sitelinks) whose Wikidata image shows a clear
face (OpenCV's YuNet face detector, at least 85% sure), styled like the what-if portraits but shrunk to 160x200. Founders without
a face here get a drawn medallion with their sign on the page. Also each
founder's year of death (Wikidata P570), so an imagined founding year never
lands after one of them died. Output: data/faces.json, data/deaths.json.
"""
import os

from common import DATA, chunks, load_json, save_json, sparql
from portraits import portrait

N = 80
founders = [f for f in load_json(os.path.join(DATA, "founders.json")) if f.get("birthday") and f.get("qid")]
info = {}
for ch in chunks([f["qid"] for f in founders], 30):
    vals = " ".join("wd:" + q for q in ch)
    for b in sparql(f"SELECT ?p ?sl ?img WHERE {{ VALUES ?p {{ {vals} }} ?p wikibase:sitelinks ?sl . OPTIONAL {{ ?p wdt:P18 ?img }} }}"):
        q = b["p"]["value"].split("/")[-1]
        cur = info.setdefault(q, {"sl": int(b["sl"]["value"]), "img": None})
        if "img" in b and not cur["img"]:
            cur["img"] = b["img"]["value"]
pool = sorted([{"name": f["name"], "qid": f["qid"], **info[f["qid"]]} for f in founders if info.get(f["qid"], {}).get("img")], key=lambda p: -p["sl"])
faces, skipped = {}, []
for p in pool:
    if len(faces) == N:
        break
    if p["name"] in faces:
        continue
    pr = portrait(p, size=(160, 200), strict=True)
    if not pr["face_found"]:
        skipped.append(p["name"])
        continue
    faces[p["name"]] = {k: pr[k] for k in ("src", "credit", "license", "file_url")}
save_json(os.path.join(DATA, "faces.json"), faces)
deaths = {}
for ch in chunks([f["qid"] for f in founders], 60):
    vals = " ".join("wd:" + q for q in ch)
    for b in sparql(f"SELECT ?p ?d WHERE {{ VALUES ?p {{ {vals} }} ?p p:P570/psv:P570 [ wikibase:timeValue ?d ] . }}"):
        q, y = b["p"]["value"].split("/")[-1], int(b["d"]["value"][:4])
        deaths[q] = min(deaths.get(q, y), y)
save_json(os.path.join(DATA, "deaths.json"), deaths)
print(len(deaths), "founders have died (Wikidata P570)")
kb = sum(len(v["src"]) for v in faces.values()) / 1024
print(f"{len(faces)} faces, {kb:.0f} KB inlined; no clear face for {len(skipped)}: {', '.join(skipped[:12])}")
