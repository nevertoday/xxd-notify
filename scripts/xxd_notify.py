#!/usr/bin/env python3
"""xxd-notify: push the moments that need you to your iPhone through Bark.

Standard library only. Subcommands:
  send     one notification (what agents call)
  run      run a command, notify when it ends
  watch    wait for a process / condition, warn on stalls and low disk
  setup    paste your Bark URL once, send a test
  test     send a test notification
  config   show | set FIELD VALUE | unset FIELD | reset | path
  flush    resend notifications that could not be delivered earlier
  history  the last notifications and whether they arrived
"""
import argparse
import collections
import contextlib
import datetime as dt
import getpass
import ipaddress
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

try:
    import fcntl
except ImportError:  # Windows: no locking, dedup still works best-effort
    fcntl = None

CONFIG_PATH = Path(os.environ.get("XXD_BARK_CONFIG", "~/.config/xxd-notify/config.json")).expanduser()
STATE_DIR = Path(os.environ.get("XXD_NOTIFY_STATE", str(CONFIG_PATH.parent))).expanduser()

DEFAULTS = {"sound": "birdsong", "group": "AI 任务", "isArchive": 1}
FIELDS = {
    "endpoint": str, "sound": str, "group": str, "level": str, "icon": str, "url": str,
    "badge": int, "isArchive": int, "autoCopy": int, "copy": str, "autoSubtitle": int,
}
LEVELS = {"critical", "timeSensitive", "active", "passive"}

# status -> (emoji, Bark interruption level)
STATUS = {
    "decide": ("⚠️", "timeSensitive"),   # needs you: choose, pay, approve, log in
    "fail": ("❌", "timeSensitive"),
    "stop": ("⏹️", "timeSensitive"),     # paused / cancelled / halted
    "done": ("✅", "active"),
    "progress": ("▶️", "active"),         # a milestone the user asked for
    "test": ("🧪", "active"),
}
ALIASES = {"cancel": "stop", "pause": "stop", "start": "progress", "stage": "progress",
           "milestone": "progress", "ok": "done", "error": "fail", "confirm": "decide"}
EMOJI_STATUS = [("⚠", "decide"), ("❌", "fail"), ("⏹", "stop"), ("✅", "done"),
                ("▶", "progress"), ("🧪", "test")]

EXIT_USAGE, EXIT_NO_CONFIG, EXIT_REJECTED, EXIT_NETWORK = 2, 3, 4, 5
TITLE_MAX_BYTES, BODY_MAX_BYTES = 240, 2400   # APNs payloads top out around 4 KB
AUTO_DEDUP_SECONDS = 120
HISTORY_KEEP = 500


# ---------------------------------------------------------------- helpers

def clean(text):
    """Text from argv may hold broken bytes (macOS bash 3.2 eats the first byte of a
    Chinese character that follows "$var"). Never let that stop a notification."""
    if text is None:
        return None
    return text.encode("utf-8", "surrogateescape").decode("utf-8", "replace")


def clip(text, max_bytes):
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    return raw[: max_bytes - 3].decode("utf-8", "ignore") + "…"


def now():
    return dt.datetime.now().astimezone()


def stamp(t=None):
    return (t or now()).strftime("%Y-%m-%d %H:%M:%S")


def say(message):
    print(message, file=sys.stderr)


def private_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    tmp.replace(path)


def append_line(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    with contextlib.suppress(OSError):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def read_lines(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            out.append(json.loads(line))
    return out


@contextlib.contextmanager
def state_lock():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handle = (STATE_DIR / ".lock").open("a")
    try:
        if fcntl:
            fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl:
            fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def human_duration(seconds):
    seconds = int(seconds)
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    if h:
        return f"{h} 小时 {m} 分"
    if m:
        return f"{m} 分 {s} 秒"
    return f"{s} 秒"


# ---------------------------------------------------------------- config

def load_config():
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_config(config):
    private_write(CONFIG_PATH, json.dumps(config, ensure_ascii=False, indent=2) + "\n")


def plain_http_ok(host):
    """Self-hosted Bark on this Mac or the home LAN may use http; the public internet may not."""
    if not host:
        return False
    if host == "localhost" or host.endswith(".local"):
        return True
    with contextlib.suppress(ValueError):
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    return False


def normalize_endpoint(raw):
    """Accept what people actually paste: a bare key, the Bark app's sample URL
    (https://api.day.app/KEY/这里改成你自己的推送内容), or a self-hosted server URL."""
    value = (raw or "").strip().strip("'\"")
    if not value:
        raise ValueError("地址是空的")
    if re.fullmatch(r"[A-Za-z0-9]{8,64}", value):
        return f"https://api.day.app/{value}"
    parts = urlsplit(value)
    if parts.scheme not in ("https", "http") or not parts.netloc:
        raise ValueError("看起来不是 Bark 地址：应该以 https:// 开头，或者只粘贴 Key")
    if parts.scheme == "http" and not plain_http_ok(parts.hostname):
        raise ValueError("公网地址必须用 https://（Key 等同于密码）")
    segments = [s for s in parts.path.split("/") if s]
    if parts.hostname == "api.day.app":
        if not segments:
            raise ValueError("地址里没有 Key")
        segments = segments[:1]
    return urlunsplit((parts.scheme, parts.netloc, "/" + "/".join(segments), "", ""))


def resolve_endpoint(config):
    raw = os.environ.get("XXD_BARK_ENDPOINT") or config.get("endpoint")
    if not raw:
        return None
    return normalize_endpoint(str(raw))


def mask(endpoint):
    try:
        parts = urlsplit(endpoint)
        segments = parts.path.rstrip("/").split("/")
        if segments and segments[-1]:
            key = segments[-1]
            segments[-1] = key[:4] + "…" + key[-4:] if len(key) > 10 else "****"
        return urlunsplit((parts.scheme, parts.netloc, "/".join(segments), "", ""))
    except Exception:
        return "****"


def masked_config(config):
    visible = dict(config)
    if visible.get("endpoint"):
        visible["endpoint"] = mask(str(visible["endpoint"]))
    return visible


# ---------------------------------------------------------------- building a message

def resolve_status(status, title):
    if status:
        status = ALIASES.get(status, status)
        if status not in STATUS:
            raise ValueError(f"未知状态：{status}（可用：{', '.join(STATUS)}）")
        return status
    stripped = title.lstrip()
    for mark, name in EMOJI_STATUS:
        if stripped.startswith(mark):
            return name
    return None


def git_root_name(cwd):
    with contextlib.suppress(Exception):
        out = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=2)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).name
    return None


def auto_subtitle(config):
    source = os.environ.get("XXD_NOTIFY_SOURCE")
    if source is not None:
        return source or None
    if str(config.get("autoSubtitle", 1)) == "0":
        return None
    cwd = os.getcwd()
    if cwd in (str(Path.home()), "/"):
        return None
    return git_root_name(cwd) or Path(cwd).name


def build_payload(config, title, body, status=None, subtitle=None, overrides=None):
    title, body = clean(title), clean(body)
    status = resolve_status(status, title)
    if status and not title.lstrip().startswith(STATUS[status][0][0]):
        title = f"{STATUS[status][0]} {title}"
    payload = {"title": clip(title, TITLE_MAX_BYTES), "body": clip(body, BODY_MAX_BYTES)}
    for key in ("sound", "group", "icon", "url", "badge", "isArchive", "autoCopy", "copy"):
        value = config.get(key)
        if value not in (None, ""):
            payload[key] = value
    level = config.get("level") or None
    if status:
        level = STATUS[status][1]
    if level:
        payload["level"] = level
    subtitle = auto_subtitle(config) if subtitle is None else (clean(subtitle) or None)
    if subtitle:
        payload["subtitle"] = clip(subtitle, 120)
    for key, value in (overrides or {}).items():
        if value not in (None, ""):
            payload[key] = clean(value) if isinstance(value, str) else value
    if payload.get("level") and payload["level"] not in LEVELS:
        raise ValueError(f"level 只能是：{', '.join(sorted(LEVELS))}")
    return status, payload


# ---------------------------------------------------------------- delivery

class Rejected(Exception):
    """Bark answered, but not with code 200 (wrong key, bad field…). Retrying won't help."""


def retry_delays():
    raw = os.environ.get("XXD_NOTIFY_RETRY_DELAYS")
    if raw is not None:
        return [float(x) for x in raw.split(",") if x.strip()]
    return [2, 5, 15]


def post_once(endpoint, payload, timeout=10):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(endpoint, data=data, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        if exc.code == 429 or exc.code >= 500:
            raise ConnectionError(f"HTTP {exc.code}") from exc
        raise Rejected(f"HTTP {exc.code}: {raw[:200]}") from exc
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConnectionError(f"不是 Bark 的回应：{raw[:120]}") from exc
    if result.get("code") != 200:
        raise Rejected(raw[:200])
    return raw


def deliver(endpoint, payload):
    """Up to four tries: proxies flap, OpenClash reloads, Wi-Fi drops for a few seconds."""
    delays = retry_delays()
    last = None
    for attempt in range(len(delays) + 1):
        try:
            return post_once(endpoint, payload)
        except Rejected:
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
            last = getattr(exc, "reason", None) or exc
            if attempt < len(delays):
                time.sleep(delays[attempt])
    raise ConnectionError(str(last))


def desktop_fallback(payload):
    if sys.platform != "darwin" or os.environ.get("XXD_NOTIFY_NO_DESKTOP") or not shutil.which("osascript"):
        return False
    def q(text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    script = f"display notification {q(payload.get('body', ''))} with title {q(payload.get('title', ''))}"
    if payload.get("subtitle"):
        script += f" subtitle {q(payload['subtitle'])}"
    with contextlib.suppress(Exception):
        return subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5).returncode == 0
    return False


def record_history(status, payload, result, error=None):
    path = STATE_DIR / "history.jsonl"
    append_line(path, {"time": stamp(), "status": status, "title": payload.get("title"),
                       "subtitle": payload.get("subtitle"), "result": result, "error": error})
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > HISTORY_KEEP * 2:
        private_write(path, "\n".join(lines[-HISTORY_KEEP:]) + "\n")


def dedup_check(payload, once, window_minutes, force):
    """True if this message should be skipped. Records it otherwise."""
    path = STATE_DIR / "dedup.json"
    with state_lock():
        try:
            seen = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except json.JSONDecodeError:
            seen = {}
        t = time.time()
        seen = {k: v for k, v in seen.items() if t - v < 86400 * 2}
        auto_key = "auto:" + json.dumps([payload.get("title"), payload.get("body"), payload.get("subtitle")],
                                        ensure_ascii=False)
        keys = [(auto_key, AUTO_DEDUP_SECONDS)]
        if once:
            keys.append(("once:" + once, window_minutes * 60))
        if not force:
            for key, window in keys:
                if key in seen and t - seen[key] < window:
                    return True
        for key, _ in keys:
            seen[key] = t
        private_write(path, json.dumps(seen, ensure_ascii=False))
    return False


def queue_for_later(status, payload, error):
    append_line(STATE_DIR / "outbox.jsonl", {"time": stamp(), "status": status, "payload": payload, "error": error})


def flush_outbox(endpoint, limit=10, quiet=False):
    path = STATE_DIR / "outbox.jsonl"
    with state_lock():
        pending = read_lines(path)
        if not pending:
            return 0, 0
        sent, keep = 0, []
        for index, item in enumerate(pending):
            if sent >= limit:
                keep.extend(pending[index:])
                break
            payload = dict(item["payload"])
            payload["body"] = clip(f"{payload.get('body', '')}\n（补发：原定 {item['time'][5:16]}）", BODY_MAX_BYTES)
            try:
                post_once(endpoint, payload)
                sent += 1
                record_history(item.get("status"), payload, "resent")
            except Exception:
                keep.extend(pending[index:])
                break
        if keep:
            private_write(path, "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in keep))
        else:
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
    if sent and not quiet:
        say(f"另外补发了 {sent} 条之前没送到的通知")
    return sent, len(keep)


def send(title, body, status=None, subtitle=None, overrides=None, once=None, window=60,
         force=False, dry_run=False, quiet=False, show_json=True):
    """Returns an exit code. 0 = delivered or deliberately skipped as a duplicate."""
    try:
        config = load_config()
        status, payload = build_payload(config, title, body, status, subtitle, overrides)
    except (ValueError, json.JSONDecodeError) as exc:
        say(f"xxd-notify: {exc}")
        return EXIT_USAGE
    try:
        endpoint = resolve_endpoint(config)
    except ValueError as exc:
        say(f"xxd-notify: 配置里的地址有问题：{exc}")
        endpoint = None

    if dry_run:
        print(json.dumps({"endpoint": mask(endpoint) if endpoint else None, "payload": payload},
                         ensure_ascii=False, indent=2))
        return 0
    if dedup_check(payload, once, window, force):
        if not quiet:
            say("skipped: 同样的通知刚发过，这条不重复推")
        record_history(status, payload, "skipped")
        return 0
    if not endpoint:
        say(f"xxd-notify: 还没设置 Bark（{CONFIG_PATH}）。运行 `python3 {Path(__file__).name} setup`。")
        queue_for_later(status, payload, "no config")
        desktop_fallback(payload)
        record_history(status, payload, "queued", "no config")
        return EXIT_NO_CONFIG
    try:
        raw = deliver(endpoint, payload)
    except Rejected as exc:
        say(f"xxd-notify: Bark 拒收了（多半是 Key 不对或已重置）：{exc}")
        queue_for_later(status, payload, str(exc))
        desktop_fallback(payload)
        record_history(status, payload, "queued", str(exc))
        return EXIT_REJECTED
    except ConnectionError as exc:
        say(f"xxd-notify: 重试后还是连不上 Bark：{exc}。已存进待补发，网络恢复后的下一条会顺路补发。")
        queue_for_later(status, payload, str(exc))
        shown = desktop_fallback(payload)
        if shown:
            say("已先在这台 Mac 上弹了一条本机通知。")
        record_history(status, payload, "queued", str(exc))
        return EXIT_NETWORK
    record_history(status, payload, "sent")
    if show_json and not quiet:
        print(raw)
    flush_outbox(endpoint, quiet=quiet)
    return 0


# ---------------------------------------------------------------- subcommands

def add_message_options(parser, title_required=True):
    parser.add_argument("--title", "-t", required=title_required)
    parser.add_argument("--status", "-s", help="decide | fail | stop | done | progress | test")
    parser.add_argument("--subtitle", help="默认自动填项目名；传空字符串则不填")
    parser.add_argument("--sound")
    parser.add_argument("--group")
    parser.add_argument("--level", help="覆盖自动选的打扰程度：critical | timeSensitive | active | passive")
    parser.add_argument("--url", help="点通知打开的地址")
    parser.add_argument("--copy", help="长按通知可复制的内容")
    parser.add_argument("--call", action="store_true", help="持续响铃 30 秒（Bark 的 call=1）")
    parser.add_argument("--once", metavar="KEY", help="同一个 KEY 在 --window 分钟内只推一次")
    parser.add_argument("--window", type=float, default=60, metavar="MIN")
    parser.add_argument("--force", action="store_true", help="不去重")
    parser.add_argument("--dry-run", action="store_true", help="只打印要发的内容，不发")
    parser.add_argument("--quiet", "-q", action="store_true")


def message_overrides(args):
    out = {"sound": args.sound, "group": args.group, "level": args.level, "url": args.url, "copy": args.copy}
    if args.call:
        out["call"] = "1"
    return out


def cmd_send(args):
    body = args.body
    if body == "-":
        body = sys.stdin.read().strip()
    if not clean(args.title).strip() or not clean(body or "").strip():
        say("xxd-notify: --title 和 --body 都要有内容")
        return EXIT_USAGE
    return send(args.title, body, args.status, args.subtitle, message_overrides(args), args.once,
                args.window, args.force, args.dry_run, args.quiet)


def cmd_run(args):
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        say("用法：xxd_notify.py run [选项] -- 命令 参数…")
        return EXIT_USAGE
    name = args.title or clip(" ".join(shlex.quote(c) for c in command[:3]), 60)
    started = time.time()
    tail = collections.deque(maxlen=max(args.tail, 0))
    interrupted = False
    try:
        if args.tail > 0:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, errors="replace", bufsize=1)
            for line in proc.stdout:
                sys.stdout.write(line)
                tail.append(line.rstrip())
            code = proc.wait()
        else:
            code = subprocess.call(command)
    except KeyboardInterrupt:
        interrupted, code = True, 130
    except FileNotFoundError:
        say(f"找不到命令：{command[0]}")
        code = 127
    took = human_duration(time.time() - started)
    lines = [f"耗时 {took}，退出码 {code}"]
    if tail:
        lines += ["最后输出："] + list(tail)
    if interrupted:
        status, title = "stop", f"{name}：被中断"
    elif code == 0:
        status, title = "done", f"{name}：跑完了"
    else:
        status, title = "fail", f"{name}：失败了"
    send(title, "\n".join(lines), status, args.subtitle, message_overrides(args), args.once,
         args.window, args.force, args.dry_run, args.quiet, show_json=False)
    return code


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # An exited child nobody has reaped yet (common under screen/nohup) still answers kill(0).
    with contextlib.suppress(Exception):
        out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        state = out.stdout.strip()
        if out.returncode != 0 or not state or state.startswith("Z"):
            return False
    return True


def cmd_watch(args):
    if not any([args.pid, args.until, args.log, args.disk]):
        say("watch 至少要一个条件：--pid / --until / --log / --disk")
        return EXIT_USAGE
    label = args.name or (f"进程 {args.pid}" if args.pid else "等的任务")
    started = time.time()
    confirmed = 0
    stall_warned = disk_warned = False
    overrides = message_overrides(args)

    def notify(title, body, status, key):
        send(title, body, status, args.subtitle, overrides, f"watch:{label}:{key}", args.window,
             False, args.dry_run, args.quiet, show_json=False)

    while True:
        elapsed = time.time() - started
        if args.log:
            try:
                idle = time.time() - os.path.getmtime(args.log)
            except OSError:
                idle = None
            if idle is not None and idle > args.stall * 60 and not stall_warned:
                notify(f"{label}：疑似卡住", f"日志已 {int(idle // 60)} 分钟没有更新\n{args.log}", "decide", "stall")
                stall_warned = True
            elif idle is not None and idle < 60:
                stall_warned = False
        if args.disk:
            free_gb = shutil.disk_usage(args.disk).free / 1024 ** 3
            if free_gb < args.min_free and not disk_warned:
                notify("磁盘快满了", f"{args.disk} 只剩 {free_gb:.1f}G（警戒线 {args.min_free:g}G）\n正在等：{label}",
                       "decide", "disk")
                disk_warned = True
            elif free_gb > args.min_free + 1:
                disk_warned = False
        finished = False
        if args.pid and not pid_alive(args.pid):
            finished = True
        if args.until:
            ok = subprocess.run(args.until, shell=True, capture_output=True).returncode == 0
            confirmed = confirmed + 1 if ok else 0
            finished = confirmed >= args.confirm
        if finished:
            title = args.title or f"{label}：完成"
            body = args.body or f"等了 {human_duration(elapsed)}"
            send(title, body, args.status or "done", args.subtitle, overrides, None, args.window,
                 args.force, args.dry_run, args.quiet, show_json=False)
            return 0
        if args.timeout and elapsed > args.timeout * 60:
            notify(f"{label}：等太久了", f"已经等了 {human_duration(elapsed)} 还没好，我不等了", "decide", "timeout")
            return 1
        time.sleep(args.interval)


def cmd_setup(args):
    print(f"配置文件：{CONFIG_PATH}")
    raw = args.endpoint
    if raw is None:
        if sys.stdin.isatty():
            print("在 iPhone 的 Bark App 里复制推送地址（形如 https://api.day.app/xxxx/…），粘贴到这里。")
            print("输入不会显示在屏幕上，也不会进命令历史。")
            raw = getpass.getpass("Bark 地址或 Key：")
        else:
            raw = sys.stdin.read()
    try:
        endpoint = normalize_endpoint(raw)
    except ValueError as exc:
        say(f"没保存：{exc}")
        return EXIT_USAGE
    config = load_config()
    config["endpoint"] = endpoint
    for key, value in DEFAULTS.items():
        config.setdefault(key, value)
    save_config(config)
    print("已保存：")
    print(json.dumps(masked_config(config), ensure_ascii=False, indent=2))
    if args.no_test:
        return 0
    return cmd_test(argparse.Namespace(quiet=False))


def cmd_test(args):
    config = load_config()
    prefs = "、".join(f"{k}={config[k]}" for k in ("sound", "group") if config.get(k)) or "默认"
    body = f"{stamp()} 从 {os.uname().nodename if hasattr(os, 'uname') else '这台电脑'} 发出\n偏好：{prefs}"
    code = send("Bark 连接正常", body, "test", "", None, None, 60, True, False, args.quiet, show_json=False)
    if code == 0:
        print("已发送，看一眼手机。")
    return code


def cmd_config(args):
    config = load_config()
    if args.action == "path":
        print(CONFIG_PATH)
        return 0
    if args.action == "show":
        print(json.dumps(masked_config(config), ensure_ascii=False, indent=2))
        return 0
    if args.action == "reset":
        endpoint = config.get("endpoint")
        config = dict(DEFAULTS)
        if endpoint:
            config["endpoint"] = endpoint
    elif args.action in ("set", "unset"):
        if not args.field or args.field not in FIELDS:
            say(f"可设置的字段：{', '.join(FIELDS)}")
            return EXIT_USAGE
        if args.action == "unset" or (args.value or "").lower() == "none":
            config.pop(args.field, None)
        else:
            if args.value is None:
                say("set 需要 FIELD 和 VALUE")
                return EXIT_USAGE
            value = args.value
            try:
                if args.field == "endpoint":
                    value = normalize_endpoint(value)
                elif FIELDS[args.field] is int:
                    value = int(value)
                elif args.field == "level" and value not in LEVELS:
                    raise ValueError(f"level 只能是：{', '.join(sorted(LEVELS))}")
            except ValueError as exc:
                say(f"没保存：{exc}")
                return EXIT_USAGE
            config[args.field] = value
    save_config(config)
    print(json.dumps(masked_config(config), ensure_ascii=False, indent=2))
    return 0


def cmd_flush(args):
    try:
        endpoint = resolve_endpoint(load_config())
    except ValueError as exc:
        say(f"配置里的地址有问题：{exc}")
        return EXIT_NO_CONFIG
    if not endpoint:
        say("还没设置 Bark，先运行 setup")
        return EXIT_NO_CONFIG
    sent, left = flush_outbox(endpoint, limit=args.limit, quiet=True)
    print(f"补发 {sent} 条，还剩 {left} 条")
    return 0 if left == 0 else EXIT_NETWORK


def cmd_history(args):
    items = read_lines(STATE_DIR / "history.jsonl")[-args.n:]
    outbox = read_lines(STATE_DIR / "outbox.jsonl")
    marks = {"sent": "✓ 已送达", "resent": "✓ 补发", "skipped": "· 去重跳过", "queued": "✗ 待补发"}
    for item in items:
        sub = f" [{item['subtitle']}]" if item.get("subtitle") else ""
        err = f"  ({item['error']})" if item.get("error") else ""
        print(f"{item['time']}  {marks.get(item['result'], item['result'])}  {item['title']}{sub}{err}")
    if outbox:
        print(f"\n还有 {len(outbox)} 条没送到，联网后下一条通知会顺路补发，或运行 flush。")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="xxd_notify.py", description="把需要你的时刻推到 iPhone（Bark）。")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("send", help="发一条通知")
    add_message_options(p)
    p.add_argument("--body", "-b", required=True, help="正文；传 - 从标准输入读")
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("run", help="跑一个命令，结束时通知")
    add_message_options(p, title_required=False)
    p.add_argument("--tail", type=int, default=0, help="把最后 N 行输出放进通知")
    p.add_argument("command", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("watch", help="等进程/条件完成；卡住、磁盘不够时提醒")
    add_message_options(p, title_required=False)
    p.add_argument("--body", "-b")
    p.add_argument("--name", help="通知里怎么称呼它，比如「批处理」")
    p.add_argument("--pid", type=int, help="这个进程退出就算完成")
    p.add_argument("--until", metavar="SHELL", help="这条命令返回 0 就算完成")
    p.add_argument("--confirm", type=int, default=1, help="--until 连续成功几次才算（防抖）")
    p.add_argument("--log", help="盯这个日志文件")
    p.add_argument("--stall", type=float, default=30, metavar="MIN", help="日志多少分钟不动算卡住")
    p.add_argument("--disk", metavar="PATH", help="盯这个磁盘的剩余空间")
    p.add_argument("--min-free", type=float, default=10, metavar="GB")
    p.add_argument("--interval", type=float, default=60, metavar="SEC")
    p.add_argument("--timeout", type=float, default=0, metavar="MIN", help="最多等多久，0 = 一直等")
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("setup", help="粘贴 Bark 地址，存好并发一条测试")
    p.add_argument("--endpoint", help=argparse.SUPPRESS)
    p.add_argument("--no-test", action="store_true")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("test", help="发一条测试通知")
    p.add_argument("--quiet", "-q", action="store_true")
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("config", help="show | set FIELD VALUE | unset FIELD | reset | path")
    p.add_argument("action", choices=["show", "set", "unset", "reset", "path"])
    p.add_argument("field", nargs="?")
    p.add_argument("value", nargs="?")
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("flush", help="补发之前没送到的通知")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_flush)

    p = sub.add_parser("history", help="最近的通知和送达情况")
    p.add_argument("-n", type=int, default=20)
    p.set_defaults(func=cmd_history)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
