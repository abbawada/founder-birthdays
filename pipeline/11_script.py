"""Narration for the demo video, generated from data/stats.json so every number
said matches the page. Writes VIDEO_SCRIPT.md. Each block is one chapter of
Play the story, with the seconds that chapter stays on screen.
"""
import os

from common import DATA, ROOT, load_json

S = load_json(os.path.join(DATA, "stats.json"))
T = S["tests"]
founders = load_json(os.path.join(DATA, "founders.json"))
sg, el, pr, pm, ra, fv, bk, se, mo = (T[k] for k in ("signs", "elements", "pairs", "pair_matrix", "relative_age", "fallen_vs_thriving", "breakups", "sectors", "moon"))
bw = bk.get("with_ousters", bk)
pct = lambda p: f"{100*p:.0f}%"
n_dated = sum(1 for f in founders if f.get("birthday"))
i = sg["bins"].index(sg["tallest"])
comp = next(m for m in pr["measures"] if m["name"] == "traditionally compatible")
ELW = {"Fire": "fire signs", "Earth": "earth signs", "Air": "air signs", "Water": "water signs"}
ie = el["bins"].index(el["tallest"])
musk = [p for p in pm["pairs"] if p["split"] and "Elon Musk" in (p["a"], p["b"])]

blocks = [
    ("Open", 0, "My birthday is the day after Steve Jobs. So I asked a silly question and did it properly: **do the stars pick founders?**"),
    ("I. Every founder, on their birthday", 10, f"Every dot is a founder of one of the world's most valuable companies, on the day they were born. {n_dated} of them. The bars count founders per sign, and **the gold tick is what luck alone would give.**"),
    ("II. Libra leads. That's luck.", 13, f"{sg['tallest']} has the most: {sg['observed'][i]} founders, where luck gives {sg['expected'][i]:.0f}. Looks like a signal. **Now watch random birthdays.** Every shuffle crowns a new winner. A lead like {sg['tallest']}'s shows up {pct(sg['p_max_dev'])} of the time by luck."),
    ("III. Fire, earth, air, water", 9, f"Grouped into elements, {ELW[el['tallest']]} lead with {el['observed'][ie]} against {el['expected'][ie]:.0f}. **Random birthdays do that well half the time.**"),
    ("IV. Who should you start a company with?", 15, f"This is the one people actually ask. Astrology says fire gets on with air, earth with water. **{pct(comp['observed'])} of real cofounder pairs are a match. Random teams: {pct(comp['null_mean'])}.** Jobs and Wozniak? Not a match. Gates and Allen? Not a match, and they fell out."),
    ("V. The match chart", 16, "Find your sign, read across. Every square is a pair of signs. **Click one and you meet the cofounders.** Pisces and Leo: Jobs and Wozniak. Switch to compared with luck and the gold squares are combos that show up more than random teams would make. Small numbers, great stories."),
    ("VI. Your sign's cofounders", 11, "Pick your sign. **If you're a Sagittarius, here are the founders like you, and who they built with.**"),
    ("VII. Do mismatched signs split up?", 11, f"{bw['n_broke']} cofounder pairs in the list split. **{pct(bw['compatible_broke'])} of them were a match, against {pct(bw['compatible_intact'])} of pairs that stayed.** If anything, matches split more. Elon Musk, a Cancer, is in {len(musk)} of those splits."),
    ("VIII. Does failure have a sign?", 9, f"Red: {fv['n_fallen']} founders whose billion-dollar companies collapsed. **Their signs look like everyone else's.**"),
    ("IX. The one birthday effect science takes seriously", 12, f"In sports, the oldest kids in class get picked first. Does that make founders? **Oldest third of the class: {pct(ra['share_oldest_third'])}. Luck: {pct(ra['null_oldest_third'])}.** So, when should you have your kid? Whenever you like."),
    ("X. Do signs pick industries?", 9, f"Colored by industry. **No sign owns one.** The strongest lean is luck {pct(se['p_max_cell'])} of the time."),
    ("XI. The Moon and rising signs", 8, f"Moon signs: no pattern. Rising signs need a birth time, and only a handful of founders have one on record."),
    ("XII. Where do you land?", 12, "Now you. **Type your birthday, make your card, and post your sign.** Mine says Pisces, a day after Steve Jobs. The stars don't pick founders. Luck does."),
]
out = ["# Founders by Birthday: video script", "",
       "## Post", "", "**Title:** Helping you decide when to have your kid", "",
       "**Post text:** I put 338 founders of the world's biggest companies on the day they were born and tested every astrology claim against luck. Signs, cofounder matches, breakups, even school birthdays. Find your sign:", "",
       "Record the page with Play the story running (about 2 minutes 15 seconds). Read each block while its chapter is on screen; bold is the beat to land as the circle moves.", ""]
total = 0
for title, secs, text in blocks:
    total += secs
    out += [f"## {title}" + (f" · {secs} s" if secs else ""), "", text, ""]
out.append(f"Total about {total // 60} min {total % 60} s.")
open(os.path.join(ROOT, "VIDEO_SCRIPT.md"), "w").write("\n".join(out) + "\n")
print("VIDEO_SCRIPT.md written,", total, "seconds")
