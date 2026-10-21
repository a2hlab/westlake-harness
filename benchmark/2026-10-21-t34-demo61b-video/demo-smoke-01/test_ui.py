"""Offline only: real BMS raw marker path with mocked transport; local bash envelope."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import ui

ROOT = Path(os.environ.get("T34_MAIN", Path(__file__).resolve().parents[3]))
spec = importlib.util.spec_from_file_location("ui_test_bms", ROOT / ui.BMS)
bms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bms)
BOOT = "dc603250-21c6-4aaf-ab84-d28cfe096ee5"
SESSION = dict(serial=ui.SERIAL, boot=BOOT,
               holder="inner(cc-video) 123 2026-10-21T02:00:00+0800",
               start=1792519200)
# Derive exact test epoch from literal holder rather than maintaining two fixtures.
SESSION["start"] = ui.datetime.fromisoformat(SESSION["holder"].split()[2]).timestamp()


class Tests(unittest.TestCase):
    def budget(self, age=0, recovery=False, action="launch", session=None):
        s = session or SESSION
        return ui.Budget(s, recovery, action, wall=lambda: SESSION["start"] + age,
                         mono=lambda: 100)

    def test_fixed_identity_and_time(self):
        for key, value in [("serial", "5cd"), ("boot", ""), ("holder", "outer(codex) 1 x"),
                           ("start", SESSION["start"] + 2)]:
            with self.subTest(key=key), self.assertRaises((RuntimeError, ValueError)):
                self.budget(session=dict(SESSION, **{key: value}))
        for age in (-1, 1200, 1800):
            with self.subTest(age=age), self.assertRaises(RuntimeError):
                self.budget(age=age)

    def test_recovery_and_monotonic(self):
        self.assertEqual(self.budget(1300, True, "capture").left(999), 500)
        with self.assertRaises(RuntimeError):
            self.budget(1300, True, "tap")
        with self.assertRaises(RuntimeError):
            self.budget(1800, True, "capture")
        budget = self.budget()
        budget.mono = lambda: 1300
        with self.assertRaises(RuntimeError):
            budget.left()

    def with_board(self, mode, command="uitest uiInput click 12 34"):
        calls = []
        def transport(board, argv, timeout=60):
            calls.append(argv)
            if argv[-2:] == ["held", ui.SERIAL]:
                return 0, SESSION["holder"] if mode != "holder" else "inner(cc-video) 999 wrong"
            text = argv[-1]
            marker = re.search(r"(__BMS_REMOTE_RC_[0-9a-f]+__)", text).group(1)
            if text.startswith("cat /proc"):
                return 0, (BOOT if mode != "boot" else "other") + "\n" + marker + "0\n"
            if mode == "lost":
                return 0, ""
            response = "T34_UI_RC=0\nT34_AWAKE_RC=0\nT34_POWER_READ_RC=0\nOverrideTimeout=86400000ms\n"
            if mode == "awake":
                response = response.replace("T34_AWAKE_RC=0", "T34_AWAKE_RC=1")
            return 0, response + marker + ("1" if mode == "awake" else "0") + "\n"
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            board = ui.board_class(bms)(SESSION, self.budget(), ROOT, "mock-hdc", out)
            with patch.object(bms.Board, "command", transport):
                if mode == "pass":
                    self.assertEqual(board.shell(command)[0], 0)
                else:
                    with self.assertRaises((RuntimeError, bms.BatchStop)):
                        board.shell(command)
            receipts = [json.loads(p.read_text()) for p in out.glob("ui-*.json")]
        return calls, receipts

    def test_actual_bms_marker_dispatch_and_awake(self):
        calls, receipts = self.with_board("pass")
        writes = [a for a in calls if "T34_UI_RC" in a[-1]]
        self.assertEqual(len(writes), 1)
        self.assertIn("power-shell timeout -o 86400000", writes[0][-1])
        self.assertEqual(receipts[0]["remote_rc"], 0)

    def test_guard_rejects_before_ui(self):
        for mode in ("holder", "boot"):
            with self.subTest(mode=mode):
                calls, receipts = self.with_board(mode)
                self.assertFalse(any("T34_UI_RC" in a[-1] for a in calls))
                self.assertEqual(receipts, [])

    def test_lost_marker_is_not_retried(self):
        calls, receipts = self.with_board("lost")
        self.assertEqual(sum("T34_UI_RC" in a[-1] for a in calls), 1)
        self.assertEqual(receipts[0]["status"], "intent_unknown")

    def test_awake_failure_preserves_completed_ui_receipt(self):
        calls, receipts = self.with_board("awake")
        self.assertEqual(sum("T34_UI_RC" in a[-1] for a in calls), 1)
        self.assertEqual(receipts[0]["status"], "completed")
        self.assertIn("T34_UI_RC=0", receipts[0]["stdout"])
        self.assertEqual(receipts[0]["remote_rc"], 1)

    def test_local_envelope_preserves_ui_error_and_restores_awake(self):
        # Local functions only: no HDC or device. Exercise shell control flow, not strings.
        prelude = ('cat(){ echo ' + BOOT + '; }; '
                   'uitest(){ return 37; }; '
                   'power-shell(){ if [ "$1" = timeout ]; then echo AWAKE_CALLED; '
                   'else echo OverrideTimeout=86400000ms; fi; }; ')
        result = subprocess.run(["bash", "-c", prelude + ui.ui_envelope(
            "uitest uiInput click 1 2", BOOT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 37)
        self.assertIn("AWAKE_CALLED", result.stdout)
        self.assertIn("T34_UI_RC=37", result.stdout)
        self.assertIn("T34_POWER_READ_RC=0", result.stdout)

    def test_removed_actions_rejected_without_device(self):
        for action in ("install", "rollback", "reboot", "lock", "unlock"):
            with self.subTest(action=action), patch("subprocess.run") as run:
                with self.assertRaises(SystemExit):
                    ui.main(["--repo", ".", "--window", ".", "--session", "absent",
                             "--tag", "x", action])
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
