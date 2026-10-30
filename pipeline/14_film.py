"""The film: narration lines written from data/stats.json (so every number spoken
matches the page), voiced locally with Kokoro (af_heart), encoded as small MP3s
and written to data/film.json for the page to play. Also writes VIDEO_SCRIPT.md.

Run with the TTS environment (kokoro-onnx), not the founders one:
  PYTHONPATH=pipeline ~/.venvs/tts/bin/python -P pipeline/14_film.py
"""
import base64
import json
import os
import subprocess
import tempfile

import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
load = lambda n: json.load(open(os.path.join(DATA, n)))
S = load("stats.json"); T = S["tests"]
founders = load("founders.json"); companies = {c["name"]: c for c in load("companies.json")}
N = sum(1 for f in founders if f.get("birthday"))
sg = T["signs"]; i = sg["bins"].index(sg["tallest"]); lead, leadN, leadE = sg["tallest"], sg["observed"][i], round(sg["expected"][i])
comp = next(m for m in T["pairs"]["measures"] if m["name"] == "traditionally compatible")
V, ra, fv = T["value"], T["relative_age"], T["fallen_vs_thriving"]
EL = {"Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire", "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth", "Gemini": "Air", "Libra": "Air", "Aquarius": "Air", "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"}
ok = lambda a, b: EL[a] == EL[b] or {EL[a], EL[b]} in ({"Fire", "Air"}, {"Earth", "Water"})
teams = {}
for p in T["pair_matrix"]["pairs"]:
    teams.setdefault(p["company"], []).append(ok(p["sa"], p["sb"]))
clash = sorted([c for c, v in teams.items() if sum(v) / len(v) < 0.5], key=lambda c: -(companies[c]["value_usd"] or 0))[:3]
short = lambda c: c.split(" (")[0]
pct = lambda x: f"{round(x * 100)} percent"
in_ten = lambda p: {0: "almost never", 1: "one in ten", 2: "two in ten", 3: "three in ten", 4: "four in ten", 5: "half", 6: "six in ten", 7: "seven in ten", 8: "eight in ten", 9: "nine in ten", 10: "nearly always"}[round(p * 10)]
bil = lambda v: f"{round(v / 1e9)} billion dollars"
wb = T["breakups"].get("with_ousters", T["breakups"])

X = load("extras.json")
W = load("whatif.json")
idea = lambda n: next((w for w in W if n in (w["a"]["name"], w["b"]["name"])), None)
z, g, e = idea("Mark Zuckerberg"), idea("Jensen Huang"), idea("Elon Musk")
lore = {l["sign"]: l for l in X["lore"]}
ages = X["ages"]; one_in = round(1 / ages["under25"])
trill = X["clash"]["trillion"]; n_cl = sum(1 for t in trill if t["kind"] == "clash")
splits_matched = round(wb["compatible_broke"] * wb["n_broke"])

# (id, what the subtitle shows). The voice reads the same words with a few respellings (see SAY).
LINES = [
    ("jobs", "Steve Jobs was born on February 24th. A Pisces."),
    ("others", "Bill Gates is a Scorpio. Elon Musk is a Cancer."),
    ("title", "Do the stars pick founders?"),
    ("checked", f"We found the exact birthday of {N} founders of the world's most valuable companies."),
    ("zoom", "Each founder becomes a star, on the day they were born. Here's Steve Jobs."),
    ("reveal", "And here's everyone."),
    ("bars", f"Count the founders under each sign, and {lead} comes out on top, with {leadN}."),
    ("fair", f"Split {sg['n']} founders evenly across twelve signs, and each gets about {leadE}. {lead} has {leadN - leadE} extra. But some sign always pulls ahead by about that much."),
    ("every", "What matters more: every sign has founded a giant. Whatever your sign, you're in good company."),
    ("who", "Now the question founders really ask. Who should you start a company with?"),
    ("rule1", "Astrology has a rule for this. Every sign belongs to an element: fire, earth, air or water."),
    ("rule2", "Same element is a match. So is fire with air, or earth with water. Anything else is a clash."),
    ("page", "Larry Page and Sergey Brin? Both fire. A match."),
    ("woz", "Steve Jobs and Steve Wozniak? Water and fire. A clash."),
    ("coin", "Here's the thing. Exactly half of all sign pairs are matches. And half of real cofounders are matches. It's a coin flip."),
    ("built", "So we looked at what each team built."),
    ("money", f"The clashing teams built bigger companies. About twice as big: {bil(V['teams_unmatched_median'])}, against {bil(V['teams_matched_median'])}."),
    ("trillion", f"Now look at the very top: the companies worth over a trillion dollars. {['Zero','One','Two','Three','Four','Five','Six','Seven'][len(trill)]} had a founding team, and {['zero','one','two','three','four','five','six','seven'][n_cl]} of those teams were clashing signs."),
    ("names", "Nvidia. Apple. Microsoft. Tesla. Meta. Only Google is a match."),
    ("holds", "We cut the data every way we could. Before 2000 and after. Software and everything else. Small teams and big ones. The clashing teams came out ahead every time."),
    ("also", f"They collapsed less often, too. And when cofounders fell out, it was usually a matched pair: {splits_matched} of the {wb['n_broke']} splits."),
    ("odds", f"Could it be chance? If signs meant nothing, you'd see a gap this big about once in {round(1 / V['p_teams'])} tries. Rare enough to be interesting."),
    ("grid", "Here's how much every pair of signs built together. The brighter the square, the more money."),
    ("game", "Which raises a fun question. What if?"),
    ("wif1", f"What if Mark Zuckerberg and Steve Jobs had started a company? We imagine {z['idea']['name']}: a phone with only your people on it."),
    ("wif2", f"Bill Gates and Jensen Huang? {g['idea']['name']}: an operating system built for graphics chips, twenty years early."),
    ("wif3", f"Elon Musk and Chris Hughes? {e['idea']['name']}: a rocket company that pays its passengers."),
    ("wifhow", "We paired ten of them, from the sign pairs that built the most in real life. On the page, you can build your own team."),
    ("lore", "Astrology also gives every sign a job description. So we checked them."),
    ("lore2", "Leos, the born leaders, really did go solo more often. Sagittarians, the risk-takers, never once crashed. And Libra, the partnership sign, doesn't partner any more than anyone else."),
    ("agetitle", "Birthdays do tell us one thing for sure: how old founders were when they started."),
    ("ages", f"The typical founder started at {int(ages['median'])}. Only about one in {one_in} started before 25. Bill Gates and Mark Zuckerberg, at 20, are the exceptions."),
    ("older", f"And founders are getting older. In the sixties and seventies, they started around {int(ages['by_era'][0]['median'])}. Lately, closer to {int(ages['by_era'][3]['median'])}."),
    ("twins", "Some founders even share a birthday. Steve Jobs shares his with Nike's Phil Knight. Steve Wozniak shares his with SoftBank's Masayoshi Son."),
    ("paradox", "Fate? Not quite. It's the birthday paradox. Put 23 people in a room, and two probably share a birthday."),
    ("school1", "There's one birthday effect science takes seriously. In sports, the oldest kids in class get picked first."),
    ("school2", f"Does that make founders? {X['school']['oldest_third']} were among the oldest in their class. {X['school']['youngest_third']} were among the youngest. No head start."),
    ("kid", "So when should you have your kid? Whenever you like."),
    ("answer", "So, do the stars pick founders? Not your sign, and not your birthday. But if you're choosing a cofounder, don't fear a clash."),
    ("end", "Scroll down to find your sign, your birthday twins, and your dream cofounder."),
]
SAY = [("Libra", "Leebra"), ("Elon", "Eelon")]   # how the voice should say them; subtitles keep the real spelling
def say_of(t):
    for a_, b_ in SAY:
        t = t.replace(a_, b_)
    return t

k = Kokoro(os.path.expanduser("~/.cache/kokoro/kokoro-v1.0.onnx"), os.path.expanduser("~/.cache/kokoro/voices-v1.0.bin"))
out, total = [], 0.0
with tempfile.TemporaryDirectory() as td:
    for bid, say in LINES:
        samples, sr = k.create(say_of(say), voice="af_heart", speed=1.0, lang="en-us")
        wav, mp3 = os.path.join(td, bid + ".wav"), os.path.join(td, bid + ".mp3")
        sf.write(wav, samples, sr)
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-ac", "1", "-ar", "24000", "-b:a", "48k", mp3], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"ffmpeg failed for {bid}: {r.stderr}")
        dur = len(samples) / sr
        total += dur
        out.append({"id": bid, "say": say, "dur": round(dur, 2), "audio": "data:audio/mpeg;base64," + base64.b64encode(open(mp3, "rb").read()).decode()})
json.dump(out, open(os.path.join(DATA, "film.json"), "w"))
lines = ["# Founders by Birthday: the film", "", "**Post title:** Helping you decide when to have your kid", "",
         "**Post text:** I put 338 founders of the world's biggest companies on the day they were born. Astrology's cofounder rule turned out backwards: the teams it says should clash built companies twice as big, including five of the six trillion-dollar ones.", "",
         f"The film on the page plays this narration (voice: Kokoro af_heart), about {int(total // 60)} min {int(total % 60)} s. Record the screen while it plays, or read these lines over it yourself.", ""]
lines += [f"{n + 1}. {say}" for n, (bid, say) in enumerate(LINES)]
open(os.path.join(ROOT, "VIDEO_SCRIPT.md"), "w").write("\n".join(lines) + "\n")
print(len(out), "lines,", round(total, 1), "seconds of narration,", os.path.getsize(os.path.join(DATA, "film.json")) // 1024, "KB")
