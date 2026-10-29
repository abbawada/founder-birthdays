"""Company type for every company, from the 'industry' field of its English
Wikipedia infobox (Wikidata P452 when the infobox has none), mapped by keyword
to six plain groups. A handful of one-word or 'conglomerate' entries are set by
hand below, each with the reason. Output: data/sectors.json
{company: {"sector": ..., "industry_text": ..., "source": url}}.
Exploratory: this question was asked after pre-registration.
"""
import os
import re

from common import DATA, load_json, save_json, wp_page, infobox, strip_markup, sparql

SECTORS = ["Software & internet", "Chips & hardware", "Money & finance", "Health & biotech", "Shops & consumer brands", "Energy, cars & industry"]
RULES = [  # first rule whose keyword appears in the FIRST listed industry wins; then the whole field is tried
    ("Health & biotech", r"pharma|biotech|health|medic|drug|life science|diagnos|biopharm|therapeut|genom|hospital|genetic"),
    ("Money & finance", r"financ|bank|invest|insur|payment|fintech|crypto|asset manag|venture|brokerage|private equity|holding|lending|credit|stock exchange|trading|prediction market|betting"),
    ("Chips & hardware", r"semiconductor|hardware|electronic|storage|networking|telecommunications equipment|telecoms equip|personal computer|battery|chip|robot|consumer electronics|printer|display|gpu|electrical|appliance|test & automation|photovoltaic"),
    ("Software & internet", r"software|internet|information technology|cloud|cyber|security|social|video game|artificial intelligence|\bai\b|e-commerce|search|saas|online|web|mobile app|ride|delivery|streaming|data|platform|technology|video conference|b2b it|self-driving|scooter"),
    ("Shops & consumer brands", r"retail|apparel|clothing|fashion|food|beverage|restaurant|coffee|cosmetic|consumer goods|hospitality|hotel|travel|furniture|toy|footwear|luxury|grocery|supermarket|beauty|lodging|wholesale|sports equipment|lifestyle"),
    ("Energy, cars & industry", r"energy|oil|gas|automotive|vehicle|transport|logistic|aerospace|space|real estate|construction|industrial|manufactur|mining|steel|chemical|utilit|telecom|media|entertainment|airline|shipping|engineering|conglomerate|professional services|staffing|agricult|education|petroleum|waste|rental|apartment|infrastructure|property|outsourcing|human capital|weapon|defense|port operator|heavy equipment|motorsport|advertising|glass|wind|farming"),
]
HAND = {  # company -> (sector, why)
    "Apple": ("Chips & hardware", "infobox says only 'Technology'; Apple's revenue is mostly iPhone and Mac hardware"),
    "Amazon": ("Software & internet", "infobox says 'Conglomerate'; Amazon began and is best known as an online store and cloud provider"),
    "Tencent": ("Software & internet", "infobox lists video games first; Tencent is WeChat, games and online services"),
    "SoftBank Group Corp.": ("Money & finance", "holding company and venture capital investor"),
    "SpaceX": ("Energy, cars & industry", "rockets and satellites"),
    "Tesla": ("Energy, cars & industry", "cars and batteries"),
    "JUUL": ("Shops & consumer brands", "infobox says 'Electronic cigarettes'; a consumer product, not computer hardware"),
    "Twilio": ("Software & internet", "infobox says 'Communications'; Twilio sells cloud software for texts and calls"),
    "Titan Company": ("Shops & consumer brands", "infobox says 'Lifestyle'; Titan sells watches and jewellery"),
    "Fastenal": ("Energy, cars & industry", "no industry field; distributes industrial and construction supplies"),
    "BeOne Medicines": ("Health & biotech", "no industry field; cancer-drug maker, formerly BeiGene"),
    "Adani Enterprises": ("Energy, cars & industry", "no industry field; flagship of an energy, mining and infrastructure group"),
    "Eternal (Zomato)": ("Software & internet", "no industry field; food-delivery app"),
    "DexCom": ("Health & biotech", "no industry field; glucose-monitor maker"),
    "Ryanair": ("Energy, cars & industry", "no industry field; airline"),
    "J. B. Hunt": ("Energy, cars & industry", "no industry field; trucking and logistics"),
    "Circle Internet Group": ("Money & finance", "no industry field; issuer of the USDC stablecoin"),
    "Checkout.com": ("Money & finance", "no industry field; payments processor"),
    "Blockbuster": ("Shops & consumer brands", "no industry field; video-rental store chain"),
    "Byju's": ("Software & internet", "no industry field; online-learning app"),
    "Excite@Home (At Home Corporation)": ("Software & internet", "no industry field; internet portal and cable internet provider"),
    "New Century Financial": ("Money & finance", "no industry field; mortgage lender"),
    "Powa Technologies": ("Money & finance", "no industry field; mobile-payments company"),
}


def classify(text):
    if not text:
        return None
    parts = [p.strip() for p in re.split(r"\||\*|,|;|\n|  +", text) if p.strip() and not p.strip().lower().startswith(("ublist", "ubl", "unbulleted", "hlist", "plainlist", "flatlist", "ubil"))]
    for chunk in parts[:1] + [text]:
        low = chunk.lower()
        for sector, rx in RULES:
            if re.search(rx, low):
                return sector
    return None


companies = load_json(os.path.join(DATA, "companies.json"))
out, missing = {}, []
for c in companies:
    name = c["name"]
    raw, url = "", c.get("article_url")
    pg = wp_page(c["article"]) if c.get("article") else None
    if pg:
        _, f = infobox(pg["text"])
        raw = strip_markup(f.get("industry", "") or "")
        url = pg["url"]
    if not raw and c.get("qid"):
        res = sparql(f"SELECT ?iLabel WHERE {{ wd:{c['qid']} wdt:P452 ?i . SERVICE wikibase:label {{ bd:serviceParam wikibase:language \"en\". }} }}")
        raw = ", ".join(b["iLabel"]["value"] for b in res)
        url = f"https://www.wikidata.org/wiki/{c['qid']}"
    if name in HAND:
        sector, why = HAND[name]
        out[name] = {"sector": sector, "industry_text": raw[:160], "source": url, "set_by_hand": why}
        continue
    sector = classify(raw)
    if sector:
        out[name] = {"sector": sector, "industry_text": raw[:160], "source": url}
    else:
        missing.append((name, raw[:80]))
save_json(os.path.join(DATA, "sectors.json"), out)
from collections import Counter
print(len(out), "companies typed;", len(missing), "untyped")
print(Counter(v["sector"] for v in out.values()))
for m in missing:
    print("  untyped:", m)
