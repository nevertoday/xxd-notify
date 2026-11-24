#!/usr/bin/env python3
"""Renders assets/how-it-works.gif from the SVGs, and assets/social.png from assets/src/social.html.

    python3 assets/src/build_assets.py && python3 assets/src/make_gif.py
    python3 assets/src/make_gif.py --still levels.svg 3.5 /tmp/out.png   # one frame, for checking

The GIF is for places that can't play SVG animation (X, 小红书, 公众号).
Needs Google Chrome and ffmpeg. Each frame is a headless-Chrome screenshot with every
CSS and SMIL animation paused at time t, so frames are exact, not screen recordings.
"""
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1]
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
FPS = 15
PAGE = """<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#F1EFEA}}svg{{display:block}}</style>
{svg}
<script>
const s=document.querySelector('svg'), t={t};
s.setAttribute('width',{w});s.setAttribute('height',{h});
s.pauseAnimations();s.setCurrentTime(t);
document.getAnimations().forEach(a=>{{a.pause();a.currentTime=t*1000;}});
</script>"""


def size(svg_text):
    import re
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg_text)
    return int(m.group(1)), int(m.group(2))


def shot(svg_path, t, out, tmp, scale=2, slot=0):
    text = svg_path.read_text(encoding="utf-8")
    w, h = size(text)
    page = tmp / f"p{slot}_{t:.4f}.html"
    page.write_text(PAGE.format(svg=text, t=t, w=w, h=h), encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                    f"--user-data-dir={tmp / f'profile{slot}'}", f"--window-size={w},{h}", "--virtual-time-budget=1500",
                    f"--screenshot={out}", page.as_uri()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return Path(out).exists()


def gif(svg_name, dur, out_name, width=900):
    with tempfile.TemporaryDirectory(prefix="xxd-gif-") as d:
        tmp = Path(d)
        n = int(dur * FPS)
        groups = [[i for i in range(n) if i % 8 == g] for g in range(8)]  # one Chrome profile per worker

        def run(grp):
            return all(shot(ASSETS / svg_name, i / FPS, tmp / f"f{i:04d}.png", tmp, slot=grp[0] % 8) for i in grp)

        with ThreadPoolExecutor(8) as ex:
            if not all(ex.map(run, groups)):
                sys.exit(f"✗ {svg_name}: some frames failed")
        vf = (f"scale={width}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];"
              "[b][p]paletteuse=dither=none:diff_mode=rectangle")
        out = ASSETS / out_name
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                        "-vf", vf, "-loop", "0", str(out)], check=True)
        print(f"✓ assets/{out_name}  {n} frames  {out.stat().st_size / 1024:.0f} KB")


def main():
    if not Path(CHROME).exists():
        sys.exit("needs Google Chrome (set CHROME=/path/to/chrome) and ffmpeg")
    if sys.argv[1:2] == ["--still"]:
        name, t, out = sys.argv[2], float(sys.argv[3]), sys.argv[4]
        with tempfile.TemporaryDirectory() as d:
            ok = shot(ASSETS / name, t, out, Path(d))
        print(out if ok else "failed")
        return
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        f"--user-data-dir={Path(d) / 'profile'}", "--window-size=1280,640", "--virtual-time-budget=1500",
                        f"--screenshot={ASSETS / 'social.png'}", (ASSETS / "src" / "social.html").as_uri()],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("✓ assets/social.png  1280×640  (upload it in Settings → Social preview)")
    gif("how-it-works.svg", 14, "how-it-works.gif")
    gif("how-it-works.en.svg", 14, "how-it-works.en.gif")


if __name__ == "__main__":
    main()
