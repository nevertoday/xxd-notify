"""Run: python3 -m unittest discover -s tests

Talks to a fake Bark server on 127.0.0.1; never touches your real config or phone."""
import json
import os
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


class NotifyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeBark)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}/TESTKEY1234567890"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        FakeBark.plan, FakeBark.received = [], []
        self.tmp = tempfile.TemporaryDirectory()
        self.config = Path(self.tmp.name) / "config.json"
        self.config.write_text(json.dumps({"endpoint": self.endpoint, "sound": "birdsong",
                                           "group": "AI 任务", "level": "active"}))
        self.env = dict(os.environ, XXD_BARK_CONFIG=str(self.config), XXD_NOTIFY_RETRY_DELAYS="0,0,0",
                        XXD_NOTIFY_NO_DESKTOP="1", XXD_NOTIFY_SOURCE="demo-project", LANG="en_US.UTF-8")
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


if __name__ == "__main__":
    unittest.main()
