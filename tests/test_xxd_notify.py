"""Run: python3 -m unittest discover -s tests

Talks to fake Bark and AIHOT servers on 127.0.0.1; never touches your real config or phone."""
import gzip
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "xxd_notify.py"
WRAPPER = ROOT / "scripts" / "bark_notify.sh"
sys.path.insert(0, str(ROOT / "scripts"))
import xxd_notify  # noqa: E402


class FakeBark(BaseHTTPRequestHandler):
    plan = []        # list of (status, body) to answer with, then 200s
    received = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        FakeBark.received.append(json.loads(self.rfile.read(length).decode("utf-8")))
        status, body = FakeBark.plan.pop(0) if FakeBark.plan else (200, {"code": 200, "message": "success"})
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


class FakeAihot(BaseHTTPRequestHandler):
    feeds = {}       # product -> list of events, or an HTTP status / raw bytes to fail with
    log = []         # one dict per request answered

    def do_GET(self):
        match = re.fullmatch(r"/api/v1/(.+)-resets/recent", self.path)
        product = match.group(1) if match else None
        feed = FakeAihot.feeds.get(product, [])
        etag, raw, status = None, b"", 200
        if isinstance(feed, int):
            status = feed
        elif isinstance(feed, bytes):
            raw = feed
        else:
            raw = json.dumps({"schemaVersion": 1, "count": len(feed), "events": feed}).encode()
            etag = f'W/"v1-{product}-resets-recent-{hashlib.sha1(raw).hexdigest()[:16]}"'
            if self.headers.get("If-None-Match") == etag:
                status, raw = 304, b""
        FakeAihot.log.append({"product": product, "status": status, "ua": self.headers.get("User-Agent")})
        gzipped = bool(raw) and "gzip" in self.headers.get("Accept-Encoding", "")
        if gzipped:
            raw = gzip.compress(raw)
        self.send_response(status)
        if etag:
            self.send_header("ETag", etag)
        if gzipped:
            self.send_header("Content-Encoding", "gzip")
        if status == 429:
            self.send_header("Retry-After", "60")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


def reset_event(event_id, status, post="Claude 的周额度会在今天重置"):
    done = status == "confirmed"
    return {
        "id": event_id, "status": "confirmed" if done else "announced", "title": f"Claude 额度重置 {status}",
        "presentation": {"status": status, "audienceZh": "所有付费用户", "productsZh": "Claude Code"},
        "estimate": None if done else {"label": "北京时间 11月22日 07:00–10:00", "basis": "model"},
        "schedule": None, "confirmedAt": "2026-11-21T17:18:53.000+08:00" if done else None,
        "posts": [{"stage": "预告", "text": post}], "url": "https://aihot.news/claude-reset",
    }


class NotifyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeBark)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}/TESTKEY1234567890"
        cls.aihot = ThreadingHTTPServer(("127.0.0.1", 0), FakeAihot)
        threading.Thread(target=cls.aihot.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.aihot.shutdown()

    def setUp(self):
        FakeBark.plan, FakeBark.received = [], []
        FakeAihot.feeds, FakeAihot.log = {}, []
        self.tmp = tempfile.TemporaryDirectory()
        self.config = Path(self.tmp.name) / "config.json"
        self.config.write_text(json.dumps({"endpoint": self.endpoint, "sound": "birdsong",
                                           "group": "AI 任务", "level": "active"}))
        self.env = dict(os.environ, XXD_BARK_CONFIG=str(self.config), XXD_NOTIFY_RETRY_DELAYS="0,0,0",
                        XXD_NOTIFY_NO_DESKTOP="1", XXD_NOTIFY_SOURCE="demo-project", LANG="en_US.UTF-8",
                        XXD_RESETS_BASE=f"http://127.0.0.1:{self.aihot.server_port}", TZ="America/Los_Angeles",
                        XXD_LAUNCH_AGENTS_DIR=str(Path(self.tmp.name) / "LaunchAgents"),
                        XXD_NOTIFY_NO_LAUNCHCTL="1")
        self.env.pop("XXD_BARK_ENDPOINT", None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, wrapper=False, env=None, **kw):
        cmd = [str(WRAPPER), *args] if wrapper else [sys.executable, str(SCRIPT), *args]
        return subprocess.run(cmd, capture_output=True, text=True, env=env or self.env, timeout=60, **kw)

    def state(self, name):
        path = Path(self.tmp.name) / name
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    # --- the old interface keeps working
    def test_wrapper_sends_and_prints_bark_json(self):
        out = self.run_cli("--title", "✅ 测试通过", "--body", "312/312", wrapper=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('"code": 200', out.stdout)
        sent = FakeBark.received[0]
        self.assertEqual(sent["title"], "✅ 测试通过")
        self.assertEqual(sent["sound"], "birdsong")
        self.assertEqual(sent["subtitle"], "demo-project")

    def test_bash32_broken_bytes_still_send(self):
        # macOS bash 3.2 swallows the first byte of "（" after $reason — the 11-01 failure.
        script = 'reason=CHILD_STAGE_PAUSED; "$0" --title "❌ 任务暂停" --body "第3批 暂停：$reason（登录/额度）"'
        out = subprocess.run(["/bin/bash", "-c", script, str(WRAPPER)], capture_output=True, text=True,
                             env=self.env, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(FakeBark.received[0]["body"].startswith("第3批 暂停："))

    # --- status decides how loudly it rings
    def test_status_from_emoji_sets_level(self):
        self.run_cli("--title", "⚠️ 要你选方案", "--body", "A / B", wrapper=True)
        self.run_cli("--title", "✅ 做完了", "--body", "ok", wrapper=True)
        self.assertEqual(FakeBark.received[0]["level"], "timeSensitive")
        self.assertEqual(FakeBark.received[1]["level"], "active")

    def test_status_flag_adds_emoji(self):
        self.run_cli("send", "-s", "fail", "-t", "部署失败", "-b", "退出码 1")
        self.assertEqual(FakeBark.received[0]["title"], "❌ 部署失败")
        self.assertEqual(FakeBark.received[0]["level"], "timeSensitive")

    def test_explicit_level_wins(self):
        self.run_cli("send", "-s", "decide", "-t", "x", "-b", "y", "--level", "critical")
        self.assertEqual(FakeBark.received[0]["level"], "critical")

    # --- reliability
    def test_retries_then_succeeds(self):
        FakeBark.plan = [(503, {"code": 503}), (500, {"code": 500})]
        out = self.run_cli("send", "-t", "✅ x", "-b", "y")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(len(FakeBark.received), 3)

    def test_wrong_key_is_not_retried_and_is_queued(self):
        FakeBark.plan = [(400, {"code": 400, "message": "failed to get device token"})]
        out = self.run_cli("send", "-t", "✅ x", "-b", "y")
        self.assertEqual(out.returncode, xxd_notify.EXIT_REJECTED)
        self.assertEqual(len(FakeBark.received), 1)
        self.assertEqual(len(self.state("outbox.jsonl")), 1)

    def test_offline_queues_then_next_send_flushes(self):
        env = dict(self.env)
        self.config.write_text(json.dumps({"endpoint": "http://127.0.0.1:9/KEY"}))
        out = self.run_cli("send", "-t", "⚠️ 要你拍板", "-b", "断网时发的", env=env)
        self.assertEqual(out.returncode, xxd_notify.EXIT_NETWORK)
        self.assertEqual(len(self.state("outbox.jsonl")), 1)
        self.config.write_text(json.dumps({"endpoint": self.endpoint}))
        out = self.run_cli("send", "-t", "✅ 网好了", "-b", "这条带出补发")
        self.assertEqual(out.returncode, 0, out.stderr)
        titles = [r["title"] for r in FakeBark.received]
        self.assertEqual(titles, ["✅ 网好了", "⚠️ 要你拍板"])
        self.assertIn("补发", FakeBark.received[1]["body"])
        self.assertEqual(self.state("outbox.jsonl"), [])

    def test_missing_config_is_queued_not_crashed(self):
        self.config.unlink()
        out = self.run_cli("send", "-t", "✅ x", "-b", "y")
        self.assertEqual(out.returncode, xxd_notify.EXIT_NO_CONFIG)
        self.assertIn("setup", out.stderr)

    # --- no spam
    def test_identical_message_within_two_minutes_is_skipped(self):
        self.run_cli("send", "-t", "❌ 批处理没能启动", "-b", "导出")
        out = self.run_cli("send", "-t", "❌ 批处理没能启动", "-b", "导出")
        self.assertEqual(out.returncode, 0)
        self.assertIn("skipped", out.stderr)
        self.assertEqual(len(FakeBark.received), 1)

    def test_once_key(self):
        self.run_cli("send", "-t", "⚠️ 磁盘快满了", "-b", "剩 9G", "--once", "disk")
        self.run_cli("send", "-t", "⚠️ 磁盘快满了", "-b", "剩 8G", "--once", "disk")
        self.run_cli("send", "-t", "⚠️ 磁盘快满了", "-b", "剩 7G", "--once", "disk", "--force")
        self.assertEqual([r["body"] for r in FakeBark.received], ["剩 9G", "剩 7G"])

    # --- run / watch
    def test_run_reports_exit_code_and_passes_it_through(self):
        out = self.run_cli("run", "--title", "跑测试", "--tail", "1", "--",
                           sys.executable, "-c", "print('3 failed'); raise SystemExit(3)")
        self.assertEqual(out.returncode, 3)
        msg = FakeBark.received[0]
        self.assertEqual(msg["title"], "❌ 跑测试：失败了")
        self.assertIn("退出码 3", msg["body"])
        self.assertIn("3 failed", msg["body"])

    def test_watch_until_with_confirm(self):
        flag = Path(self.tmp.name) / "done"
        flag.touch()
        out = self.run_cli("watch", "--name", "导出", "--until", f"test -e '{flag}'", "--confirm", "2",
                           "--interval", "0.1")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(FakeBark.received[-1]["title"], "✅ 导出：完成")

    def test_watch_pid(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.5)"])
        out = self.run_cli("watch", "--pid", str(proc.pid), "--name", "队列", "--interval", "0.2")
        proc.wait()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(FakeBark.received[-1]["title"], "✅ 队列：完成")

    # --- setup / config never show the key
    def test_setup_accepts_bark_app_sample_url(self):
        self.config.unlink()
        out = self.run_cli("setup", "--no-test",
                           input="https://api.day.app/AbCdEfGhIjKlMnOp/这里改成你自己的推送内容\n")
        self.assertEqual(out.returncode, 0, out.stderr)
        saved = json.loads(self.config.read_text())
        self.assertEqual(saved["endpoint"], "https://api.day.app/AbCdEfGhIjKlMnOp")
        self.assertNotIn("AbCdEfGhIjKlMnOp", out.stdout)
        self.assertEqual(oct(self.config.stat().st_mode)[-3:], "600")

    def test_normalize_endpoint(self):
        n = xxd_notify.normalize_endpoint
        self.assertEqual(n("AbCdEfGhIjKl"), "https://api.day.app/AbCdEfGhIjKl")
        self.assertEqual(n("https://bark.example.com/KEY123/"), "https://bark.example.com/KEY123")
        self.assertEqual(n("http://192.168.2.10:8080/KEY"), "http://192.168.2.10:8080/KEY")
        with self.assertRaises(ValueError):
            n("http://bark.example.com/KEY")

    def test_config_show_masks_key(self):
        self.config.write_text(json.dumps({"endpoint": "https://api.day.app/AbCdEfGhIjKlMnOp"}))
        out = self.run_cli("config", "show")
        self.assertIn("AbCd…MnOp", out.stdout)
        self.assertNotIn("AbCdEfGhIjKlMnOp", out.stdout)
        legacy = subprocess.run([sys.executable, str(ROOT / "scripts" / "bark_config.py"), "show"],
                                capture_output=True, text=True, env=self.env)
        self.assertIn("AbCd…MnOp", legacy.stdout)

    def test_dry_run_sends_nothing(self):
        out = self.run_cli("send", "-s", "decide", "-t", "x", "-b", "y", "--dry-run")
        self.assertEqual(out.returncode, 0)
        self.assertEqual(FakeBark.received, [])
        self.assertNotIn("TESTKEY1234567890", out.stdout)

    def test_history(self):
        self.run_cli("send", "-t", "✅ 一", "-b", "1")
        out = self.run_cli("history")
        self.assertIn("✓ 已送达", out.stdout)
        self.assertIn("✅ 一", out.stdout)

    # --- AI quota resets (AIHOT)
    def resets(self, *args):
        return self.run_cli("resets", "check", *args)

    def test_resets_first_check_skips_past_resets_but_pushes_pending(self):
        FakeAihot.feeds = {"antigravity": [reset_event("old", "confirmed")],
                           "claude": [reset_event("next", "announced")]}
        out = self.resets()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(len(FakeBark.received), 1)
        msg = FakeBark.received[0]
        self.assertEqual(msg["title"], "🔄 Claude 要重置额度了")
        self.assertEqual(msg["body"], "预计 北京时间 11月22日 07:00–10:00\n适用：所有付费用户 · Claude Code\n"
                                      "Claude 的周额度会在今天重置")
        self.assertEqual((msg["subtitle"], msg["group"], msg["url"], msg["level"]),
                         ("AIHOT · Claude", "额度重置", "https://aihot.news/claude-reset", "active"))
        self.assertEqual({r["ua"] for r in FakeAihot.log}, {"xxd-notify"})

    def test_resets_announced_then_confirmed_pushes_twice(self):
        FakeAihot.feeds = {"claude": [reset_event("r1", "announced")]}
        self.resets("--only", "claude")
        FakeAihot.feeds = {"claude": [reset_event("r1", "in_progress", post="正在分批重置")]}
        self.resets("--only", "claude")
        FakeAihot.feeds = {"claude": [reset_event("r1", "confirmed", post="已经全部重置")]}
        out = self.resets("--only", "claude")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual([r["title"] for r in FakeBark.received], ["🔄 Claude 要重置额度了", "🔄 Claude 额度已重置"])
        self.assertTrue(FakeBark.received[1]["body"].startswith("确认于 11/21 17:18\n"))

    def test_resets_landing_between_checks_pushes(self):
        self.resets("--only", "claude")
        FakeAihot.feeds = {"claude": [reset_event("r1", "confirmed")]}
        self.resets("--only", "claude")
        self.assertEqual([r["title"] for r in FakeBark.received], ["🔄 Claude 额度已重置"])

    def test_resets_unchanged_feed_is_a_304_and_pushes_nothing(self):
        FakeAihot.feeds = {"claude": [reset_event("r1", "announced")]}
        self.resets("--only", "claude")
        out = self.resets("--only", "claude")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual([r["status"] for r in FakeAihot.log], [200, 304])
        self.assertEqual(len(FakeBark.received), 1)

    def test_resets_likely_completed_does_not_push(self):
        FakeAihot.feeds = {"claude": [reset_event("r1", "announced")]}
        self.resets("--only", "claude")
        FakeAihot.feeds = {"claude": [reset_event("r1", "likely_completed"), reset_event("r2", "expired_unconfirmed")]}
        self.resets("--only", "claude")
        self.assertEqual([r["title"] for r in FakeBark.received], ["🔄 Claude 要重置额度了"])

    def test_resets_lost_state_does_not_push_again(self):
        FakeAihot.feeds = {"claude": [reset_event("r1", "announced")]}
        self.resets("--only", "claude")
        (Path(self.tmp.name) / "resets.json").unlink()
        FakeAihot.feeds = {"claude": [reset_event("r1", "announced", post="补充：大约两小时后")]}
        out = self.resets("--only", "claude")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(len(FakeBark.received), 1)

    def test_resets_one_feed_down_still_checks_the_rest(self):
        FakeAihot.feeds = {"claude": 429, "codex": b"<html>busy</html>", "antigravity": [reset_event("r1", "announced")]}
        out = self.resets("--only", "claude,codex,antigravity")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual([r["title"] for r in FakeBark.received], ["🔄 Antigravity 要重置额度了"])
        self.assertIn("Claude", out.stderr)
        self.assertIn("Codex", out.stderr)

    def test_resets_every_feed_down_is_exit_5_and_silent(self):
        FakeAihot.feeds = {"claude": 503, "codex": b"not json"}
        out = self.resets("--only", "claude,codex")
        self.assertEqual(out.returncode, xxd_notify.EXIT_NETWORK)
        self.assertEqual(FakeBark.received, [])

    def test_resets_unknown_product(self):
        out = self.resets("--only", "bogus")
        self.assertEqual(out.returncode, xxd_notify.EXIT_USAGE)
        self.assertEqual(FakeAihot.log, [])

    def test_resets_dry_run_sends_and_saves_nothing(self):
        FakeAihot.feeds = {"claude": [reset_event("r1", "announced")]}
        out = self.resets("--only", "claude", "--dry-run")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("会推送：🔄 Claude 要重置额度了", out.stdout)
        self.assertEqual(FakeBark.received, [])
        self.assertFalse((Path(self.tmp.name) / "resets.json").exists())

    @unittest.skipUnless(sys.platform == "darwin", "launchd is macOS only")
    def test_resets_install_and_uninstall(self):
        plist = Path(self.env["XXD_LAUNCH_AGENTS_DIR"]) / "com.xxd-notify.resets.plist"
        self.run_cli("resets", "install", "--only", "codex")
        out = self.run_cli("resets", "install", "--only", "claude")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("resets uninstall", out.stdout)
        agent = plistlib.loads(plist.read_bytes())
        self.assertEqual(agent["ProgramArguments"][-4:], ["resets", "check", "--only", "claude"])
        self.assertEqual((agent["StartInterval"], agent["RunAtLoad"]), (600, True))
        out = self.run_cli("resets", "uninstall")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(plist.exists())
        self.assertEqual(self.run_cli("resets", "uninstall").returncode, 0)


if __name__ == "__main__":
    unittest.main()
