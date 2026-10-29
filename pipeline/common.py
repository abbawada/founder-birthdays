"""Shared helpers: cached HTTP, Wikipedia and Wikidata access.

Every raw API response is cached under cache/ so reruns are reproducible
and never hit the network twice for the same request.
"""
import hashlib
import json
import os
import re
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
DATA = os.path.join(ROOT, "data")
UA = {"User-Agent": "founder-birthdays/0.2 (https://github.com/abbawada/founder-birthdays; research data story)"}
WP_API = "https://en.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"


def _key(prefix, payload):
    h = hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]
    return os.path.join(CACHE, prefix, h + ".json")


def get_json(prefix, url, params, sleep=0.1, headers=None):
    path = _key(prefix, {"url": url, "params": params})
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)["body"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    hdr = dict(UA)
    if headers:
        hdr.update(headers)
    r = None
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=hdr, timeout=120)
        except requests.RequestException as e:   # timeouts and dropped connections: wait and retry
            print(f"  retry {attempt + 1} after {type(e).__name__}: {url}")
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 200:
            body = r.json()
            with open(path, "w") as fh:
                json.dump({"url": url, "params": params, "fetched": time.strftime("%Y-%m-%d"), "body": body}, fh)
            time.sleep(sleep)
            return body
        if r.status_code == 429:
            time.sleep(10 * (attempt + 1))
        else:
            time.sleep(2)
    raise RuntimeError(f"GET failed {r.status_code if r is not None else 'no response'}: {url} {params}")


def wp_search(query, limit=6):
    body = get_json("wp", WP_API, {"action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json"})
    return body["query"]["search"]


def wp_page(title):
    """Wikitext, canonical title (after redirects) and Wikidata QID for an article."""
    body = get_json("wp", WP_API, {
        "action": "query", "prop": "revisions|pageprops", "rvprop": "content", "rvslots": "main",
        "ppprop": "wikibase_item", "titles": title, "redirects": 1, "format": "json"})
    pages = body["query"]["pages"]
    pg = next(iter(pages.values()))
    if "missing" in pg:
        return None
    text = pg.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
    return {"title": pg.get("title"), "qid": pg.get("pageprops", {}).get("wikibase_item"), "text": text,
            "url": "https://en.wikipedia.org/wiki/" + pg.get("title", "").replace(" ", "_")}


def infobox(text):
    """Return (infobox name, {field: raw value}) for the first infobox in the wikitext."""
    m = re.search(r"\{\{\s*Infobox[ _]([^\n|]+)", text)
    if not m:
        return None, {}
    i = m.start()
    depth = 0
    j = i
    while j < len(text):
        if text.startswith("{{", j):
            depth += 1
            j += 2
            continue
        if text.startswith("}}", j):
            depth -= 1
            j += 2
            if depth == 0:
                break
            continue
        j += 1
    box = text[i:j]
    fields = {}
    # split on top-level pipes only
    depth = 0
    cur = []
    parts = []
    k = 0
    while k < len(box):
        if box.startswith("{{", k) or box.startswith("[[", k):
            depth += 1
            cur.append(box[k:k + 2])
            k += 2
            continue
        if box.startswith("}}", k) or box.startswith("]]", k):
            depth -= 1
            cur.append(box[k:k + 2])
            k += 2
            continue
        if box[k] == "|" and depth == 1:
            parts.append("".join(cur))
            cur = []
            k += 1
            continue
        cur.append(box[k])
        k += 1
    parts.append("".join(cur))
    for p in parts[1:]:
        if "=" in p:
            name, val = p.split("=", 1)
            fields[name.strip().lower()] = val.strip()
    return m.group(1).strip().lower(), fields


def strip_markup(v):
    v = re.sub(r"<ref[^>]*/>", "", v)
    v = re.sub(r"<ref.*?</ref>", "", v, flags=re.S)
    v = re.sub(r"<!--.*?-->", "", v, flags=re.S)
    v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", v)
    v = re.sub(r"\{\{(?:nowrap|small|smaller|nobold|abbr)\|([^}|]*)[^}]*\}\}", r"\1", v, flags=re.I)
    v = re.sub(r"<[^>]+>", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def names_from_field(v):
    """Person names (wikilink targets when present) from an infobox founders field."""
    if not v:
        return []
    v = re.sub(r"<ref[^>]*/>", "", v)
    v = re.sub(r"<ref.*?</ref>", "", v, flags=re.S)
    v = re.sub(r"<!--.*?-->", "", v, flags=re.S)
    links = re.findall(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]", v)
    if links:
        return [l.strip() for l in links if not l.lower().startswith(("file:", "image:"))]
    v = re.sub(r"\{\{(?:ubl|unbulleted list|hlist|plainlist|flatlist|collapsible list|cslist|bulleted list)\s*\|", "\n", v, flags=re.I)
    v = re.sub(r"\{\{[^}]*\}\}", "", v)
    v = re.sub(r"<br\s*/?>", "\n", v, flags=re.I)
    v = re.sub(r"<[^>]+>", "\n", v)
    parts = re.split(r"\n|\*|,|;|\band\b|&", v)
    out = []
    for p in parts:
        p = p.strip(" *|}{")
        p = re.sub(r"\(.*?\)", "", p).strip()
        if 3 <= len(p) <= 40 and re.search(r"[A-Za-z]", p):
            out.append(p)
    return out


def sparql(query):
    body = get_json("wd", SPARQL, {"query": query}, sleep=0.5, headers={"Accept": "application/sparql-results+json"})
    return body["results"]["bindings"]


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def load_json(path, default=None):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
