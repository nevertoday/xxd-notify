#!/usr/bin/env python3
import json
import os
import stat
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

CONFIG_PATH = Path(os.environ.get("XXD_BARK_CONFIG", "~/.config/xxd-notify/config.json")).expanduser()
ALLOWED = {"endpoint", "sound", "group", "level", "badge", "url", "icon", "isArchive", "autoCopy", "copy"}
INTEGER_FIELDS = {"badge", "isArchive", "autoCopy"}
DEFAULTS = {"sound": "birdsong", "group": "AI 任务", "level": "active", "isArchive": 1}

def load():
    if not CONFIG_PATH.exists(): return {}
    with CONFIG_PATH.open(encoding="utf-8") as handle: return json.load(handle)

def save(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = CONFIG_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2); handle.write("\n")
    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR); temp_path.replace(CONFIG_PATH)

def masked_endpoint(value):
    try:
        parts = urlsplit(value); segments = parts.path.rstrip("/").split("/")
        if segments and segments[-1]:
            key = segments[-1]; segments[-1] = (key[:4] + "…" + key[-4:]) if len(key) > 10 else "****"
        return urlunsplit((parts.scheme, parts.netloc, "/".join(segments), parts.query, parts.fragment))
    except Exception: return "****"

def show(config):
    visible = dict(config)
    if visible.get("endpoint"): visible["endpoint"] = masked_endpoint(str(visible["endpoint"]))
    print(json.dumps(visible, ensure_ascii=False, indent=2))

def main():
    if len(sys.argv) < 2: print("Usage: bark_config.py show | set FIELD VALUE | reset", file=sys.stderr); return 2
    command = sys.argv[1]; config = load()
    if command == "show" and len(sys.argv) == 2: show(config); return 0
    if command == "reset" and len(sys.argv) == 2:
        endpoint = config.get("endpoint"); config = dict(DEFAULTS)
        if endpoint: config["endpoint"] = endpoint
        save(config); show(config); return 0
    if command == "set" and len(sys.argv) == 4:
        field, raw_value = sys.argv[2:]
        if field not in ALLOWED: print(f"Unsupported field: {field}", file=sys.stderr); return 2
        if raw_value.lower() == "none": config.pop(field, None)
        else:
            value = raw_value
            if field in INTEGER_FIELDS:
                try: value = int(raw_value)
                except ValueError: print(f"{field} must be an integer", file=sys.stderr); return 2
            if field == "endpoint" and not value.startswith("https://"): print("endpoint must use https://", file=sys.stderr); return 2
            config[field] = value
        save(config); show(config); return 0
    print("Usage: bark_config.py show | set FIELD VALUE | reset", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
