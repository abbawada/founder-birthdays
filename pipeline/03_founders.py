"""Phase 2a: founder roster. Union of Wikipedia infobox founders (resolved to
Wikidata items through their articles) and Wikidata P112 founders.

Output: data/founders_raw.json, one row per (company, founder).
"""
import os
import re
import sys
from urllib.parse import unquote

from common import DATA, ROOT, load_json, save_json, wp_page, wp_search, sparql, chunks

companies = load_json(os.path.join(DATA, "companies.json"))
overrides = load_json(os.path.join(ROOT, "pipeline", "overrides.json"), {})
links = load_json(os.path.join(ROOT, "pipeline", "founder_links.json"), {})   # {company: {founder name: QID}} hand-checked links that the mention test would reject
rows = []
unlinked = []
for c in companies:
    if not c.get("founded_year") or c["founded_year"] < 1960:
        continue
    seen = set()
    base = re.sub(r"\s*\(.*?\)", "", c["name"]).strip().lower()
    art = unquote(c.get("article") or "").lower()
    forced = links.get(c["name"], {})
    toks = [w for w in re.findall(r"[a-z0-9]+", art or base) if len(w) >= 4 or w.isupper()] or [base]
    STOP = {"inc", "corp", "corporation", "group", "holdings", "holding", "company", "limited", "technologies", "technology", "international", "industries", "global"}
    toks = [w for w in toks if w not in STOP] or [base]
    def mentions(pg):
        """A same-named article counts only if it mentions the company (Joe Parkinson the footballer is not Micron's founder)."""
        if not pg:
            return False
        low = pg["text"].lower()
        return base in low or (art and art in low) or any(w in low for w in toks[:2])
    for name in c.get("founders_wp", []):
        pg = wp_page(name)
        if pg and pg["qid"] and not mentions(pg) and forced.get(name) != pg["qid"]:
            pg = None
        qid = pg["qid"] if pg else None
        title = pg["title"] if pg else None
        if not qid:
            # plain-text name: accept a search hit only when the title is the name
            hits = wp_search(name, 3)
            for h in hits:
                if re.sub(r"\s*\(.*?\)", "", h["title"]).lower() == name.lower():
                    pg = wp_page(h["title"])
                    if pg and pg["qid"] and mentions(pg):
                        qid, title = pg["qid"], pg["title"]
                    break
        if not qid:
            unlinked.append((c["name"], name))
            rows.append({"company": c["name"], "company_qid": c.get("qid"), "founder_qid": None, "founder_name": name,
                         "wp_title": None, "source": "wikipedia infobox (no article)"})
            continue
        if qid in seen:
            continue
        seen.add(qid)
        rows.append({"company": c["name"], "company_qid": c.get("qid"), "founder_qid": qid, "founder_name": name,
                     "wp_title": title, "source": "wikipedia infobox"})
    for qid, label in (c.get("founders_wd") or {}).items():
        if qid in seen:
            continue
        seen.add(qid)
        rows.append({"company": c["name"], "company_qid": c.get("qid"), "founder_qid": qid, "founder_name": label,
                     "wp_title": None, "source": "wikidata P112"})

# dedupe within a company: the same person can arrive as a plain name and as a Wikidata item
def _norm(s):
    return re.sub(r"[^a-z]", "", s.lower().replace("ø", "o").replace("é", "e").replace("ü", "u"))
deduped, seen_pairs = [], {}
for r in rows:
    k = (r["company"], _norm(r["founder_name"]))
    if k in seen_pairs:
        prev = seen_pairs[k]
        if not prev["founder_qid"] and r["founder_qid"]:
            deduped[deduped.index(prev)] = r
            seen_pairs[k] = r
        continue
    seen_pairs[k] = r
    deduped.append(r)
rows = deduped

# keep only humans among linked items; drop organisations that slipped into the founders field
qids = sorted({r["founder_qid"] for r in rows if r["founder_qid"]})
human = set()
for chunk in chunks(qids, 150):
    vals = " ".join("wd:" + q for q in chunk)
    for b in sparql(f"SELECT ?p WHERE {{ VALUES ?p {{ {vals} }} ?p wdt:P31 wd:Q5 . }}"):
        human.add(b["p"]["value"].split("/")[-1])
kept = [r for r in rows if (r["founder_qid"] in human) or r["founder_qid"] is None]
dropped = [r for r in rows if r["founder_qid"] and r["founder_qid"] not in human]
save_json(os.path.join(DATA, "founders_raw.json"), kept)
save_json(os.path.join(DATA, "founders_dropped_nonhuman.json"), dropped)
print(len(kept), "founder rows across", len({r['company'] for r in kept}), "companies;", len(unlinked), "unlinked names;", len(dropped), "non-human items dropped")
