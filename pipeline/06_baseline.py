"""Birth-seasonality baseline from Our World in Data's mirror of the Human
Fertility Database monthly births (birth rate per day, by country and month).

Output: data/baseline.json  {country: {year: [12 monthly shares]}} plus the
list of countries covered. Shares are of births in that year by month,
already adjusted for month length (rate per day x days in month).
"""
import calendar
import csv
import os
from collections import defaultdict

from common import CACHE, DATA, save_json

src = os.path.join(CACHE, "owid", "monthly-birth-rate-per-day.csv")
raw = defaultdict(lambda: defaultdict(dict))
for r in csv.DictReader(open(src)):
    y, m = r["month"].split("-")
    try:
        raw[r["entity"]][int(y)][int(m)] = float(r["birth_rate_per_day"])
    except ValueError:
        pass
baseline = {}
for ent, years in raw.items():
    baseline[ent] = {}
    for y, months in years.items():
        if len(months) != 12:
            continue
        counts = [months[m] * calendar.monthrange(y, m)[1] for m in range(1, 13)]
        tot = sum(counts)
        baseline[ent][str(y)] = [round(c / tot, 6) for c in counts]
save_json(os.path.join(DATA, "baseline.json"), {
    "source": "Our World in Data, 'Monthly birth rate per day' (Human Fertility Database STFF mirror), downloaded 2026-10-29, https://ourworldindata.org/grapher/monthly-birth-rate-per-day",
    "countries": {k: [min(map(int, v)), max(map(int, v))] for k, v in baseline.items()},
    "shares": baseline})
for k, v in sorted(baseline.items()):
    ys = sorted(map(int, v))
    print(f"{k:20s} {ys[0]}-{ys[-1]}  ({len(ys)} years)")
