"""Checks the team builder in a real browser (Playwright + Chromium):

1. Every founder pair (and you with every founder): no "undefined", "NaN" or
   empty text, founding years only when both founders were adults and alive,
   imagined names never equal to a real company, and every replay sums to 100.
2. The live "invent it with Claude" button against a fake claude.ai runtime:
   an answer, a bad answer, a rate limit, switching teams mid-answer (the old
   answer must not land), and Claude switched off (the button hides).
3. Leaving the chapter and coming back keeps the team, the idea and the card.

Run after `pipeline/08_build.py`:
    pip install playwright && python -m playwright install chromium
    python -P tests/team_builder_check.py
Exits 1 if anything fails.
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

PAGE = os.environ.get("PAGE") or "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist", "index.html"))
FAKE_CLAUDE = r"""
window.__mock = {mode: "ok", delay: 400};
window.claude = {use: async (name) => {
  if (name === "sample") { const f = async () => { throw {code: "invalid_request"}; };
    f.json = (prompt, opts) => new Promise((res, rej) => { const m = window.__mock.mode;
      const t = setTimeout(() => m === "ok" ? res({name: "Test Works", pitch: "A test company.", roles: "One builds, one sells."}) : (m === "bad" ? res({}) : rej({code: m})), window.__mock.delay);
      opts && opts.signal && opts.signal.addEventListener("abort", () => { clearTimeout(t); rej({code: "cancelled"}); }); });
    return f; }
  if (name === "downloads") return {save: async () => ({status: "saved"})};
  return null; }};
"""
SWEEP = r"""
(() => {
  const {F, simPerson, realCo, verdictHTML, foundYear, ideaOf, simPool, simDraw, simStats, compatible, rng, REALCOS} = window.__founders.sim, state = window.__founders.state;
  const bad = /undefined|NaN|\bnull\b|\[object|Infinity/, out = [], keys = F.map(f => String(f.i));
  const check = (label, s) => { if (typeof s !== "string" || !s.trim() || bad.test(s)) out.push(label + ": " + String(s).slice(0, 120)); };
  const pair = (a, b, label) => { const m = compatible(a.sign, b.sign);
    check("verdict " + label, verdictHTML(a, b, m, realCo(a, b)));
    for (let v = 0; v < 3; v++) { const d = ideaOf(a, b, v); ["name", "pitch", "roles", "when"].forEach(k => check(k + " " + label, d[k])); if (REALCOS.has(d.name.toLowerCase())) out.push("real company name " + d.name); }
    const fy = foundYear(a, b);
    if (!fy.time && !a.me && !b.me && !(fy.y >= Math.max(a.year, b.year) + 18 && fy.y <= Math.min(2026, a.died || 9999, b.died || 9999))) out.push("year " + label + " " + fy.y); };
  for (let i = 0; i < keys.length; i++) for (let j = i + 1; j < keys.length; j++) { const a = simPerson(keys[i]), b = simPerson(keys[j]); pair(a, b, a.name + "+" + b.name); }
  state.youSet = true; for (const y of [null, 1996]) { state.youYear = y; keys.forEach(k => { const b = simPerson(k); pair(simPerson("me"), b, "you+" + b.name); }); }
  const r = rng(7);
  for (let n = 0; n < 2000; n++) { const a = simPerson(keys[Math.floor(r() * keys.length)]), b = simPerson(keys[Math.floor(r() * keys.length)]); if (a.key === b.key) continue;
    for (const kind of ["clash", "match"]) { const st = simStats(simDraw(simPool(kind, a, b, foundYear(a, b).y, null), 100, n)); if (st.jars.reduce((x, y) => x + y, 0) !== 100 || !isFinite(st.median)) out.push("replay " + a.name + "+" + b.name); } }
  return out.slice(0, 20);
})()
"""


async def main():
    fails = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("pageerror", lambda e: fails.append(f"page error: {e}"))
        await pg.add_init_script(FAKE_CLAUDE)
        await pg.goto(PAGE + "#simulator")
        await pg.wait_for_timeout(2500)
        await pg.evaluate("document.documentElement.style.scrollBehavior='auto'")
        fails += await pg.evaluate(SWEEP)
        idea = lambda: pg.eval_on_selector("#simIdea", "e=>e.innerText")
        await pg.evaluate("window.__founders.state.youSet=false")
        await pg.click("#simAsk"); await pg.wait_for_timeout(700)
        if "Test Works" not in await idea(): fails.append("Claude's answer did not show")
        await pg.evaluate("window.__mock.mode='bad'"); await pg.click("#simAsk"); await pg.wait_for_timeout(700)
        if "idea machine" not in await idea(): fails.append("a bad answer did not fall back to the idea machine")
        await pg.evaluate("window.__mock.mode='rate_limited'"); await pg.click("#simAsk"); await pg.wait_for_timeout(700)
        if not await pg.eval_on_selector("#simAsk", "e=>e.disabled"): fails.append("rate limit did not pause the button")
        await pg.evaluate("document.getElementById('simAsk').disabled=false; window.__mock.mode='ok'; window.__mock.delay=1200")
        await pg.click("#simAsk"); await pg.wait_for_timeout(200); await pg.click("#simChips .qp:nth-child(2)"); await pg.wait_for_timeout(1500)
        if "Test Works" in await idea(): fails.append("an answer for the old team landed on the new team")
        await pg.evaluate("window.__mock.delay=300"); await pg.click("#simAsk"); await pg.wait_for_timeout(600); await pg.click("#simMake"); await pg.wait_for_timeout(1200)
        for sel in ["#lore", "#whatif", "#simulator"]:
            await pg.evaluate(f"document.querySelector('{sel}').scrollIntoView({{block:'center'}})"); await pg.wait_for_timeout(700)
        if "Test Works" not in await idea() or await pg.eval_on_selector("#simCardOut", "e=>e.hidden"): fails.append("coming back to the chapter lost the idea or the card")
        await pg.evaluate("window.__mock.mode='not_granted'"); await pg.click("#simAsk"); await pg.wait_for_timeout(700)
        if not await pg.eval_on_selector("#simAsk", "e=>e.hidden"): fails.append("the Claude button stayed when Claude was switched off")
        await b.close()
    print("\n".join(fails) if fails else "team builder: all checks passed")
    sys.exit(1 if fails else 0)

asyncio.run(main())
