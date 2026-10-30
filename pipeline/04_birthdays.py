"""Phase 2b: birthdays and places for every founder.

Wikidata P569 through the full statement path (precision 11 = day only).
If Wikidata has no day-precision date, read the person's English Wikipedia
infobox birth_date template and store that URL. Never from memory.

Output: data/founders.json (one row per person, companies listed).
"""
import os
import re
from collections import defaultdict

from common import DATA, ROOT, load_json, save_json, sparql, chunks, wp_page, infobox, strip_markup

rows = load_json(os.path.join(DATA, "founders_raw.json"))
people = {}
for r in rows:
    key = r["founder_qid"] or ("name:" + r["founder_name"])
    p = people.setdefault(key, {"qid": r["founder_qid"], "name": r["founder_name"], "companies": [], "wp_title": r.get("wp_title"), "roster_sources": set()})
    p["companies"].append(r["company"])
    p["roster_sources"].add(r["source"])
    if r.get("wp_title") and not p["wp_title"]:
        p["wp_title"] = r["wp_title"]

qids = sorted(q for q in people if not q.startswith("name:"))
facts = defaultdict(lambda: {"dob": [], "citizenship": set(), "birthplace": None, "birthplace_country": None, "lat": None, "lon": None, "gender": None, "enwiki": None, "label": None})
for chunk in chunks(qids, 60):
    vals = " ".join("wd:" + q for q in chunk)
    res = sparql(f"""SELECT ?p ?pLabel ?dob ?prec ?rank ?cit ?citLabel ?bp ?bpLabel ?bpc ?bpcLabel ?coord ?gender ?genderLabel ?art WHERE {{
      VALUES ?p {{ {vals} }}
      OPTIONAL {{ ?p p:P569 ?st . ?st psv:P569 ?v . ?v wikibase:timeValue ?dob ; wikibase:timePrecision ?prec . ?st wikibase:rank ?rank . }}
      OPTIONAL {{ ?p wdt:P27 ?cit . }}
      OPTIONAL {{ ?p wdt:P19 ?bp . OPTIONAL {{ ?bp wdt:P17 ?bpc . }} OPTIONAL {{ ?bp wdt:P625 ?coord . }} }}
      OPTIONAL {{ ?p wdt:P21 ?gender . }}
      OPTIONAL {{ ?art schema:about ?p ; schema:isPartOf <https://en.wikipedia.org/> . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")
    for b in res:
        q = b["p"]["value"].split("/")[-1]
        f = facts[q]
        f["label"] = b["pLabel"]["value"]
        if "dob" in b:
            f["dob"].append((b["dob"]["value"][:10], int(b["prec"]["value"]), b["rank"]["value"].split("#")[-1]))
        if "citLabel" in b:
            f["citizenship"].add(b["citLabel"]["value"])
        if "bpLabel" in b and not f["birthplace"]:
            f["birthplace"] = b["bpLabel"]["value"]
            f["birthplace_country"] = b.get("bpcLabel", {}).get("value")
            if "coord" in b:
                m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", b["coord"]["value"])
                if m:
                    f["lon"], f["lat"] = float(m.group(1)), float(m.group(2))
        if "genderLabel" in b:
            f["gender"] = b["genderLabel"]["value"]
        if "art" in b:
            f["enwiki"] = b["art"]["value"]

MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"])}


def wp_birthday(title):
    pg = wp_page(title)
    if not pg:
        return None, None, None
    _, fields = infobox(pg["text"])
    raw = fields.get("birth_date") or fields.get("born") or ""
    m = re.search(r"\{\{\s*(?:birth[ _-]date(?: and age)?|bda|dob)\s*\|(?:\s*(?:df|mf)\s*=\s*\w+\s*\|)?\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", raw, re.I)
    if m:
        y, mo, d = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}", pg["url"], strip_markup(raw)[:80]
    clean = strip_markup(raw)
    if not re.search(r"\d{4}", clean):
        # no usable infobox date: try the lead sentence "(born 12 March 1965" / "(born March 12, 1965"
        lead = strip_markup(re.sub(r"\{\{Infobox.*?\n\}\}", "", pg["text"][:6000], flags=re.S))
        m = re.search(r"\(born\s+(?:[^()\d]{0,60}?)(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})", lead)
        if m:
            clean = m.group(1)
    m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})", clean)
    if m:
        return f"{int(m.group(3)):04d}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}", pg["url"], clean[:80]
    m = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", clean)
    if m:
        return f"{int(m.group(3)):04d}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}", pg["url"], clean[:80]
    return None, pg["url"], clean[:80]


out = []
for key, p in people.items():
    q = p["qid"]
    f = facts.get(q) if q else None
    rec = {"qid": q, "name": (f["label"] if f and f["label"] and not f["label"].startswith("Q") else p["name"]), "companies": sorted(set(p["companies"])),
           "roster_sources": sorted(p["roster_sources"]), "birthday": None, "birth_precision": None, "birth_source": None, "birth_source_url": None,
           "birth_raw": None, "citizenship": sorted(f["citizenship"]) if f else [], "birthplace": f["birthplace"] if f else None,
           "birthplace_country": f["birthplace_country"] if f else None, "lat": f["lat"] if f else None, "lon": f["lon"] if f else None,
           "gender": f["gender"] if f else None, "wikipedia_url": (f["enwiki"] if f and f["enwiki"] else (("https://en.wikipedia.org/wiki/" + p["wp_title"].replace(" ", "_")) if p.get("wp_title") else None)),
           "wikidata_url": f"https://www.wikidata.org/wiki/{q}" if q else None}
    if f and f["dob"]:
        best = sorted(f["dob"], key=lambda t: (t[2] == "PreferredRank", t[1]), reverse=True)[0]
        if best[1] >= 11 and not best[0].startswith("-"):
            rec.update({"birthday": best[0], "birth_precision": "day", "birth_source": "wikidata", "birth_source_url": rec["wikidata_url"]})
        else:
            rec.update({"birth_precision": {9: "year", 10: "month"}.get(best[1], str(best[1])), "birth_raw": best[0]})
    if not rec["birthday"]:
        title = None
        if rec["wikipedia_url"]:
            title = rec["wikipedia_url"].split("/wiki/")[-1].replace("_", " ")
        if title:
            bd, url, raw = wp_birthday(title)
            if bd:
                rec.update({"birthday": bd, "birth_precision": "day", "birth_source": "wikipedia infobox", "birth_source_url": url, "birth_raw": raw})
            elif raw:
                rec["birth_raw"] = raw
            if bd:
                rec["birth_source"] = "wikipedia infobox" if "{{" in (raw or "") or re.search(r"\d{4}", strip_markup(raw or "")) else "wikipedia lead"
    out.append(rec)
# verified corrections and found dates from the review workflow (pipeline/birthday_overrides.json: key -> {birthday, source_url, source})
bo = load_json(os.path.join(ROOT, "pipeline", "birthday_overrides.json"), {})
n_bo = 0
for rec in out:
    k = rec["qid"] or ("name:" + rec["name"])
    o = bo.get(k)
    if o and "retract" in o and not o.get("birthday"):
        rec.update({"birthday": None, "birth_precision": None, "birth_source": None, "birth_source_url": None, "birth_raw": "retracted: " + o["retract"][:120]})
        n_bo += 1
        continue
    if o and o.get("birthday"):
        rec.update({"birthday": o["birthday"], "birth_precision": "day", "birth_source": o.get("source", "verified"), "birth_source_url": o.get("source_url"), "birth_raw": (rec.get("birth_raw") or "") + " | verified"})
        n_bo += 1
print(n_bo, "birthdays set from verified overrides")
# names: Wikidata's English label, except where it was vandalised or carries a typo (pipeline/name_fixes.json: qid -> {name, reason, source_url})
nf = load_json(os.path.join(ROOT, "pipeline", "name_fixes.json"), {})
for rec in out:
    if rec["qid"] in nf:
        rec["name"] = nf[rec["qid"]]["name"]
print(sum(1 for r in out if r["qid"] in nf), "names fixed by hand")
save_json(os.path.join(DATA, "founders.json"), out)
dated = [o for o in out if o["birthday"]]
print(len(out), "people;", len(dated), "day-dated (", sum(o['birth_source'] == 'wikidata' for o in dated), "wikidata,", sum(o['birth_source'] == 'wikipedia infobox' for o in dated), "wikipedia );", len(out) - len(dated), "missing")
