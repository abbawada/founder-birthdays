"""Phase 1b: resolve each candidate to its Wikipedia article and Wikidata item,
read founding year and founders from the infobox, union with Wikidata P112.

Output: data/companies_raw.json (one row per candidate, with flags for review).
Overrides in pipeline/overrides.json win over automatic picks.
"""
import json
import os
import re
import sys

from common import DATA, ROOT, infobox, load_json, names_from_field, save_json, sparql, strip_markup, wp_page, wp_search, chunks

cands = load_json(os.path.join(DATA, "candidates.json"))
overrides = load_json(os.path.join(ROOT, "pipeline", "overrides.json"), {})
COMPANY_BOXES = ("company", "business", "organization", "organisation", "bank", "dot-com company", "brand", "website", "exchange", "law firm", "airline", "cooperative")


def tokens(s):
    return set(re.findall(r"[a-z0-9]+", s.lower())) - {"inc", "corp", "corporation", "co", "ltd", "limited", "group", "holdings", "holding", "the", "company", "plc", "ag", "sa", "se", "nv", "international", "technologies", "technology", "industries"}


def pick_article(c):
    ov = overrides.get(c["name"], {})
    if ov.get("article"):
        pg = wp_page(ov["article"])
        return pg, "override"
    base = re.sub(r"\s*\(.*?\)", "", c["name"]).strip()
    alt = re.search(r"\((.*?)\)", c["name"])
    queries = [base]
    if alt:
        queries.insert(0, alt.group(1))
    tried = []
    for q in queries:
        for s in wp_search(q + " company")[:6] + wp_search(q)[:4]:
            if s["title"] in tried:
                continue
            tried.append(s["title"])
            pg = wp_page(s["title"])
            if not pg or not pg["text"]:
                continue
            box, fields = infobox(pg["text"])
            if not box or not any(box.startswith(b) for b in COMPANY_BOXES):
                continue
            # evidence it is the right company: ticker in traded_as, or strong name overlap
            traded = strip_markup(fields.get("traded_as", "") + " " + fields.get("ticker", ""))
            tick = c["ticker"].split(".")[0]
            name_ok = len(tokens(q) & tokens(pg["title"])) >= max(1, min(2, len(tokens(q))))
            tick_ok = bool(tick) and re.search(r"\b" + re.escape(tick) + r"\b", traded) is not None
            if tick_ok or name_ok:
                return pg, "ticker" if tick_ok else "name"
    return None, "none"


def founded_year(fields):
    raw = ""
    for k in ("founded", "foundation", "founding", "established", "formation", "founded_date", "formed"):
        if fields.get(k):
            raw = fields[k]
            break
    clean = strip_markup(raw)
    yrs = [int(y) for y in re.findall(r"(?<!\d)(1[6-9]\d\d|20[0-2]\d)(?!\d)", clean)]
    return (min(yrs) if yrs else None), clean[:200]


out = []
for i, c in enumerate(cands):
    pg, how = pick_article(c)
    row = dict(c)
    ov = overrides.get(c["name"], {})
    if not pg:
        row.update({"article": None, "qid": None, "match": how, "founded_year": None, "founders_wp": [], "flags": ["no article"]})
        out.append(row)
        continue
    box, fields = infobox(pg["text"])
    fy, fraw = founded_year(fields)
    founders = names_from_field(fields.get("founders") or fields.get("founder") or "")
    if ov.get("founded_year"):
        fy = ov["founded_year"]
    if ov.get("founders") is not None:
        founders = ov["founders"]
    flags = []
    if fy is None:
        flags.append("no founded year")
    if not founders:
        flags.append("no founders in infobox")
    if how == "name" and c["listing"] == "public":
        flags.append("matched by name only")
    row.update({"article": pg["title"], "article_url": pg["url"], "qid": pg["qid"], "match": how, "infobox": box,
                "founded_year": fy, "founded_raw": fraw, "founders_wp": founders, "flags": flags})
    out.append(row)
    if i % 100 == 0:
        print(i, "/", len(cands), file=sys.stderr)

# Wikidata founders (P112, humans) for every matched QID
qids = sorted({r["qid"] for r in out if r.get("qid")})
wd_founders = {}
wd_inception = {}
for chunk in chunks(qids, 80):
    vals = " ".join("wd:" + q for q in chunk)
    res = sparql(f"""SELECT ?c ?inc ?f ?fLabel WHERE {{ VALUES ?c {{ {vals} }}
      OPTIONAL {{ ?c wdt:P571 ?inc }}
      OPTIONAL {{ ?c wdt:P112 ?f . ?f wdt:P31 wd:Q5 . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")
    for b in res:
        q = b["c"]["value"].split("/")[-1]
        if "inc" in b:
            y = b["inc"]["value"][:4]
            if y.isdigit():
                wd_inception[q] = min(wd_inception.get(q, 9999), int(y))
        if "f" in b:
            wd_founders.setdefault(q, {})[b["f"]["value"].split("/")[-1]] = b["fLabel"]["value"]
for r in out:
    q = r.get("qid")
    r["founders_wd"] = wd_founders.get(q, {})
    r["inception_wd"] = wd_inception.get(q)
    if r.get("founded_year") is None and r.get("inception_wd"):
        r["founded_year"] = r["inception_wd"]
        r["flags"] = [f for f in r["flags"] if f != "no founded year"] + ["founded year from Wikidata"]
    if not r.get("founders_wp") and r["founders_wd"]:
        r["flags"] = [f for f in r["flags"] if f != "no founders in infobox"] + ["founders from Wikidata only"]

save_json(os.path.join(DATA, "companies_raw.json"), out)
inwin = [r for r in out if r.get("founded_year") and r["founded_year"] >= 1960]
named = [r for r in inwin if r.get("founders_wp") or r.get("founders_wd")]
print(len(out), "candidates;", len(inwin), "founded 1960+;", len(named), "with any founder names")
from collections import Counter
print(Counter(f for r in out for f in r["flags"]).most_common())
