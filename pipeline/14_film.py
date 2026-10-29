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

# id, spoken line. The page decides what each id shows.
LINES = [
    ("jobs", "Steve Jobs was born on February 24th. That makes him a Pisces."),
    ("others", "Bill Gates is a Scorpio. Elon Musk, a Cancer."),
    ("ask", "So here's a question people actually ask."),
    ("title", "Do the stars pick founders?"),
    ("apple", "Could your sign, or your cofounder's, decide whether you build the next Apple?"),
    ("checked", "So we checked."),
    ("count", f"We found the founders of the world's most valuable companies, and the exact day each one was born. {N} of them."),
    ("zoom", "Every founder becomes a star, placed on their birthday. Here's Steve Jobs, on February 24th."),
    ("reveal", "Do that for everyone, and you get this."),
    ("colors", "Gold stars built companies worth over a hundred billion dollars. Red ones built companies that later collapsed."),
    ("bars", "Now count the founders under each sign."),
    ("lead", f"{lead} comes out on top, with {leadN}."),
    ("marks", "But how many would you expect? Birth records tell us how many people are born under each sign, in each country, each year."),
    ("norm", f"If founders were born like everyone else, {lead} would have about {leadE}."),
    ("special", f"So, {leadN - leadE} extra. Is that special?"),
    ("crowd", "Here's the catch. Every crowd has a top sign. This is a random crowd of ordinary people who never founded anything."),
    ("crowd2", "A different sign wins. Another crowd, another winner."),
    ("tenk", f"We built ten thousand crowds like this. {in_ten(sg['p_max_dev']).capitalize()} of them had a sign that stood out as much as {lead} does."),
    ("ordinary", f"So {lead}'s lead is ordinary. Fire, earth, air and water come out even too."),
    ("pivot", "Now for the question founders really ask."),
    ("who", "Who should you start a company with?"),
    ("rule1", "Astrology has a rule for this. Every sign belongs to an element: fire, earth, air or water."),
    ("rule2", "Two signs are a match if they share an element, or if one is fire and the other air, or one is earth and the other water. Anything else is a clash."),
    ("page", "Larry Page is an Aries. Sergey Brin, a Leo. Both fire. A match."),
    ("woz", "Steve Jobs is a Pisces. Steve Wozniak, a Leo. Water and fire. A clash."),
    ("test", f"So are real cofounders matched more often? We broke up all {T['pairs']['n_teams']} founding teams, and paired the founders at random."),
    ("fifty", f"Real teams: {pct(comp['observed'])} matched. Random pairs: {pct(comp['null_mean'])}. No difference at all."),
    ("care", "Then we asked what a founder actually cares about. Did matched teams build bigger companies?"),
    ("backwards", "They didn't. Teams astrology says should clash built companies worth about twice as much."),
    ("money", f"{bil(V['teams_unmatched_median']).capitalize()} for a typical clashing team. {bil(V['teams_matched_median'])} for a matched one."),
    ("examples", f"{short(clash[0])}, {short(clash[1])} and {short(clash[2])} were all founded by clashing signs."),
    ("caveat", f"Is it real? Probably not. Without any real effect, a gap this big still shows up about one time in {round(1 / V['p_teams'])}. We asked about fifteen questions, so one surprise like this is normal."),
    ("closest", "But it's the closest thing to a pattern we found."),
    ("grid", "Here's every pairing at once. Each square is two signs. The brighter the square, the more those cofounders built."),
    ("game", "Which makes for a fun game."),
    ("wif1", "What if Mark Zuckerberg had started a company with Steve Jobs?"),
    ("wif2", "Or Bill Gates with Jensen Huang?"),
    ("wif3", "Sam Altman with Paul Allen?"),
    ("wifhow", "We paired ten of them, using the sign pairs whose real cofounders built the most."),
    ("splits", "Do clashing signs split up? Gates and Allen fell out. So did Zuckerberg and Saverin."),
    ("splitsno", f"But of the {wb['n_broke']} pairs that split, more were a match, not fewer."),
    ("fallen", f"And the {fv['n_fallen']} founders whose companies collapsed? Their signs look just like everyone else's."),
    ("science", "There's one birthday effect science does take seriously."),
    ("school", "Kids born just after the school cutoff are the oldest in their class. In sports, they get picked first."),
    ("schoolno", f"So does that make founders? {pct(ra['share_oldest_third']).capitalize()} were in the oldest third of their class. Everyone else: {pct(ra['null_oldest_third'])}."),
    ("kid", "So, when should you have your kid? Whenever you like."),
    ("answer", "So, do the stars pick founders? No. Not your sign, not your cofounder's, and not your birth month."),
    ("luck", "Luck just does a very good impression of a pattern."),
    ("end", "Scroll down to explore every founder, and find your own sign."),
]

k = Kokoro(os.path.expanduser("~/.cache/kokoro/kokoro-v1.0.onnx"), os.path.expanduser("~/.cache/kokoro/voices-v1.0.bin"))
out, total = [], 0.0
with tempfile.TemporaryDirectory() as td:
    for bid, say in LINES:
        samples, sr = k.create(say, voice="af_heart", speed=1.0, lang="en-us")
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
         "**Post text:** I put 338 founders of the world's biggest companies on the day they were born and tested what astrology says about them: signs, cofounder matches, breakups, even school birthdays. One result surprised me.", "",
         f"The film on the page plays this narration (voice: Kokoro af_heart), about {int(total // 60)} min {int(total % 60)} s. Record the screen while it plays, or read these lines over it yourself.", ""]
lines += [f"{n + 1}. {say}" for n, (bid, say) in enumerate(LINES)]
open(os.path.join(ROOT, "VIDEO_SCRIPT.md"), "w").write("\n".join(lines) + "\n")
print(len(out), "lines,", round(total, 1), "seconds of narration,", os.path.getsize(os.path.join(DATA, "film.json")) // 1024, "KB")
