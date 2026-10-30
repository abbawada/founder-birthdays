"""Record the page's narrated film as an MP4 for social media.

The film runs on a fake clock: every timer, animation frame and CSS animation
in the page advances exactly 1/fps seconds per frame, and each frame is a
screenshot. So the video is smooth at any speed of machine, and the narration
lines (from data/film.json) are placed at the exact moment the page starts each
line. Subtitles stay burned in (most people watch muted); the player controls
are hidden.

    python -P tools/record_film.py                        # the whole film -> video/founders-by-birthday.mp4
    python -P tools/record_film.py --from 6 --seconds 8   # a short test clip

Needs Playwright with Chromium, and ffmpeg.
"""
import argparse
import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile

from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PAGE = "file://" + os.path.join(ROOT, "dist", "index.html")

FAKE_CLOCK = r"""
(() => {
  let now = 0, id = 1, rid = 1;
  const t0 = Date.now(), timers = new Map(), rafs = new Map();
  window.__clock = {
    now: () => now,
    advance(ms) {
      const target = now + ms;
      for (;;) {
        let next = null;
        for (const t of timers.values()) if (t.at <= target && (!next || t.at < next.at || (t.at === next.at && t.id < next.id))) next = t;
        if (!next) break;
        now = next.at;
        if (next.every) next.at += next.every; else timers.delete(next.id);
        try { next.fn(...next.args); } catch (e) { console.error(e); }
      }
      now = target;
      const cbs = [...rafs.values()]; rafs.clear();
      cbs.forEach(cb => { try { cb(now); } catch (e) { console.error(e); } });
      document.getAnimations().forEach(a => { if (a.__t0 === undefined) { a.__t0 = now - (a.currentTime || 0); a.pause(); } a.currentTime = now - a.__t0; });
    },
  };
  const fnOf = f => typeof f === "function" ? f : () => {};
  window.setTimeout = (f, ms = 0, ...args) => { const t = {id: id++, at: now + Math.max(0, +ms || 0), fn: fnOf(f), args, every: 0}; timers.set(t.id, t); return t.id; };
  window.setInterval = (f, ms = 0, ...args) => { const e = Math.max(1, +ms || 0), t = {id: id++, at: now + e, fn: fnOf(f), args, every: e}; timers.set(t.id, t); return t.id; };
  window.clearTimeout = window.clearInterval = i => timers.delete(i);
  window.requestAnimationFrame = cb => { const i = rid++; rafs.set(i, cb); return i; };
  window.cancelAnimationFrame = i => rafs.delete(i);
  performance.now = () => now;
  Date.now = () => t0 + now;
  // no real playback: the narration is mixed in afterwards from data/film.json
  window.Audio = function () { return {play: () => Promise.resolve(), pause() {}, currentTime: 0, muted: true, preload: "", addEventListener() {}}; };
})();
"""
# for phones: no player controls, bigger subtitles in the space the controls leave, a bigger chapter label
HIDE = (".f-bar{visibility:hidden!important} body::after{display:none!important}"
        ".f-sub{font-size:30px!important;line-height:1.28!important;width:min(94vw,1120px)!important;bottom:28px!important}"
        ".f-label{font-size:22px!important} .f-label b{font-size:28px!important}")


async def frames(args, ff):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": args.width, "height": args.height}, device_scale_factor=args.scale)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script(FAKE_CLOCK)
        await pg.goto(PAGE + "?still")
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(1500)          # real time, for fonts and images; the page's clock stays at 0
        await pg.add_style_tag(content=HIDE)
        await pg.evaluate("""() => { const F = window.__founders.FILM; let v = F.i; window.__starts = [];
            Object.defineProperty(F, 'i', {get() { return v; }, set(x) { v = x; window.__starts.push([x, __clock.now()]); }}); }""")
        await pg.evaluate("__clock.advance(1)")
        # open the film the way the page's own button does, at the chosen line
        if not await pg.evaluate("() => { const b = document.getElementById('play'); if (b) b.click(); return !!b; }"):
            raise SystemExit("could not find the 'watch the film' button")
        if args.start:
            await pg.evaluate(f"""() => {{ for (let k = 0; k < {args.start}; k++) document.getElementById('fNext').click(); }}""")
        step = 1000 / args.fps
        film = json.load(open(os.path.join(ROOT, "data", "film.json")))
        last = len(film) - 1
        n = 0
        while True:
            await pg.evaluate(f"__clock.advance({step})")
            ff.stdin.write(await pg.screenshot(type="jpeg", quality=93))
            n += 1
            starts = await pg.evaluate("window.__starts")
            t = n / args.fps
            if args.seconds and t >= args.seconds:
                break
            ends = [s for s in starts if s[0] == last]
            if ends and (await pg.evaluate("__clock.now()")) >= ends[-1][1] + film[last]["dur"] * 1000 + 2500:
                break
            if n % (args.fps * 10) == 0:
                print(f"  {t:.0f} s recorded (line {starts[-1][0] + 1 if starts else 0} of {len(film)})", flush=True)
        await b.close()
        if errs:
            print("page errors:", errs)
        return starts, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "video", "founders-by-birthday.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--scale", type=float, default=1.5)      # 1280x720 at 1.5x = 1920x1080, with text big enough for a phone
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--seconds", type=float, default=0)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="film_")
    silent = os.path.join(tmp, "video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(args.fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    starts, n = asyncio.run(frames(args, ff))
    assert ff.stdin
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg failed while encoding the frames")
    # the narration: each line's audio at the moment the page started that line
    film = json.load(open(os.path.join(ROOT, "data", "film.json")))
    first = {}
    for i, ms in starts:
        if i >= args.start:
            first.setdefault(i, ms)
    clip0 = first.get(args.start, 0)
    ins, parts = [], []
    for k, (i, ms) in enumerate(sorted(first.items(), key=lambda x: x[1])):
        a = film[i]["audio"]
        path = os.path.join(tmp, f"line{i:02d}.mp3")
        open(path, "wb").write(base64.b64decode(a.split(",", 1)[1] if a.startswith("data:") else a))
        d = max(0, round(ms - clip0) + 33)
        ins += ["-i", path]
        parts.append(f"[{k + 1}:a]adelay={d}|{d}[a{k}]")
    mix = ";".join(parts) + ";" + "".join(f"[a{k}]" for k in range(len(parts))) + f"amix=inputs={len(parts)}:normalize=0:dropout_transition=0,apad[aout]"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, *ins, "-filter_complex", mix, "-map", "0:v", "-map", "[aout]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", args.out],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg failed while adding the narration:\n" + r.stderr)
    print(f"{args.out}: {n / args.fps:.1f} s, {len(first)} lines, {os.path.getsize(args.out) / 1e6:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
