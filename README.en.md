<div align="center">

![xxd-notify](assets/xxd-notify-banner.jpeg)

# xxd-notify

**Walk away while your AI agent works. Your iPhone buzzes only when it actually needs you.**

A Bark notification skill for Claude Code, Codex and other coding agents: it decides *when* to interrupt you, says *what* it needs, and makes sure the message *arrives*.

[简体中文](README.md) · English

</div>

<p align="center"><img src="assets/how-it-works.en.svg" width="100%" alt="The agent stops to ask A or B; your phone gets a notification with the options; you reply A, it ships, and a done notification follows"></p>

## Why

You have probably been here:

1. **Babysitting.** The job takes ninety minutes, so you check the terminal every ten and get nothing else done.
2. **Waiting for nothing.** It stopped at minute three to ask "A or B?" — you see it after lunch, forty minutes later.
3. **Muted.** You wired up notifications, it pinged on every step, you silenced it, and the one that mattered got lost.

xxd-notify fixes all three: it **interrupts only when you're needed**, **says exactly what it needs**, and **doesn't lose the message** when the network flakes.

## When it rings

<p align="center"><img src="assets/levels.en.svg" width="100%" alt="Needs your call and failed/stopped break through Focus; done and requested milestones are regular alerts; everything else is silent"></p>

- **Needs your call** — pick a plan, spend money, email real users, delete data, log in or renew. Sent as Bark `timeSensitive`, so it shows even in Focus mode: without you, nothing moves.
- **Done / milestones you asked for** — regular alerts.
- **Everything else** — silence.

And **it only notifies when you ask it to**. Ordinary chats and tasks never trigger a push.

## What a good notification looks like

| Typical | xxd-notify |
|---|---|
| Task complete | **✅ Data migration finished**<br>12,000 records, all verified<br>took 14 min |
| Action required | **⚠️ #42 needs your call**<br>A Export button in the top bar (recommended)<br>B Put it in the footer<br>Reply A/B in the terminal · *tap to open the proposal* |

- **The subtitle names the project** automatically, so with five sessions open you know which one to answer.
- **The first line is the point** — readable from the lock screen.
- **It asks once.** The same question won't ping you every ten minutes.

## Use it: just tell your agent

> Run the whole test suite and Bark me when it's done — failures too.

> Loop through the open issues. Whenever you need me to confirm something (choose a design, spend money, email real users, delete data), Bark me first and say what to confirm and where to look.

> Process these 500 images, ping me at every 20%, and right away if something breaks.

> Keep an eye on that background batch — tell me if it stalls or the disk gets low, and when it finishes.

A standing rule like "Bark me when you need my call" holds for the whole session or loop; you don't repeat it.

## No agent needed: three commands

```bash
alias notify="python3 ~/.claude/skills/xxd-notify/scripts/xxd_notify.py"

notify run --title "tests" --tail 3 -- npm test          # ✅ or ❌ by exit code; exit code passed through
notify watch --pid 12345 --name "batch" --log logs/latest.log --stall 30 --disk / --min-free 15
notify send -s decide -t "Pick a domain" -b $'A example.com (rec.)\nB example.ai' --url "https://…"
```

## Nothing gets lost

<p align="center"><img src="assets/never-lost.en.svg" width="100%" alt="Retries on failure; when offline it shows a Mac notification and waits in an outbox, then rides along with the next delivered message"></p>

- **Retries** after 2, 5 and 15 seconds — proxies switch, Wi-Fi drops.
- **Really offline?** It shows a local Mac notification right away, keeps the message in an outbox, and resends it with the next successful push, marked with the original time.
- **No spam:** identical messages within 2 minutes are sent once; `--once KEY` limits a topic to one push per hour.
- **Broken bytes still send:** macOS's bash 3.2 mangles Chinese text right after `$var`; that used to kill the whole notification.
- **Auditable:** `notify history` shows what arrived.

## Install in 3 minutes

1. **Get Bark** on your iPhone ([project page](https://github.com/Finb/Bark)) and copy your push URL from the app.
2. **Add the skill:**
   ```bash
   npx skills add https://github.com/nevertoday/xxd-notify --skill xxd-notify
   # or: git clone https://github.com/nevertoday/xxd-notify ~/.claude/skills/xxd-notify   (Codex: ~/.codex/skills/)
   ```
3. **Paste the URL:**
   ```bash
   python3 ~/.claude/skills/xxd-notify/scripts/xxd_notify.py setup
   ```
   Input is hidden and never lands in your shell history. A "🧪 Bark 连接正常" test notification means you're done.

Python 3.8+ only, no dependencies.

## Configure

```bash
notify config show                 # key masked
notify config set sound birdsong
notify config set group "AI Tasks"
notify config set autoSubtitle 0   # no automatic project subtitle
notify test
```

Fields: `sound`, `group`, `level` (fallback when no status), `isArchive`, `icon`, `url`, `badge`, `copy`, `autoCopy`, `autoSubtitle`. Config lives at `~/.config/xxd-notify/config.json` (mode 600); override with `XXD_BARK_CONFIG`, or set `XXD_BARK_ENDPOINT` for CI. Self-hosted [bark-server](https://github.com/Finb/bark-server) works; plain http is allowed only for localhost / LAN addresses.

## From your own scripts

| Exit | Meaning |
|---|---|
| `0` | delivered, or deliberately skipped as a duplicate |
| `3` | not set up yet |
| `4` | Bark rejected it (usually a wrong key) |
| `5` | still offline after retries |

Every non-zero result is kept in the outbox, so `|| true` is safe. The old `scripts/bark_notify.sh --title … --body …` and `scripts/bark_config.py` still work.

## FAQ

**How is this different from a Claude Code Stop hook?** A Stop hook fires whenever the agent stops — done, stuck, or just waiting for a reply. xxd-notify lets the agent decide whether you're actually needed, and puts the ask in the notification. Use both if you like.

**Does it send my code anywhere?** Only a title and a few lines; the skill forbids keys, passwords, tokens, private chats and long source text. Messages pass through Bark's server (api.day.app) — self-host bark-server if that matters.

**Android?** Bark is iPhone / iPad only (it also runs on Apple-silicon Macs).

## Development

```bash
python3 -m unittest discover -s tests   # uses a fake local Bark server
python3 assets/src/build_assets.py      # rebuild the animated SVGs (zh + en)
```

`assets/how-it-works.gif` is a GIF of the main animation for places that don't play SVG.

## License

MIT
