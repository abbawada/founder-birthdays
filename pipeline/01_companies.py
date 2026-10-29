"""Phase 1a: candidate company universe.

Public: companiesmarketcap.com ranking (cached HTML pages) down to $20B.
Private: Crunchbase Unicorn Board rows at $20B+ (read 2026-10-28 board) plus
two multiples.vc extras, entered by hand with their source.
Output: data/candidates.json
"""
import html
import json
import os
import re

from common import CACHE, DATA, save_json

MCAP_DATE = "2026-10-29"
MCAP_URL = "https://companiesmarketcap.com/"
rows = []
for p in range(1, 14):
    path = os.path.join(CACHE, "mcap", f"p{p}.html")
    t = open(path).read()
    for m in re.finditer(r"<tr>(.*?)</tr>", t, re.S):
        r = m.group(1)
        name = re.search(r'class="company-name">([^<]+)<', r)
        if not name:
            continue
        code = re.search(r'class="company-code">(?:<span[^>]*></span>)?([^<]+)<', r)
        slug = re.search(r'<a href="/([^/]+)/marketcap/"', r)
        cap = re.search(r'<td class="td-right" data-sort="(\d+)"><span class="currency-symbol-left">\$</span>', r)
        country = re.search(r'<td>[^<]*<span class="responsive-hidden">([^<]+)</span>', r)
        rows.append({
            "name": html.unescape(name.group(1)).strip(),
            "ticker": code.group(1).strip() if code else "",
            "country": country.group(1).strip() if country else "",
            "value_usd": int(cap.group(1)) if cap else None,
            "value_kind": "market cap",
            "value_date": MCAP_DATE,
            "value_source": f"https://companiesmarketcap.com/{slug.group(1)}/marketcap/" if slug else MCAP_URL,
            "listing": "public",
        })
rows = [r for r in rows if r["value_usd"] and r["value_usd"] >= 20e9]

CB = "https://news.crunchbase.com/unicorn-company-list/"
CB_DATE = "2026-10-28"
MV = "https://multiples.vc/insights/50-most-valuable-private-companies-in-the-world"
MV_DATE = "2026-10-23"
private = [
    ("Anthropic", "United States", 965, CB), ("OpenAI", "United States", 852, CB), ("ByteDance", "China", 480, CB),
    ("Databricks", "United States", 190, CB), ("Stripe", "United States", 159, CB), ("Ant Group", "China", 150, CB),
    ("Waymo", "United States", 126, CB), ("Revolut", "United Kingdom", 115, CB), ("DeepSeek", "China", 91, CB),
    ("Ramp", "United States", 62, CB), ("Anduril Industries", "United States", 61, CB), ("Reliance Jio", "India", 58, CB),
    ("Moonshot AI", "China", 50, CB), ("Cognition", "United States", 48, CB), ("Prometheus", "United States", 41, CB),
    ("Checkout.com", "United Kingdom", 40, CB), ("Ripple", "United States", 40, CB), ("Figure", "United States", 39, CB),
    ("Axiom Solutions International", "United States", 38, CB), ("DayOne", "Singapore", 34, CB),
    ("Safe Superintelligence", "United States", 32, CB), ("Fanatics", "United States", 31, CB), ("Crusoe", "United States", 31, CB),
    ("VAST Data", "United States", 30, CB), ("Alibaba Bendi Shenghuo Fuwu Gongsi", "China", 30, CB), ("Scale AI", "United States", 29, CB),
    ("Devoted Health", "United States", 25, CB), ("OKX", "Seychelles", 25, CB), ("Reflection AI", "United States", 25, CB),
    ("Epic Games", "United States", 25, CB), ("Mistral AI", "France", 24, CB), ("FNZ", "United Kingdom", 24, CB),
    ("The Boring Company", "United States", 23, CB), ("Yangtze Memory Technologies", "China", 23, CB), ("Kalshi", "United States", 22, CB),
    ("ElevenLabs", "United States", 22, CB), ("BYJU'S", "India", 22, CB), ("Kraken Exchange", "United States", 21, CB),
    ("Etched", "United States", 21, CB), ("Envision Group", "China", 21, CB), ("JUUL", "United States", 21, CB),
    ("Crypto.com", "Singapore", 20, CB), ("Whatnot", "United States", 20, CB), ("Perplexity", "United States", 20, CB),
    ("Tether", "El Salvador", 500, MV), ("Blue Origin", "United States", 140, MV),
]
for name, country, bn, src in private:
    rows.append({
        "name": name, "ticker": "", "country": country, "value_usd": int(bn * 1e9),
        "value_kind": "last private valuation", "value_date": CB_DATE if src == CB else MV_DATE,
        "value_source": src, "listing": "private",
    })
save_json(os.path.join(DATA, "candidates.json"), rows)
print(len(rows), "candidates;", sum(r["listing"] == "public" for r in rows), "public,", sum(r["listing"] == "private" for r in rows), "private")
