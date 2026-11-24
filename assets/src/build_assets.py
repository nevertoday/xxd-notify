#!/usr/bin/env python3
"""Builds the README illustrations (Chinese + English). The GitHub social card is assets/src/social.html.

    python3 assets/src/build_assets.py      # SVGs
    python3 assets/src/make_gif.py          # GIF + social.png (needs Google Chrome + ffmpeg)

Pure SVG + CSS/SMIL animation, so GitHub plays them inside <img> with no JavaScript.
Palette: warm paper, the same family as ghostty-tint."""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]

PAGE, CARD, LINE, LINE2 = "#F1EFEA", "#FBFAF8", "#E2DED6", "#DDD9D0"
INK, INK2, INK3 = "#2B2A27", "#8A867D", "#BDB8AD"
RED, AMBER, GREEN = "#C25B52", "#B07A1F", "#3E8A5E"
CORAL, SAGE, APRICOT, MIST, LILAC = "#EBD6D3", "#DDE7D3", "#EFDFC9", "#D7E2EC", "#E0DAEA"
SANS = ("-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Noto Sans CJK SC',"
        "'Microsoft YaHei','Segoe UI',sans-serif")
MONO = "ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,'PingFang SC','Microsoft YaHei',monospace"

BELL = ("M0,-8.5 C-4.6,-8.5 -6.6,-5 -6.6,-1.2 L-6.6,3.6 L-8.6,5.8 L8.6,5.8 L6.6,3.6 L6.6,-1.2 "
        "C6.6,-5 4.6,-8.5 0,-8.5 Z M-2.4,7.4 A2.4,2.4 0 0 0 2.4,7.4 Z")
SHADOW = ('<filter id="sh" x="-15%" y="-15%" width="130%" height="140%">'
          '<feDropShadow dx="0" dy="14" stdDeviation="16" flood-color="#3A3326" flood-opacity=".16"/></filter>'
          '<filter id="sh2" x="-10%" y="-20%" width="120%" height="160%">'
          '<feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#3A3326" flood-opacity=".10"/></filter>')
WALL = (f'<linearGradient id="wall" x1="0" y1="0" x2=".35" y2="1">'
        f'<stop offset="0" stop-color="{MIST}"/><stop offset=".55" stop-color="{LILAC}"/><stop offset="1" stop-color="{APRICOT}"/></linearGradient>')


def t(x):
    return escape(x, quote=False)


def width(s, size):
    """Rough text width: CJK and emoji ≈ 1em, everything else ≈ .56em."""
    return sum(size if ord(c) > 0x2E80 or ord(c) in (0x26A0, 0x23F9, 0x2705, 0x25B6) else size * .56 for c in s)


def appear(name, dur, t_in, t_out=None, dy=6, fade=0.45, scale=None):
    """Keyframes: hidden until t_in, visible until t_out (default: until the loop resets)."""
    t_out = dur - 0.6 if t_out is None else t_out
    p = lambda s: f"{max(0.0, min(100.0, s / dur * 100)):.2f}%"
    hidden = f"opacity:0;transform:translateY({dy}px)" + (f" scale({scale})" if scale else "")
    return (f"@keyframes {name}{{0%,{p(t_in)}{{{hidden}}}"
            f"{p(t_in + fade)},{p(t_out)}{{opacity:1;transform:none}}"
            f"{p(t_out + fade)},100%{{opacity:0;transform:none}}}}"
            f".{name}{{animation:{name} {dur}s infinite both;transform-box:fill-box;transform-origin:center}}")


def svg(width_, height, title, css, body, defs=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_} {height}" width="{width_}" height="{height}" role="img" aria-label="{escape(title)}">
<title>{t(title)}</title>
<defs>{SHADOW}{WALL}{defs}</defs>
<style>
svg{{fill:{INK}}}
text{{font-family:{SANS}}}
.mono{{font-family:{MONO}}}
{css}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}
</style>
<rect width="{width_}" height="{height}" rx="22" fill="{PAGE}"/>
{body}
</svg>
"""


def window(x, y, w, h, title, tint, cid):
    """A light terminal window whose title bar follows the pane colour (ghostty-tint style)."""
    out = [f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/></clipPath>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#000" opacity=".9" filter="url(#sh)"/>',
           f'<g clip-path="url(#{cid})"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{tint}"/></g>']
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        out.append(f'<circle cx="{x + 20 + i * 20}" cy="{y + 17}" r="6" fill="{c}"/>')
    out.append(f'<text x="{x + w / 2}" y="{y + 21.5}" font-size="12" fill="{INK}" opacity=".5" text-anchor="middle">{t(title)}</text>')
    return "\n".join(out)


def phone(x, y, w, h, clock, date):
    """Dark bezel, soft pastel lock screen. Returns (svg, screen_x, screen_w)."""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="42" fill="{INK}" filter="url(#sh)"/>',
           f'<rect x="{x + 8}" y="{y + 8}" width="{w - 16}" height="{h - 16}" rx="34" fill="url(#wall)"/>',
           f'<rect x="{x + w / 2 - 42}" y="{y + 18}" width="84" height="23" rx="11.5" fill="#1B1A18"/>',
           f'<text x="{x + w / 2}" y="{y + 100}" font-size="54" font-weight="300" text-anchor="middle" fill="{INK}" opacity=".88">{clock}</text>',
           f'<text x="{x + w / 2}" y="{y + 124}" font-size="13" text-anchor="middle" fill="{INK}" opacity=".6">{t(date)}</text>',
           f'<rect x="{x + w / 2 - 50}" y="{y + h - 22}" width="100" height="4" rx="2" fill="{INK}" opacity=".35"/>']
    return "\n".join(out)


def notification(x, y, w, lines, now_label, tag=None, tag_tint=CORAL, tag_ink=RED, scale=1.0):
    """iOS-style banner. lines = [title, subtitle, *body]."""
    title, sub, *rows = lines
    last = 88 + 17 * (len(rows) - 1)
    h = last + (44 if tag else 18)
    out = [f'<g transform="translate({x},{y}) scale({scale})">',
           f'<rect width="{w}" height="{h}" rx="16" fill="{CARD}" fill-opacity=".94" stroke="#fff" filter="url(#sh2)"/>',
           f'<rect x="12" y="12" width="22" height="22" rx="6" fill="{RED}"/>',
           f'<path d="{BELL}" transform="translate(23,22.5) scale(.82)" fill="{CARD}"/>',
           f'<text x="42" y="27" font-size="11" fill="{INK2}" letter-spacing=".5">BARK</text>',
           f'<text x="{w - 12}" y="27" font-size="11" fill="{INK2}" text-anchor="end">{t(now_label)}</text>',
           f'<text x="12" y="52" font-size="13.5" font-weight="700">{t(title)}</text>',
           f'<text x="12" y="69" font-size="11" fill="{INK2}">{t(sub)}</text>']
    for i, row in enumerate(rows):
        out.append(f'<text x="12" y="{88 + 17 * i}" font-size="12" fill="{INK}" opacity=".82">{t(row)}</text>')
    if tag:
        ty = last + 12
        out.append(f'<rect x="12" y="{ty}" width="{width(tag, 11) + 22:.0f}" height="20" rx="10" fill="{tag_tint}"/>'
                   f'<text x="23" y="{ty + 14}" font-size="11" fill="{tag_ink}">{t(tag)}</text>')
    out.append("</g>")
    return "\n".join(out), h


# ------------------------------------------------------------------ 1. how it works (hero)

HERO = {
    "zh": {
        "title": "xxd-notify 怎么工作：AI 卡在要你拍板的地方，手机才响",
        "term": "claude — my-app",
        "lines": ["✻ 处理 issue #42：设置页导出", "  ⎿ 改完 6 个文件，测试 312/312",
                  "  ? 导出按钮放哪？A / B / C", "  ⏸ 等你拍板…", "❯ A",
                  "  ✓ 已上线，issue 已关闭"],
        "clock": "09:47", "date": "11月3日 星期二", "now": "现在",
        "n1": ["⚠️ #42 要你选方案", "my-app", "A 顶栏右侧（推荐）", "B 页面底部", "回终端回复 A/B"],
        "n2": ["✅ #42 已上线并关闭", "my-app", "6 个文件 · 测试 312/312", "用时 18 分钟"],
        "tag1": "专注模式下也会亮屏", "tag2": "普通提醒",
        "cap1": "你去忙你的。", "cap2": "只有 AI 卡在要你拍板的地方，手机才会响。",
        "cap3": "不用守着终端，也不会被每个小步骤吵到。做完了，它再告诉你一声。",
    },
    "en": {
        "title": "How xxd-notify works: your phone buzzes only when the agent needs you",
        "term": "claude — my-app",
        "lines": ["✻ Working on issue #42: settings export", "  ⎿ 6 files changed, tests 312/312",
                  "  ? Where should Export go? A/B/C", "  ⏸ waiting for you…", "❯ A",
                  "  ✓ Shipped, issue closed"],
        "clock": "09:47", "date": "Tuesday, November 3", "now": "now",
        "n1": ["⚠️ #42 needs your call", "my-app", "A  Top bar, right (rec.)", "B  Page footer", "Reply A/B in the terminal"],
        "n2": ["✅ #42 shipped and closed", "my-app", "6 files · tests 312/312", "took 18 min"],
        "tag1": "breaks through Focus", "tag2": "regular alert",
        "cap1": "Walk away.", "cap2": "It pings you only when the agent needs you.",
        "cap3": "No babysitting, no buzz for every step — and a heads-up when it's done.",
    },
}


def build_hero(lang):
    s = HERO[lang]
    dur = 14
    css, body = [], []
    tx, ty, tw, th = 32, 32, 540, 262
    body.append(window(tx, ty, tw, th, s["term"], CORAL, "win"))
    colors = [INK, GREEN, RED, INK2, INK, GREEN]
    times = [0.4, 1.4, 2.6, 3.2, 8.2, 9.4]
    outs = [None, None, None, 8.0, None, None]
    for i, (line, color, tin, tout) in enumerate(zip(s["lines"], colors, times, outs)):
        name = f"l{i}"
        css.append(appear(name, dur, tin, tout, dy=4))
        y = ty + 72 + i * 34 - (34 if i >= 4 else 0)
        weight = ' font-weight="700"' if i == 2 else ""
        body.append(f'<g class="{name}"><text class="mono" x="{tx + 24}" y="{y}" font-size="15" fill="{color}"'
                    f' style="white-space:pre"{weight}>{t(line)}</text></g>')
    css.append(f"@keyframes blink{{0%,22%{{opacity:0}}23%,26%{{opacity:1}}27%,30%{{opacity:0}}31%,34%{{opacity:1}}35%,38%{{opacity:0}}"
               f"39%,42%{{opacity:1}}43%,46%{{opacity:0}}47%,50%{{opacity:1}}51%,54%{{opacity:0}}55%,57%{{opacity:1}}58%,100%{{opacity:0}}}}"
               f".blink{{animation:blink {dur}s infinite}}")
    body.append(f'<rect class="blink" x="{tx + 24 + width(s["lines"][3], 15) + 6:.0f}" y="{ty + 72 + 3 * 34 - 13}" width="8" height="16" fill="{INK2}"/>')
    body.append(f'<text x="{tx}" y="{ty + th + 50}" font-size="21" font-weight="700">{t(s["cap1"])}'
                f'<tspan fill="{RED}" dx="6">{t(s["cap2"])}</tspan></text>')
    body.append(f'<text x="{tx}" y="{ty + th + 80}" font-size="14.5" fill="{INK2}">{t(s["cap3"])}</text>')

    px, py, pw, ph = 644, 26, 268, 400
    body.append(f'<g class="shake">{phone(px, py, pw, ph, s["clock"], s["date"])}')
    nx, nw = px + 16, pw - 32
    n1, h1 = notification(nx, py + 146, nw, s["n1"], s["now"], s["tag1"], CORAL, RED)
    n2, _ = notification(nx, py + 146, nw, s["n2"], s["now"], s["tag2"], SAGE, GREEN)
    css.append(appear("n1", dur, 4.0, 7.9, dy=-26, fade=0.5, scale=.96))
    css.append(appear("n2", dur, 10.1, None, dy=-26, fade=0.5, scale=.96))
    body.append(f'<g class="n1">{n1}</g><g class="n2">{n2}</g></g>')
    css.append(f"@keyframes shake{{0%,28.6%{{transform:none}}29.3%{{transform:translateX(-4px) rotate(-1deg)}}30%{{transform:translateX(4px) rotate(1deg)}}"
               f"30.7%{{transform:translateX(-3px)}}31.4%{{transform:translateX(3px)}}32.1%,100%{{transform:none}}}}"
               f".shake{{animation:shake {dur}s infinite;transform-box:fill-box;transform-origin:center}}")

    sy = ty + 72 + 2 * 34 - 5
    path = f"M{tx + tw - 6} {sy} C{tx + tw + 40} {sy - 70}, {px - 40} {py + 150}, {px + 4} {py + 190}"
    body.append(f'<path d="{path}" fill="none" stroke="{RED}" stroke-width="1.5" stroke-dasharray="3 6" opacity=".35"/>')
    k = lambda *xs: ";".join(f"{x / dur:.4f}" for x in xs)
    for delay in (0.0, 0.18, 0.36):
        a, b = 3.2 + delay, 4.0 + delay
        body.append(f'<circle r="{5 - delay * 6:.1f}" fill="{RED}">'
                    f'<animateMotion dur="{dur}s" repeatCount="indefinite" path="{path}" calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;{k(a, b)};1"/>'
                    f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;{k(a, a + .05, b - .05, b)};1"/></circle>')
    css.append(appear("tap", dur, 7.6, 8.4, dy=0, fade=0.3))
    body.append(f'<g class="tap"><circle cx="{px + pw / 2}" cy="{py + 146 + h1 / 2}" r="26" fill="{INK}" opacity=".10"/>'
                f'<circle cx="{px + pw / 2}" cy="{py + 146 + h1 / 2}" r="12" fill="{INK}" opacity=".22"/></g>')
    return svg(944, 452, s["title"], "\n".join(css), "\n".join(body))


# ------------------------------------------------------------------ 2. before / after

BEFORE = {
    "zh": {
        "title": "同一个下午：每一步都推的通知 vs xxd-notify",
        "left": "每一步都推", "right": "xxd-notify",
        "noise": [("Claude Code", "等待你的输入"), ("Claude Code", "任务完成"), ("Codex", "命令执行完毕"),
                  ("Claude Code", "等待你的输入"), ("⚠️ 要你选方案", "A 顶栏 / B 底部"), ("Claude Code", "任务完成"),
                  ("Codex", "等待你的输入")],
        "more": "还有 16 条", "muted": "已静音",
        "good": [["⚠️ #42 要你选方案", "my-app", "A 顶栏右侧（推荐）", "B 页面底部"],
                 ["✅ 数据迁移完成", "billing", "1.2 万条记录，核对一致", "用时 14 分钟"]],
        "cap_l": "23 条。要紧的那条被淹没，你只好静音。", "cap_r": "2 条。每一条都要你看，也都写清了要你做什么。",
    },
    "en": {
        "title": "Same afternoon: notify-on-every-step vs xxd-notify",
        "left": "Notify on every step", "right": "xxd-notify",
        "noise": [("Claude Code", "Waiting for your input"), ("Claude Code", "Task complete"), ("Codex", "Command finished"),
                  ("Claude Code", "Waiting for your input"), ("⚠️ Needs your call", "A top bar / B footer"),
                  ("Claude Code", "Task complete"), ("Codex", "Waiting for your input")],
        "more": "16 more", "muted": "Muted",
        "good": [["⚠️ #42 needs your call", "my-app", "A  Top bar, right (rec.)", "B  Page footer"],
                 ["✅ Data migration done", "billing", "12,000 rows, all match", "took 14 min"]],
        "cap_l": "23 pings. The one that mattered got buried, so you muted it.",
        "cap_r": "2 pings. Each one needs you and says exactly what for.",
    },
}


def build_before(lang):
    s = BEFORE[lang]
    body = []
    W, H, pw = 944, 470, 424
    for side, x in ((0, 32), (1, W - 32 - pw)):
        ok = side == 1
        mark, color = ("✓", GREEN) if ok else ("✗", RED)
        body.append(f'<text x="{x}" y="54" font-size="19" font-weight="700"><tspan fill="{color}">{mark}</tspan>'
                    f'<tspan dx="8">{t(s["right"] if ok else s["left"])}</tspan></text>')
        body.append(f'<rect x="{x}" y="72" width="{pw}" height="322" rx="18" fill="url(#wall)"/>')
        if not ok:
            for i, (app, msg) in enumerate(s["noise"]):
                y = 88 + i * 40
                urgent = app.startswith("⚠️")
                body.append(f'<g opacity="{.55 if urgent else .9}"><rect x="{x + 14}" y="{y}" width="{pw - 28}" height="34" rx="10" fill="{CARD}" fill-opacity=".9"/>'
                            f'<rect x="{x + 24}" y="{y + 9}" width="16" height="16" rx="4" fill="{INK3}"/>'
                            f'<text x="{x + 50}" y="{y + 22}" font-size="12.5" font-weight="{700 if urgent else 600}">{t(app)}</text>'
                            f'<text x="{x + 50 + width(app, 12.5) + 10:.0f}" y="{y + 22}" font-size="12.5" fill="{INK2}">{t(msg)}</text>'
                            f'<text x="{x + pw - 26}" y="{y + 22}" font-size="11" fill="{INK3}" text-anchor="end">{14 + i // 3}:{(i * 7) % 60:02d}</text></g>')
            body.append(f'<text x="{x + pw / 2}" y="{88 + 7 * 40 + 18}" font-size="12" fill="{INK2}" text-anchor="middle">{t(s["more"])} ⌄</text>')
            mw = width(s["muted"], 13) + 44
            body.append(f'<g transform="translate({x + pw - mw - 22},{80})"><rect width="{mw:.0f}" height="30" rx="15" fill="{INK}"/>'
                        f'<text x="{mw / 2:.0f}" y="20" font-size="13" fill="{CARD}" text-anchor="middle" style="fill:{CARD}">🔕 {t(s["muted"])}</text></g>')
        else:
            y = 98
            for i, lines in enumerate(s["good"]):
                n, h = notification(x + 18, y, pw - 36, lines, "14:0" + str(3 + i * 5),
                                    tag=None)
                body.append(n)
                y += h + 14
        cap = s["cap_r"] if ok else s["cap_l"]
        body.append(f'<text x="{x}" y="426" font-size="14.5" fill="{INK if ok else INK2}"{" font-weight=\"600\"" if ok else ""}>{t(cap)}</text>')
    return svg(W, H, s["title"], "", "\n".join(body))


# ------------------------------------------------------------------ 3. levels

LEVELS = {
    "zh": {
        "title": "不同的事，不同的响法",
        "head": "不同的事，不同的响法", "col": "打扰程度",
        "rows": [
            ("!", RED, CORAL, "要你拍板", "选方案 · 要花钱 · 发给真实用户 · 删数据 · 要登录", 5, "专注模式下也亮屏"),
            ("✕", RED, CORAL, "失败了 / 停下了", "自己修不了，或额度用完、被迫暂停", 5, "专注模式下也亮屏"),
            ("✓", GREEN, SAGE, "做完了", "整件事做完、验证过才算", 3, "正常提醒"),
            ("▶", AMBER, APRICOT, "你点名的进度", "每 20%、每个阶段——只在你要求时", 3, "正常提醒"),
            ("·", INK2, PAGE, "其余每一步", "读文件、跑命令、改代码……", 0, "一声不吭"),
        ],
    },
    "en": {
        "title": "Different moments, different volume",
        "head": "Different moments, different volume", "col": "How loud",
        "rows": [
            ("!", RED, CORAL, "Needs your call", "pick a plan · spend money · email users · delete · log in", 5, "breaks through Focus"),
            ("✕", RED, CORAL, "Failed / stopped", "can't fix it alone, quota ran out, had to pause", 5, "breaks through Focus"),
            ("✓", GREEN, SAGE, "Done", "the whole job, verified", 3, "regular alert"),
            ("▶", AMBER, APRICOT, "Your milestones", "every 20%, each stage — only on request", 3, "regular alert"),
            ("·", INK2, PAGE, "Every other step", "reading files, running commands, editing…", 0, "silent"),
        ],
    },
}


def build_levels(lang):
    s = LEVELS[lang]
    dur = 6
    css, body = [], []
    body.append(f'<text x="32" y="50" font-size="22" font-weight="700">{t(s["head"])}</text>')
    body.append(f'<text x="912" y="50" font-size="13" fill="{INK2}" text-anchor="end">{t(s["col"])}</text>')
    for i, (glyph, color, tint, name, desc, bars, label) in enumerate(s["rows"]):
        y = 74 + i * 62
        quiet = bars == 0
        if quiet:
            body.append(f'<rect x="24" y="{y}" width="896" height="52" rx="14" fill="none" stroke="{INK3}" stroke-dasharray="5 6"/>')
        else:
            body.append(f'<rect x="24" y="{y}" width="896" height="52" rx="14" fill="{CARD}" stroke="{LINE}"/>')
        cx, cy = 54, y + 26
        if i == 0:
            css.append(f"@keyframes ring{{0%{{transform:scale(1);opacity:.5}}60%,100%{{transform:scale(2.2);opacity:0}}}}"
                       f".ring{{animation:ring 1.8s infinite ease-out;transform-box:fill-box;transform-origin:center}}.ring2{{animation-delay:.6s}}")
            body.append(f'<circle class="ring" cx="{cx}" cy="{cy}" r="14" fill="none" stroke="{RED}" stroke-width="1.5"/>')
            body.append(f'<circle class="ring ring2" cx="{cx}" cy="{cy}" r="14" fill="none" stroke="{RED}" stroke-width="1.5"/>')
        body.append(f'<circle cx="{cx}" cy="{cy}" r="14" fill="{tint}" stroke="{LINE2 if quiet else "none"}"/>')
        body.append(f'<text x="{cx}" y="{cy + 5}" font-size="15" font-weight="800" text-anchor="middle" fill="{color}">{glyph}</text>')
        body.append(f'<text x="86" y="{y + 32}" font-size="16" font-weight="700" fill="{INK2 if quiet else INK}">{t(name)}</text>')
        dx = 252 if lang == "zh" else 264
        body.append(f'<text x="{dx}" y="{y + 32}" font-size="13.5" fill="{INK2}">{t(desc)}</text>')
        for b in range(5):
            bx, bh = 672 + b * 13, 8 + b * 4
            on = b < bars
            name_b = f"b{i}{b}"
            if on:
                start = 0.3 + b * 0.12
                css.append(f"@keyframes {name_b}{{0%,{start / dur * 100:.1f}%{{opacity:.2}}{(start + .15) / dur * 100:.1f}%,88%{{opacity:1}}96%,100%{{opacity:.2}}}}"
                           f".{name_b}{{animation:{name_b} {dur}s infinite}}")
            body.append(f'<rect class="{name_b if on else ""}" x="{bx}" y="{y + 38 - bh}" width="8" height="{bh}" rx="2" '
                        f'fill="{color if on else LINE}"/>')
        body.append(f'<text x="910" y="{y + 31}" font-size="12.5" text-anchor="end" fill="{INK2 if quiet else color}">{t(label)}</text>')
    return svg(944, 400, s["title"], "\n".join(css), "\n".join(body))


# ------------------------------------------------------------------ 4. never lost

LOST = {
    "zh": {
        "title": "网断了也不丢",
        "head": "网断了也不丢", "ai": "AI 发通知", "bark": "Bark 服务器", "phone": "你的 iPhone",
        "lane1": "网络抖一下：自动重试（2s · 5s · 15s）", "ok": "送到了",
        "lane2": "真的断网：先在 Mac 上弹出来，存进待补发", "mac": "Mac 本机通知", "box": "待补发",
        "back": "网好了：下一条送达时顺路补发，标上原定时间", "resent": "补发 · 原定 01:19",
        "chips": ["同一件事 1 小时只推一次", "中文乱码也照样发出", "history 查每一条送没送到"],
    },
    "en": {
        "title": "Nothing gets lost when the network drops",
        "head": "Nothing gets lost when the network drops", "ai": "Agent sends", "bark": "Bark server", "phone": "Your iPhone",
        "lane1": "Network blip: retries on its own (2s · 5s · 15s)", "ok": "delivered",
        "lane2": "Really offline: shows on your Mac, waits in an outbox", "mac": "Mac notification", "box": "outbox",
        "back": "Back online: rides along with the next message, original time noted", "resent": "resent · was 01:19",
        "chips": ["one push per issue per hour", "survives broken shell bytes", "`history` shows what arrived"],
    },
}


def node(x, y, label, icon):
    return (f'<g transform="translate({x},{y})"><rect x="-64" y="-26" width="128" height="52" rx="14" fill="{CARD}" stroke="{LINE}" filter="url(#sh2)"/>'
            f'{icon}<text x="0" y="46" font-size="12.5" text-anchor="middle" fill="{INK2}">{t(label)}</text></g>')


def build_lost(lang):
    s = LOST[lang]
    dur = 12
    css, body = [], []
    k = lambda *xs: ";".join(f"{x / dur:.4f}" for x in xs)
    body.append(f'<text x="32" y="50" font-size="22" font-weight="700">{t(s["head"])}</text>')
    ax, bx, cx, ly = 124, 472, 820, 120
    term_icon = f'<text x="0" y="6" class="mono" font-size="16" font-weight="700" text-anchor="middle" fill="{INK}">❯_</text>'
    cloud_icon = (f'<path d="M-20 8 a10 10 0 0 1 2 -19.5 a13 13 0 0 1 24.5 -3 a9 9 0 0 1 13.5 9 a7 7 0 0 1 0 13.5 z" '
                  f'fill="{MIST}" stroke="{INK}" stroke-width="1.6"/>')
    phone_icon = (f'<rect x="-10" y="-16" width="20" height="32" rx="5" fill="{LILAC}" stroke="{INK}" stroke-width="1.6"/>'
                  f'<circle cx="0" cy="11" r="1.6" fill="{INK}"/>')
    body.append(f'<line x1="{ax + 64}" y1="{ly}" x2="{bx - 64}" y2="{ly}" stroke="{INK3}" stroke-width="2" stroke-dasharray="2 6"/>')
    body.append(f'<line x1="{bx + 64}" y1="{ly}" x2="{cx - 64}" y2="{ly}" stroke="{INK3}" stroke-width="2" stroke-dasharray="2 6"/>')
    body.append(node(ax, ly, s["ai"], term_icon) + node(bx, ly, s["bark"], cloud_icon) + node(cx, ly, s["phone"], phone_icon))

    tries = [(0.4, False), (1.5, False), (2.6, True)]
    for n, (start, ok) in enumerate(tries):
        end = start + (1.6 if ok else 0.7)
        path = f"M{ax + 64} {ly} L{(cx - 64) if ok else (bx - 70)} {ly}"
        body.append(f'<circle r="6" fill="{AMBER if not ok else GREEN}">'
                    f'<animateMotion dur="{dur}s" repeatCount="indefinite" path="{path}" keyPoints="0;0;1;1" keyTimes="0;{k(start, end)};1" calcMode="linear"/>'
                    f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;{k(start, start + .05, end, end + .1)};1"/></circle>')
        if not ok:
            css.append(appear(f"x{n}", dur, end, end + 0.5, dy=0, fade=0.1))
            body.append(f'<g class="x{n}"><text x="{bx - 84}" y="{ly - 14}" font-size="18" font-weight="800" fill="{RED}" text-anchor="middle">✕</text></g>')
    css.append(appear("ok1", dur, 4.2, 5.2, dy=4))
    body.append(f'<g class="ok1"><text x="{cx}" y="{ly - 40}" font-size="13" font-weight="700" fill="{GREEN}" text-anchor="middle">✓ {t(s["ok"])}</text></g>')
    css.append(appear("cap1", dur, 0.3, 5.2, dy=4))
    body.append(f'<g class="cap1"><text x="32" y="280" font-size="15"><tspan fill="{AMBER}">①</tspan> {t(s["lane1"])}</text></g>')

    mac_x, box_x, row_y = 304, 496, 188
    css.append(appear("cap2", dur, 5.4, 8.6, dy=4))
    body.append(f'<g class="cap2"><text x="32" y="280" font-size="15"><tspan fill="{RED}">②</tspan> {t(s["lane2"])}</text></g>')
    for n, start in enumerate((5.4, 5.8, 6.2)):
        end = start + 0.35
        path = f"M{ax + 64} {ly} L{bx - 70} {ly}"
        body.append(f'<circle r="5" fill="{RED}"><animateMotion dur="{dur}s" repeatCount="indefinite" path="{path}" keyPoints="0;0;1;1" keyTimes="0;{k(start, end)};1"/>'
                    f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;{k(start, start + .05, end, end + .05)};1"/></circle>')
    for n in range(3):
        css.append(appear(f"y{n}", dur, 5.75 + n * .4, 6.0 + n * .4 + .3, dy=0, fade=0.1))
        body.append(f'<g class="y{n}"><text x="{bx - 84}" y="{ly - 14}" font-size="18" font-weight="800" fill="{RED}" text-anchor="middle">✕</text></g>')
    drop = f"M{ax} {ly + 26} C{ax} {row_y + 22}, {mac_x - 90} {row_y + 22}, {mac_x} {row_y + 22}"
    body.append(f'<circle r="6" fill="{AMBER}"><animateMotion dur="{dur}s" repeatCount="indefinite" path="{drop}" keyPoints="0;0;1;1" keyTimes="0;{k(6.7, 7.5)};1"/>'
                f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;{k(6.7, 6.75, 7.5, 7.6)};1"/></circle>')
    css.append(appear("mac", dur, 7.5, None, dy=6))
    body.append(f'<g class="mac"><g transform="translate({mac_x},{row_y})">'
                f'<rect width="170" height="44" rx="12" fill="{CARD}" stroke="{LINE}" filter="url(#sh2)"/>'
                f'<rect x="12" y="12" width="20" height="20" rx="5" fill="{RED}"/><path d="{BELL}" transform="translate(22,22) scale(.75)" fill="{CARD}"/>'
                f'<text x="42" y="27" font-size="12.5">{t(s["mac"])}</text></g>'
                f'<g transform="translate({box_x},{row_y})"><rect width="128" height="44" rx="12" fill="{APRICOT}" stroke="{AMBER}" stroke-dasharray="4 4"/>'
                f'<text x="16" y="27" font-size="12.5" fill="{AMBER}" font-weight="600">{t(s["box"])}  1</text></g></g>')

    css.append(appear("cap3", dur, 8.8, None, dy=4))
    body.append(f'<g class="cap3"><text x="32" y="280" font-size="15"><tspan fill="{GREEN}">③</tspan> {t(s["back"])}</text></g>')
    up = f"M{box_x + 128} {row_y + 22} C{box_x + 200} {row_y + 22}, {cx - 40} {row_y + 10}, {cx - 30} {ly + 26}"
    body.append(f'<circle r="6" fill="{GREEN}"><animateMotion dur="{dur}s" repeatCount="indefinite" path="{up}" keyPoints="0;0;1;1" keyTimes="0;{k(9.2, 10.2)};1"/>'
                f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;{k(9.2, 9.25, 10.2, 10.3)};1"/></circle>')
    css.append(appear("resent", dur, 10.2, None, dy=4))
    body.append(f'<g class="resent"><text x="{cx}" y="{ly - 40}" font-size="13" font-weight="700" fill="{GREEN}" text-anchor="middle">✓ {t(s["resent"])}</text></g>')

    x = 32
    for chip in s["chips"]:
        w = width(chip, 13) + 30
        body.append(f'<rect x="{x}" y="304" width="{w:.0f}" height="32" rx="16" fill="{CARD}" stroke="{LINE2}"/>'
                    f'<text x="{x + 15}" y="325" font-size="13">{t(chip)}</text>')
        x += w + 12
    return svg(944, 362, s["title"], "\n".join(css), "\n".join(body))


def main():
    for lang in ("zh", "en"):
        suffix = "" if lang == "zh" else ".en"
        for name, build in (("how-it-works", build_hero), ("before-after", build_before),
                            ("levels", build_levels), ("never-lost", build_lost)):
            path = OUT / f"{name}{suffix}.svg"
            path.write_text(build(lang), encoding="utf-8")
            print(path.relative_to(OUT.parent))


if __name__ == "__main__":
    main()
