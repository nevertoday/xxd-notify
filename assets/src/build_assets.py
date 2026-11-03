#!/usr/bin/env python3
"""Builds the animated README illustrations (Chinese + English).

    python3 assets/src/build_assets.py

Pure SVG + CSS/SMIL animation, so GitHub plays them inside <img> with no JavaScript.
Palette follows assets/xxd-notify-banner.jpeg."""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]

BG, CARD, CARD2, LINE = "#10151e", "#171e2a", "#1e2634", "#2b3546"
CREAM, MUTED, DIM = "#efe8da", "#8d95a5", "#5c6577"
RED, AMBER, GREEN = "#e8472e", "#f1b43c", "#7cc84a"
SANS = "'PingFang SC','Hiragino Sans GB','Microsoft YaHei','Noto Sans CJK SC','Segoe UI',system-ui,sans-serif"
MONO = "'SF Mono','JetBrains Mono',Menlo,Consolas,'PingFang SC','Microsoft YaHei',monospace"

BELL = ("M0,-8.5 C-4.6,-8.5 -6.6,-5 -6.6,-1.2 L-6.6,3.6 L-8.6,5.8 L8.6,5.8 L6.6,3.6 L6.6,-1.2 "
        "C6.6,-5 4.6,-8.5 0,-8.5 Z M-2.4,7.4 A2.4,2.4 0 0 0 2.4,7.4 Z")


def t(x):
    return escape(x, quote=False)


def appear(name, dur, t_in, t_out=None, dy=6, fade=0.45, scale=None):
    """Keyframes: hidden until t_in, visible until t_out (default: until the loop resets)."""
    t_out = dur - 0.6 if t_out is None else t_out
    p = lambda s: f"{max(0.0, min(100.0, s / dur * 100)):.2f}%"
    hidden = f"opacity:0;transform:translateY({dy}px)" + (f" scale({scale})" if scale else "")
    return (f"@keyframes {name}{{0%,{p(t_in)}{{{hidden}}}"
            f"{p(t_in + fade)},{p(t_out)}{{opacity:1;transform:none}}"
            f"{p(t_out + fade)},100%{{opacity:0;transform:none}}}}"
            f".{name}{{animation:{name} {dur}s infinite both;transform-box:fill-box;transform-origin:center}}")


def svg(width, height, title, css, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{escape(title)}">
<title>{t(title)}</title>
<style>
text{{font-family:{SANS};fill:{CREAM}}}
.mono{{font-family:{MONO}}}
{css}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}
</style>
<rect width="{width}" height="{height}" rx="18" fill="{BG}"/>
{body}
</svg>
"""


# ------------------------------------------------------------------ 1. how it works

HERO = {
    "zh": {
        "title": "xxd-notify 怎么工作：AI 卡在要你拍板的地方，手机才响",
        "term": "Claude Code · my-app",
        "lines": ["› 处理 issue #42：设置页导出", "  ✓ 改完 6 个文件，测试 312/312",
                  "  ? 导出按钮放哪？A / B / C", "  ⏸ 等你拍板…", "› A",
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
        "term": "Claude Code · my-app",
        "lines": ["› Working on issue #42: settings export", "  ✓ 6 files changed, tests 312/312",
                  "  ? Where should Export go? A/B/C", "  ⏸ waiting for you…", "› A",
                  "  ✓ Shipped, issue closed"],
        "clock": "09:47", "date": "Tuesday, November 3", "now": "now",
        "n1": ["⚠️ #42 needs your call", "my-app", "A  Top bar, right (rec.)", "B  Page footer", "Reply A/B in the terminal"],
        "n2": ["✅ #42 shipped and closed", "my-app", "6 files · tests 312/312", "took 18 min"],
        "tag1": "breaks through Focus", "tag2": "regular alert",
        "cap1": "Walk away.", "cap2": "It pings you only when the agent needs you.",
        "cap3": "No babysitting, no buzz for every step — and a heads-up when it's done.",
    },
}


def notification(x, y, w, lines, accent, now_label, extra_rows):
    title, sub, *rows = lines
    h = 66 + 17 * len(rows)
    out = [f'<g transform="translate({x},{y})">',
           f'<rect width="{w}" height="{h}" rx="16" fill="#252d3b" stroke="{LINE}"/>',
           f'<rect x="12" y="12" width="22" height="22" rx="6" fill="{RED}"/>',
           f'<path d="{BELL}" transform="translate(23,22.5) scale(.82)" fill="{CREAM}"/>',
           f'<text x="42" y="27" font-size="11" fill="{MUTED}" letter-spacing=".5">BARK</text>',
           f'<text x="{w - 12}" y="27" font-size="11" fill="{MUTED}" text-anchor="end">{t(now_label)}</text>',
           f'<text x="12" y="52" font-size="13.5" font-weight="700">{t(title)}</text>',
           f'<text x="12" y="69" font-size="11" fill="{accent}">{t(sub)}</text>']
    for i, row in enumerate(rows):
        out.append(f'<text x="12" y="{88 + 17 * i}" font-size="12" fill="#d6d0c4">{t(row)}</text>')
    out.append(extra_rows)
    out.append("</g>")
    return "\n".join(out), h


def build_hero(lang):
    s = HERO[lang]
    dur = 14
    css = []
    body = []
    # terminal
    tx, ty, tw, th = 28, 28, 540, 262
    body.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="14" fill="{CARD}" stroke="{LINE}"/>')
    body.append(f'<path d="M{tx} {ty + 14} a14 14 0 0 1 14 -14 h{tw - 28} a14 14 0 0 1 14 14 v20 h-{tw} z" fill="{CARD2}"/>')
    for i, c in enumerate([RED, AMBER, GREEN]):
        body.append(f'<circle cx="{tx + 20 + i * 18}" cy="{ty + 17}" r="5" fill="{c}" opacity=".85"/>')
    body.append(f'<text x="{tx + tw / 2}" y="{ty + 21.5}" font-size="12" fill="{MUTED}" text-anchor="middle">{t(s["term"])}</text>')
    colors = [CREAM, GREEN, AMBER, MUTED, CREAM, GREEN]
    times = [0.4, 1.4, 2.6, 3.2, 8.2, 9.4]
    outs = [None, None, None, 8.0, None, None]
    for i, (line, color, tin, tout) in enumerate(zip(s["lines"], colors, times, outs)):
        name = f"l{i}"
        css.append(appear(name, dur, tin, tout, dy=4))
        y = ty + 70 + i * 34 - (34 if i >= 4 else 0)
        weight = ' font-weight="700"' if i == 2 else ""
        body.append(f'<g class="{name}"><text class="mono" x="{tx + 24}" y="{y}" font-size="15" fill="{color}"{weight}>{t(line)}</text></g>')
    # cursor blink while waiting
    css.append(f"@keyframes blink{{0%,22%{{opacity:0}}23%,26%{{opacity:1}}27%,30%{{opacity:0}}31%,34%{{opacity:1}}35%,38%{{opacity:0}}"
               f"39%,42%{{opacity:1}}43%,46%{{opacity:0}}47%,50%{{opacity:1}}51%,54%{{opacity:0}}55%,57%{{opacity:1}}58%,100%{{opacity:0}}}}"
               f".blink{{animation:blink {dur}s infinite}}")
    body.append(f'<rect class="blink" x="{tx + 24}" y="{ty + 70 + 4 * 34 - 34 - 2}" width="9" height="3" fill="{AMBER}"/>')
    # caption
    body.append(f'<text x="{tx}" y="{ty + th + 46}" font-size="21" font-weight="700">{t(s["cap1"])}'
                f'<tspan fill="{AMBER}" dx="6">{t(s["cap2"])}</tspan></text>')
    body.append(f'<text x="{tx}" y="{ty + th + 76}" font-size="14.5" fill="{MUTED}">{t(s["cap3"])}</text>')

    # phone
    px, py, pw, ph = 640, 22, 268, 396
    body.append(f'<g class="shake"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="40" fill="#0b0f16" stroke="#3a4558" stroke-width="2"/>')
    body.append(f'<rect x="{px + 8}" y="{py + 8}" width="{pw - 16}" height="{ph - 16}" rx="33" fill="#141b27"/>')
    body.append(f'<rect x="{px + pw / 2 - 42}" y="{py + 18}" width="84" height="22" rx="11" fill="#05070b"/>')
    body.append(f'<text x="{px + pw / 2}" y="{py + 98}" font-size="52" font-weight="300" text-anchor="middle" fill="{CREAM}">{s["clock"]}</text>')
    body.append(f'<text x="{px + pw / 2}" y="{py + 122}" font-size="13" text-anchor="middle" fill="{MUTED}">{t(s["date"])}</text>')
    nx, nw = px + 16, pw - 32
    tag1 = (f'<rect x="12" y="{66 + 17 * 3 + 8}" width="{len(s["tag1"]) * (12 if lang == "zh" else 6.4) + 20}" height="20" rx="10" fill="{RED}" opacity=".18"/>'
            f'<text x="22" y="{66 + 17 * 3 + 22}" font-size="11" fill="#ff9c86">{t(s["tag1"])}</text>')
    n1, h1 = notification(nx, py + 146, nw, s["n1"], AMBER, s["now"], tag1)
    tag2 = (f'<rect x="12" y="{66 + 17 * 2 + 8}" width="{len(s["tag2"]) * (12 if lang == "zh" else 6.4) + 20}" height="20" rx="10" fill="{GREEN}" opacity=".16"/>'
            f'<text x="22" y="{66 + 17 * 2 + 22}" font-size="11" fill="{GREEN}">{t(s["tag2"])}</text>')
    n2, _ = notification(nx, py + 146, nw, s["n2"], GREEN, s["now"], tag2)
    css.append(appear("n1", dur, 4.0, 7.9, dy=-26, fade=0.5, scale=.96))
    css.append(appear("n2", dur, 10.1, None, dy=-26, fade=0.5, scale=.96))
    body.append(f'<g class="n1">{n1}</g><g class="n2">{n2}</g>')
    body.append(f'<rect x="{px + pw / 2 - 50}" y="{py + ph - 22}" width="100" height="4" rx="2" fill="#3a4558"/></g>')
    css.append(f"@keyframes shake{{0%,28.6%{{transform:none}}29.3%{{transform:translateX(-4px) rotate(-1deg)}}30%{{transform:translateX(4px) rotate(1deg)}}"
               f"30.7%{{transform:translateX(-3px)}}31.4%{{transform:translateX(3px)}}32.1%,100%{{transform:none}}}}"
               f".shake{{animation:shake {dur}s infinite;transform-box:fill-box;transform-origin:center}}")

    # signal from the question line to the phone
    sy = ty + 70 + 2 * 34 - 5
    path = f"M{tx + tw - 6} {sy} C{tx + tw + 40} {sy - 70}, {px - 40} {py + 150}, {px + 4} {py + 190}"
    body.append(f'<path d="{path}" fill="none" stroke="{AMBER}" stroke-width="1.5" stroke-dasharray="3 6" opacity=".35"/>')
    k = lambda *xs: ";".join(f"{x / dur:.4f}" for x in xs)
    for delay in (0.0, 0.18, 0.36):
        a, b = 3.2 + delay, 4.0 + delay
        body.append(f'<circle r="{5 - delay * 6:.1f}" fill="{AMBER}">'
                    f'<animateMotion dur="{dur}s" repeatCount="indefinite" path="{path}" calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;{k(a, b)};1"/>'
                    f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;{k(a, a + .05, b - .05, b)};1"/></circle>')
    # reply arrow: user answers in terminal
    css.append(appear("tap", dur, 7.6, 8.4, dy=0, fade=0.3))
    body.append(f'<g class="tap"><circle cx="{px + pw / 2}" cy="{py + 146 + h1 / 2}" r="26" fill="{CREAM}" opacity=".16"/>'
                f'<circle cx="{px + pw / 2}" cy="{py + 146 + h1 / 2}" r="12" fill="{CREAM}" opacity=".35"/></g>')
    return svg(936, 440, s["title"], "\n".join(css), "\n".join(body))


# ------------------------------------------------------------------ 2. levels

LEVELS = {
    "zh": {
        "title": "不同的事，不同的响法",
        "head": "不同的事，不同的响法", "col": "打扰程度",
        "rows": [
            ("!", RED, "要你拍板", "选方案 · 要花钱 · 发给真实用户 · 删数据 · 要登录", 5, "专注模式下也亮屏"),
            ("✕", RED, "失败了 / 停下了", "自己修不了，或额度用完、被迫暂停", 5, "专注模式下也亮屏"),
            ("✓", GREEN, "做完了", "整件事做完、验证过才算", 3, "正常提醒"),
            ("▶", AMBER, "你点名的进度", "每 20%、每个阶段——只在你要求时", 3, "正常提醒"),
            ("·", DIM, "其余每一步", "读文件、跑命令、改代码……", 0, "一声不吭"),
        ],
    },
    "en": {
        "title": "Different moments, different volume",
        "head": "Different moments, different volume", "col": "How loud",
        "rows": [
            ("!", RED, "Needs your call", "pick a plan · spend money · email users · delete · log in", 5, "breaks through Focus"),
            ("✕", RED, "Failed / stopped", "can't fix it alone, quota ran out, had to pause", 5, "breaks through Focus"),
            ("✓", GREEN, "Done", "the whole job, verified", 3, "regular alert"),
            ("▶", AMBER, "Your milestones", "every 20%, each stage — only on request", 3, "regular alert"),
            ("·", DIM, "Every other step", "reading files, running commands, editing…", 0, "silent"),
        ],
    },
}


def build_levels(lang):
    s = LEVELS[lang]
    dur = 6
    css, body = [], []
    body.append(f'<text x="32" y="46" font-size="22" font-weight="700">{t(s["head"])}</text>')
    body.append(f'<text x="904" y="46" font-size="13" fill="{MUTED}" text-anchor="end">{t(s["col"])}</text>')
    for i, (glyph, color, name, desc, bars, label) in enumerate(s["rows"]):
        y = 72 + i * 62
        quiet = bars == 0
        dash = ' stroke-dasharray="4 5"' if quiet else ""
        body.append(f'<rect x="24" y="{y}" width="888" height="52" rx="12" fill="{CARD if not quiet else BG}" stroke="{LINE}"{dash}/>')
        cx, cy = 54, y + 26
        if i == 0:
            css.append(f"@keyframes ring{{0%{{transform:scale(1);opacity:.55}}60%,100%{{transform:scale(2.3);opacity:0}}}}"
                       f".ring{{animation:ring 1.8s infinite ease-out;transform-box:fill-box;transform-origin:center}}.ring2{{animation-delay:.6s}}")
            body.append(f'<circle class="ring" cx="{cx}" cy="{cy}" r="13" fill="none" stroke="{RED}" stroke-width="2"/>')
            body.append(f'<circle class="ring ring2" cx="{cx}" cy="{cy}" r="13" fill="none" stroke="{RED}" stroke-width="2"/>')
        body.append(f'<circle cx="{cx}" cy="{cy}" r="13" fill="{color}" opacity="{".25" if quiet else "1"}"/>')
        body.append(f'<text x="{cx}" y="{cy + 5}" font-size="15" font-weight="800" text-anchor="middle" fill="{BG if not quiet else MUTED}">{glyph}</text>')
        body.append(f'<text x="84" y="{y + 32}" font-size="16" font-weight="700" fill="{CREAM if not quiet else MUTED}">{t(name)}</text>')
        dx = 250 if lang == "zh" else 262
        body.append(f'<text x="{dx}" y="{y + 32}" font-size="13.5" fill="{MUTED}">{t(desc)}</text>')
        for b in range(5):
            bx, bh = 668 + b * 13, 8 + b * 4
            on = b < bars
            name_b = f"b{i}{b}"
            if on:
                start = 0.3 + b * 0.12
                css.append(f"@keyframes {name_b}{{0%,{start / dur * 100:.1f}%{{opacity:.15}}{(start + .15) / dur * 100:.1f}%,88%{{opacity:1}}96%,100%{{opacity:.15}}}}"
                           f".{name_b}{{animation:{name_b} {dur}s infinite}}")
            body.append(f'<rect class="{name_b if on else ""}" x="{bx}" y="{y + 38 - bh}" width="8" height="{bh}" rx="2" '
                        f'fill="{color if on else LINE}"/>')
        body.append(f'<text x="904" y="{y + 31}" font-size="12.5" text-anchor="end" fill="{color if not quiet else MUTED}">{t(label)}</text>')
    return svg(936, 392, s["title"], "\n".join(css), "\n".join(body))


# ------------------------------------------------------------------ 3. never lost

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
    return (f'<g transform="translate({x},{y})"><rect x="-64" y="-26" width="128" height="52" rx="12" fill="{CARD}" stroke="{LINE}"/>'
            f'{icon}<text x="0" y="44" font-size="12.5" text-anchor="middle" fill="{MUTED}">{t(label)}</text></g>')


def build_lost(lang):
    s = LOST[lang]
    dur = 12
    css, body = [], []
    k = lambda *xs: ";".join(f"{x / dur:.4f}" for x in xs)
    body.append(f'<text x="32" y="46" font-size="22" font-weight="700">{t(s["head"])}</text>')
    ax, bx, cx, ly = 120, 468, 816, 116
    term_icon = f'<text x="0" y="6" class="mono" font-size="16" text-anchor="middle" fill="{GREEN}">&gt;_</text>'
    cloud_icon = (f'<path d="M-20 8 a10 10 0 0 1 2 -19.5 a13 13 0 0 1 24.5 -3 a9 9 0 0 1 13.5 9 a7 7 0 0 1 0 13.5 z" '
                  f'fill="none" stroke="{CREAM}" stroke-width="2"/>')
    phone_icon = (f'<rect x="-10" y="-16" width="20" height="32" rx="5" fill="none" stroke="{CREAM}" stroke-width="2"/>'
                  f'<circle cx="0" cy="11" r="1.6" fill="{CREAM}"/>')
    body.append(f'<line x1="{ax + 64}" y1="{ly}" x2="{bx - 64}" y2="{ly}" stroke="{LINE}" stroke-width="2" stroke-dasharray="2 6"/>')
    body.append(f'<line x1="{bx + 64}" y1="{ly}" x2="{cx - 64}" y2="{ly}" stroke="{LINE}" stroke-width="2" stroke-dasharray="2 6"/>')
    body.append(node(ax, ly, s["ai"], term_icon) + node(bx, ly, s["bark"], cloud_icon) + node(cx, ly, s["phone"], phone_icon))

    # lane 1: two failed tries, third arrives
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
    body.append(f'<g class="cap1"><text x="32" y="272" font-size="15" fill="{CREAM}"><tspan fill="{AMBER}">①</tspan> {t(s["lane1"])}</text></g>')

    # lane 2: offline -> mac + outbox -> later resent
    mac_x, box_x, row_y = 300, 492, 184
    css.append(appear("cap2", dur, 5.4, 8.6, dy=4))
    body.append(f'<g class="cap2"><text x="32" y="272" font-size="15" fill="{CREAM}"><tspan fill="{RED}">②</tspan> {t(s["lane2"])}</text></g>')
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
                f'<rect width="170" height="44" rx="10" fill="{CARD2}" stroke="{LINE}"/>'
                f'<rect x="12" y="12" width="20" height="20" rx="5" fill="{RED}"/><path d="{BELL}" transform="translate(22,22) scale(.75)" fill="{CREAM}"/>'
                f'<text x="42" y="27" font-size="12.5">{t(s["mac"])}</text></g>'
                f'<g transform="translate({box_x},{row_y})"><rect width="128" height="44" rx="10" fill="{CARD2}" stroke="{AMBER}" stroke-dasharray="4 4"/>'
                f'<text x="16" y="27" font-size="12.5" fill="{AMBER}">{t(s["box"])}  1</text></g></g>')

    css.append(appear("cap3", dur, 8.8, None, dy=4))
    body.append(f'<g class="cap3"><text x="32" y="272" font-size="15" fill="{CREAM}"><tspan fill="{GREEN}">③</tspan> {t(s["back"])}</text></g>')
    up = f"M{box_x + 128} {row_y + 22} C{box_x + 200} {row_y + 22}, {cx - 40} {row_y + 10}, {cx - 30} {ly + 26}"
    body.append(f'<circle r="6" fill="{GREEN}"><animateMotion dur="{dur}s" repeatCount="indefinite" path="{up}" keyPoints="0;0;1;1" keyTimes="0;{k(9.2, 10.2)};1"/>'
                f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;{k(9.2, 9.25, 10.2, 10.3)};1"/></circle>')
    css.append(appear("resent", dur, 10.2, None, dy=4))
    body.append(f'<g class="resent"><text x="{cx}" y="{ly - 40}" font-size="13" font-weight="700" fill="{GREEN}" text-anchor="middle">✓ {t(s["resent"])}</text></g>')

    # chips
    x = 32
    for chip in s["chips"]:
        w = (len(chip) * (13.2 if lang == "zh" else 7.0)) + 28
        body.append(f'<rect x="{x}" y="296" width="{w:.0f}" height="30" rx="15" fill="{CARD}" stroke="{LINE}"/>'
                    f'<text x="{x + 14}" y="316" font-size="13" fill="{MUTED}">{t(chip)}</text>')
        x += w + 12
    return svg(936, 350, s["title"], "\n".join(css), "\n".join(body))


def main():
    for lang in ("zh", "en"):
        suffix = "" if lang == "zh" else ".en"
        for name, build in (("how-it-works", build_hero), ("levels", build_levels), ("never-lost", build_lost)):
            path = OUT / f"{name}{suffix}.svg"
            path.write_text(build(lang), encoding="utf-8")
            print(path.relative_to(OUT.parent))


if __name__ == "__main__":
    main()
