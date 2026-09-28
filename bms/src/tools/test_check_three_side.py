#!/usr/bin/env python3
"""check_three_side.py 单测:通过路径 + 每类 finding 至少一例。"""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parent / "check_three_side.py"

GOOD_SCXML = """<?xml version="1.0" encoding="UTF-8"?>
<scxml xmlns="http://www.w3.org/2005/07/scxml" version="1.0"
       name="test-strategy" initial="S_A">
  <state id="S_A">
    <transition id="T1" event="go" target="S_B"/>
  </state>
  <state id="S_B">
    <transition id="T2" event="finish" target="S_DONE"/>
    <transition id="T3" event="abort" target="S_FAILED"/>
  </state>
  <final id="S_DONE"/>
  <final id="S_FAILED"/>
</scxml>
"""

BROKEN_SCXML = GOOD_SCXML.replace('target="S_DONE"', 'target="S_NOWHERE"')

UNREACHABLE_SCXML = GOOD_SCXML.replace(
    "<final id=\"S_FAILED\"/>",
    "<final id=\"S_FAILED\"/><state id=\"S_ORPHAN\"><transition id=\"T9\" event=\"x\" target=\"S_DONE\"/></state>",
)

DEAD_END_SCXML = """<?xml version="1.0" encoding="UTF-8"?>
<scxml xmlns="http://www.w3.org/2005/07/scxml" version="1.0" initial="S_A">
  <state id="S_A">
    <transition id="T1" event="go" target="S_STUCK"/>
  </state>
  <state id="S_STUCK"/>
</scxml>
"""


def base_doc() -> dict:
    return {
        "schema": "bridge.three-side.v1",
        "progress_point": "测试推进点",
        "android_side": [
            {"ref": "docs/contract.md#anchor", "claim": "安卓侧行为 X"},
            {"tree": "aosp", "path": "frameworks/base/A.java",
             "anchor": "methodA", "claim": "安卓源码语义"},
        ],
        "oh_side": [
            {"tree": "oh", "path": "foundation/B.cpp",
             "anchor": "FuncB", "claim": "宿主侧行为 Y"},
        ],
        "ours": {
            "progress_ref": "docs/progress.md#节",
            "current_state": "S_A",
            "target_state": "S_B",
        },
        "state_machines": {"advancement": "sm/strategy.scxml"},
        "verification": {
            "implementer": "agent-impl",
            "verifier": "agent-verify",
            "receipt": "var/evidence/receipt.md",
            "verdict": "PASS",
            "date": "2026-08-06",
        },
    }


class ThreeSideGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "contract.md").write_text("c", encoding="utf-8")
        (self.root / "docs" / "progress.md").write_text("p", encoding="utf-8")
        (self.root / "evidence").mkdir()
        (self.root / "evidence" / "receipt.md").write_text(
            "verdict PASS by agent-verify", encoding="utf-8")
        (self.root / "sm").mkdir()
        (self.root / "sm" / "strategy.scxml").write_text(
            GOOD_SCXML, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_gate(self, doc: dict) -> tuple[int, str]:
        file = self.root / "three-side.yaml"
        file.write_text(yaml.safe_dump(doc, allow_unicode=True),
                        encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root),
             "--file", str(file)],
            capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def test_pass(self) -> None:
        code, out = self.run_gate(base_doc())
        self.assertEqual(code, 0, out)
        self.assertIn("THREE_SIDE_GATE_PASS", out)
        self.assertIn("DECLARED_ONLY", out)

    def test_missing_side(self) -> None:
        doc = base_doc()
        doc["oh_side"] = []
        code, out = self.run_gate(doc)
        self.assertEqual(code, 1, out)
        self.assertIn("SIDE_EMPTY oh_side", out)

    def test_anchor_path_missing(self) -> None:
        doc = base_doc()
        doc["android_side"][0]["ref"] = "docs/nonexistent.md"
        code, out = self.run_gate(doc)
        self.assertEqual(code, 1, out)
        self.assertIn("ANCHOR_PATH_MISSING android_side", out)

    def test_broken_transition_target(self) -> None:
        (self.root / "sm" / "strategy.scxml").write_text(
            BROKEN_SCXML, encoding="utf-8")
        code, out = self.run_gate(base_doc())
        self.assertEqual(code, 1, out)
        self.assertIn("SM_TARGET_UNDEFINED", out)

    def test_unreachable_state(self) -> None:
        (self.root / "sm" / "strategy.scxml").write_text(
            UNREACHABLE_SCXML, encoding="utf-8")
        code, out = self.run_gate(base_doc())
        self.assertEqual(code, 1, out)
        self.assertIn("SM_UNREACHABLE", out)
        self.assertIn("S_ORPHAN", out)

    def test_dead_end(self) -> None:
        (self.root / "sm" / "strategy.scxml").write_text(
            DEAD_END_SCXML, encoding="utf-8")
        doc = base_doc()
        doc["ours"]["target_state"] = "S_STUCK"
        code, out = self.run_gate(doc)
        self.assertEqual(code, 1, out)
        self.assertIn("SM_DEAD_END", out)

    def test_dead_end_waived_by_terminal_ok(self) -> None:
        (self.root / "sm" / "strategy.scxml").write_text(
            DEAD_END_SCXML, encoding="utf-8")
        doc = base_doc()
        doc["ours"]["target_state"] = "S_STUCK"
        doc["terminal_ok"] = ["S_STUCK"]
        code, out = self.run_gate(doc)
        self.assertEqual(code, 0, out)

    def test_advancement_no_path(self) -> None:
        doc = base_doc()
        doc["ours"]["current_state"] = "S_DONE"
        doc["ours"]["target_state"] = "S_A"
        code, out = self.run_gate(doc)
        self.assertEqual(code, 1, out)
        self.assertIn("ADV_NO_PATH", out)

    def test_advancement_unknown_state(self) -> None:
        doc = base_doc()
        doc["ours"]["target_state"] = "S_MADE_UP"
        code, out = self.run_gate(doc)
        self.assertEqual(code, 1, out)
        self.assertIn("ADV_STATE_UNKNOWN", out)

    def test_self_verification_rejected(self) -> None:
        doc = base_doc()
        doc["verification"]["verifier"] = "agent-impl"
        code, out = self.run_gate(doc)
        self.assertEqual(code, 1, out)
        self.assertIn("VERIFY_SELF", out)

    def test_missing_receipt(self) -> None:
        doc = base_doc()
        doc["verification"]["receipt"] = "var/evidence/absent.md"
        code, out = self.run_gate(doc)
        self.assertEqual(code, 1, out)
        self.assertIn("VERIFY_RECEIPT_MISSING", out)

    def test_verdict_not_pass(self) -> None:
        doc = base_doc()
        doc["verification"]["verdict"] = "FAIL"
        code, out = self.run_gate(doc)
        self.assertEqual(code, 1, out)
        self.assertIn("VERIFY_NOT_PASS", out)

    def test_file_missing(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root),
             "--feature", "specs/none"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FILE_MISSING", proc.stdout)

    def test_schema_mismatch(self) -> None:
        doc = base_doc()
        doc["schema"] = "wrong.v9"
        file = self.root / "three-side.yaml"
        file.write_text(yaml.safe_dump(doc), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root),
             "--file", str(file)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_real_repo_machine_closure(self) -> None:
        """真仓状态机烟囱测试:Fn02 android.scxml 应通过闭合检查。"""
        repo = Path(__file__).resolve().parent.parent
        real = repo / "docs/spec/concepts/Fn02/state-machines/android.scxml"
        if not real.exists():
            self.skipTest("real machine unavailable in this checkout")
        (self.root / "sm" / "strategy.scxml").write_text(
            real.read_text(encoding="utf-8"), encoding="utf-8")
        doc = base_doc()
        doc["ours"]["current_state"] = "A_PROC_ABSENT"
        doc["ours"]["target_state"] = "A_PROC_SPECIALIZED"
        code, out = self.run_gate(doc)
        self.assertEqual(code, 0, out)

    _ = copy  # 保留 import 以备扩展 fixture


if __name__ == "__main__":
    unittest.main(verbosity=2)
