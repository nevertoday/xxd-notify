<div align="center">

# xxd-notify

### Send concise, decision-ready Bark notifications when an agent task reaches a requested milestone or final state

<strong>English</strong> · <a href="README.md">简体中文</a>

</div>

## What it does

`xxd-notify` sends task notifications to an iPhone through Bark. It runs only when the current request explicitly asks for Bark, a phone alert, or a saved notification preference. It does not push ordinary task progress automatically.

## Modes

- **Send:** notify after a real completed, failed, cancelled, or decision-needed state.
- **Setup:** show the current configuration with the Bark key hidden, then change requested preferences.
- **Test:** send a connection test with the test timestamp and active preferences.
- **Milestone:** send only the percentages, stages, or milestones the user requested.

## Send a notification

```bash
./scripts/bark_notify.sh --title "✅ Project ready" --body $'Result: completed\nArtifact: /absolute/path/output.md'
```

Check the returned JSON for `code: 200` before reporting success. You can temporarily override sound, group, level, and URL without writing them to the saved configuration.

## Configure

Configuration is stored at `~/.config/xxd-notify/config.json`, or at the path in `XXD_BARK_CONFIG`. The key is never shown, copied into the repository, or included in logs and artifacts.

```bash
python3 scripts/bark_config.py show
python3 scripts/bark_config.py set sound birdsong
python3 scripts/bark_config.py set group "AI Tasks"
python3 scripts/bark_config.py reset
```

If configuration is missing, ask the user to enter setup mode. Never invent a key or send passwords, tokens, private conversations, or long source text.

## Install

```bash
npx skills add https://github.com/nevertoday/xxd-notify --skill xxd-notify
```
