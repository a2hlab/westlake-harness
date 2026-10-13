import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("collector", Path(__file__).with_name("collect_window.py"))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = self.root / "plan.json"
        self.keys = self.root / "keys.txt"
        self.keys.write_text("fixture-key\n")
        self.plan.write_text(json.dumps({"serial": collector.SERIAL, "shards": [{"name": "001-fixture-key", "keys_file": str(self.keys)}]}))
        self.runner = self.root / "runner"
        self.run = self.runner / "001-fixture-key" / "run1" / collector.SERIAL / "fixture-key"
        self.run.mkdir(parents=True)
        self.record = self.run / "record.json"
        self.record.write_text(json.dumps({"key": "fixture-key", "package": "fixture.pkg", "apk_sha256": "a" * 64, "finished_at": 1, "screenshots": []}))
        (self.run.parent / "facts.txt").write_text("fixture-key foreground_unconfirmed\n")
        old = {"r4_comparison": {}, "shots": [], "independent_visual": "NOT_LIT", "visual_note": "fixture"}
        bodies = ["{}", json.dumps({"rows": [old]}), "{}", "fixture-parser"]
        sources = []
        for number, body in enumerate(bodies):
            source = self.root / ("source-%d" % number)
            source.write_text(body)
            sources.append({"path": str(source), "sha256": collector.digest(source)})
        self.index = {"sources": sources, "rows": [{"key": "fixture-key", "package": "fixture.pkg", "apk_sha256": "a" * 64, "r4_r6_row": 0, "signed": {"verdict": "not_lit"}}]}

    def collect(self):
        return collector.collect(self.plan, self.runner, self.index, self.root)

    def test_finished_packet_remains_pending_and_smoke_excluded(self):
        (self.runner / "smoke").mkdir()
        with patch.object(collector.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout='{"status":"fixture-only"}', stderr="")) as invoked:
            rows = self.collect()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["visual_verdict"], "PENDING_IMAGE_REVIEW")
        self.assertFalse(rows[0]["human_signoff"])
        self.assertEqual(rows[0]["facts_verbatim"], "fixture-key foreground_unconfirmed\n")
        self.assertEqual(invoked.call_args.args[0][0], "python3")

    def test_unfinished_does_not_invoke_parser(self):
        data = json.loads(self.record.read_text())
        data.pop("finished_at")
        self.record.write_text(json.dumps(data))
        with patch.object(collector.subprocess, "run") as invoked:
            self.assertEqual(self.collect(), [])
        invoked.assert_not_called()

    def test_wrong_board_and_unknown_key_rejected(self):
        self.plan.write_text(json.dumps({"serial": "5ea", "shards": []}))
        with self.assertRaisesRegex(ValueError, "61b serial"):
            self.collect()
        self.plan.write_text(json.dumps({"serial": collector.SERIAL, "shards": [{"name": "001-fixture-key", "keys_file": str(self.keys)}]}))
        self.keys.write_text("unknown-key\n")
        with self.assertRaisesRegex(ValueError, "unknown/duplicate"):
            self.collect()

    def test_wrong_apk_rejected_before_parser(self):
        data = json.loads(self.record.read_text())
        data["apk_sha256"] = "b" * 64
        self.record.write_text(json.dumps(data))
        with patch.object(collector.subprocess, "run") as invoked:
            with self.assertRaisesRegex(ValueError, "APK identity drift"):
                self.collect()
        invoked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
