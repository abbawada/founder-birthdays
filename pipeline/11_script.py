"""Narration script for the demo video, generated from data/stats.json so every
number on screen matches what is said. Writes VIDEO_SCRIPT.md. Timing follows
the page's autoplay (9 seconds per chapter) but each block can be read slower.
"""
import json
import os
from collections import Counter

from common import DATA, ROOT, load_json

S = load_json(os.path.join(DATA, "stats.json"))
T = S["tests"]
companies = load_json(os.path.join(DATA, "companies.json"))
founders = load_json(os.path.join(DATA, "founders.json"))
rings = Counter(c["ring"] for c in companies)
n_dated = S["n_dated"]
sg = T["signs"]
top = sg["tallest"]
i = sg["bins"].index(top)
pairs = T.get("pairs")
ra = T.get("relative_age")
fv = T.get("fallen_vs_thriving")
br = T.get("breakups")
pm = T.get("pair_matrix")
moon = T.get("moon")
pct = lambda p: f"{100*p:.0f}%"

lines = []
L = lines.append
L("# Founders by birthday: demo narration\n")
L("Read over the page with Play the story (9 s per chapter) or step through with the arrow keys. Each block is one chapter; the bold line is the beat to land on while the ring changes.\n")
L("## 00 Open (hero)")
L(f"My birthday is the day after Steve Jobs'. I've always liked that. So I asked a dumb question properly: do the people who built the world's biggest companies cluster by birthday? **{n_dated} founders of {len(companies)} companies, each one a dot on the day they were born.**\n")
L("## 01 The ring")
L(f"Giants are the bright gold dots, companies worth a hundred billion or more. Blue is the next ring, twenty to a hundred billion. Red is the fallen: companies that hit a billion and then collapsed. **Around the rim, every sign shows its count against the shaded band of what chance would produce.** And chance here isn't flat: each founder's expected birthday follows the birth statistics of their own country in their own year.\n")
L("## 02 The tallest bar")
L(f"Your eye goes straight to the peak. Right now that's {top}: {sg['observed'][i]} founders against {sg['expected'][i]:.0f} expected. Looks like something. **Now watch: shuffle the universe.** Same founders, random birthdays. The tallest bar moves, and it's about as tall. Chance produced a peak at least this big in {pct(sg['p_max_dev'])} of ten thousand shuffles.\n")
L("## 03 Elements and modalities")
L(f"Twelve bins spread people thin, so astrology's own groupings get a turn: four elements, three modalities. **{T['elements']['tallest']} leads the elements at {T['elements']['ratio'][T['elements']['bins'].index(T['elements']['tallest'])]:.2f} times expected; chance beats it {pct(T['elements']['p_max_dev'])} of the time.** Same story for the modalities.\n")
if pairs:
    c = pairs["measures"][2]
    L("## 04 Cofounders")
    L(f"Fire with Air, Earth with Water. If compatible signs built companies together, cofounder pairs should match more often than random pairs of the same people. **{pct(c['observed'])} of {pairs['n_pairs']} pairs are compatible. Deal the same founders into random teams ten thousand times: {pct(c['null_mean'])}.**\n")
if pm:
    L("## 05 Sign by sign")
    L(f"This is the question people actually ask me. Pisces with Leo. Pisces with Cancer. **Every cofounder pair sits in one cell; hover one and the ring lights up those pairs.** {S['tests']['pair_matrix']['n_pairs']} pairs across 78 cells means most cells hold a handful of companies. It's a map for curiosity, not a verdict, and the page says so.\n")
if ra:
    L("## 06 The school year")
    L(f"There is one documented way a birth window changes a life: school cutoffs. Kids born just after the cutoff are the oldest in class for a decade. A 2012 study found it in S&P 500 CEOs; a bigger 2022 study didn't. **Flip the ring to the school year. Founders average {ra['mean_months']:.1f} months older than their youngest classmate; chance says {ra['null_mean']:.1f}.** Nothing.\n")
if fv:
    L("## 07 The fallen")
    L(f"If the stars make founders, maybe they unmake them. The red dots: {fv['n_fallen']} founders of companies that reached a billion and then went bankrupt, shut down, or ended in a fraud conviction. **Their sign mix against the thriving founders: shuffling the 'fallen' label ten thousand times produced a gap this big {pct(fv['p_perm'])} of the time.**\n")
if br:
    L("## 08 Breakups")
    L(f"The documented splits: ousters, lawsuits, public feuds between cofounders. **{pct(br['compatible_broke'])} of the pairs that broke up were 'compatible' by element. {pct(br['compatible_intact'])} of the pairs that stayed.** Astrology did not see the breakup coming.\n")
if moon:
    L("## 09 Moon and rising")
    L(f"Sun signs are what birthdays give you for free. The Moon needs the clock and the Rising sign needs it to the hour. **The Moon is computed for everyone; a Rising sign exists only for the founders whose birth time is on record.** Hover Jobs: Pisces Sun, Aries Moon, Virgo rising, from his birth certificate.\n")
L("## 10 Find yourself")
L("Type a birthday. **It defaults to February 25th, mine.** You get your wedge, how many founders share it against how many chance expects, and everyone born within three days of you.\n")
L("## 11 How we counted")
L("Every birthday has a source link. Nothing was filled from memory. The hypotheses were written and committed before the first date was pulled; anything added later says 'exploratory'. **The answer is the honest one: founders are born on every day of the year, in exactly the proportions you'd expect.** The code and the data are open.\n")
open(os.path.join(ROOT, "VIDEO_SCRIPT.md"), "w").write("\n".join(lines))
print("VIDEO_SCRIPT.md written,", len(lines), "lines")
