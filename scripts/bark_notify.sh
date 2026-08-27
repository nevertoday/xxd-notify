#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${XXD_BARK_CONFIG:-$HOME/.config/xxd-notify/config.json}"

usage() {
  printf '%s\n' 'Usage: bark_notify.sh --title TITLE --body BODY [--sound NAME] [--group NAME] [--level LEVEL] [--url URL]'
}

title=''; body=''; sound=''; group=''; level=''; url=''
while (($#)); do
  case "$1" in
    --title) title="${2-}"; shift 2 ;;
    --body) body="${2-}"; shift 2 ;;
    --sound) sound="${2-}"; shift 2 ;;
    --group) group="${2-}"; shift 2 ;;
    --level) level="${2-}"; shift 2 ;;
    --url) url="${2-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$title" || -z "$body" ]]; then usage >&2; exit 2; fi
if [[ ! -r "$CONFIG_PATH" ]]; then
  printf 'Bark config not found: %s\n' "$CONFIG_PATH" >&2
  exit 3
fi

python3 - "$CONFIG_PATH" "$title" "$body" "$sound" "$group" "$level" "$url" <<'PY'
import json
import sys
import urllib.error
import urllib.request

config_path, title, body, sound, group, level, url = sys.argv[1:]
with open(config_path, encoding="utf-8") as handle:
    config = json.load(handle)
endpoint = str(config.get("endpoint", "")).strip()
if not endpoint.startswith("https://"):
    raise SystemExit("Bark endpoint is missing or must use https://")
payload = {"title": title, "body": body}
for key in ("sound", "group", "level", "badge", "url", "icon", "isArchive", "autoCopy", "copy"):
    value = config.get(key)
    if value not in (None, ""):
        payload[key] = value
payload.update({key: value for key, value in {"sound": sound, "group": group, "level": level, "url": url}.items() if value})
request = urllib.request.Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read().decode("utf-8", errors="replace")
except urllib.error.HTTPError as exc:
    raw = exc.read().decode("utf-8", errors="replace")
    print(raw)
    raise SystemExit(4) from exc
except urllib.error.URLError as exc:
    print(f"Bark request failed: {exc.reason}", file=sys.stderr)
    raise SystemExit(5) from exc
print(raw)
try:
    result = json.loads(raw)
except json.JSONDecodeError as exc:
    raise SystemExit(6) from exc
if result.get("code") != 200:
    raise SystemExit(7)
PY
