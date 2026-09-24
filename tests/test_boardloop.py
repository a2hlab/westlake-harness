"""Known-answer tests for the board loop: no board required, log fixtures only.

Three launch archetypes, each recorded from a real outcome class the loop must distinguish:
a process crash before any UI, a stall after the first Activity, and a clean run to P4b.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from boardloop import blockers, runner, stages

# --- fixtures: condensed from real adapter_child logs of each outcome class --------------------

CRASH_LOG = """\
I/appspawn-x: side-channels started
I/WestlakeRuntime: kRegJNI loop done
I/WestlakeRuntime: sBindAppDone=true
E/AndroidRuntime: FATAL EXCEPTION: main
E/AndroidRuntime: java.lang.RuntimeException: Unable to start activity ComponentInfo{com.crashy/com.crashy.MainActivity}: java.lang.NullPointerException
"""

CRASH_FAULTLOG = """\
Pid: 12345
Signal: SIGSEGV
Reason: 'null pointer dereference'
"""

STALL_LOG = """\
I/appspawn-x: side-channels started
I/WestlakeRuntime: kRegJNI loop done
I/WestlakeRuntime: sBindAppDone=true
W/ActivityTaskManager: Unable to start activity ComponentInfo{com.stally/com.stally.MainActivity}: android.content.ActivityNotFoundException
"""

GOOD_LOG = """\
I/appspawn-x: side-channels started
I/WestlakeRuntime: kRegJNI loop done
I/WestlakeRuntime: sBindAppDone=true
I/ViewRootImpl: DecorView added for com.goody.MainActivity
I/OH_InputBridge: VT com.goody.MainActivity rect=[0,0 1080x2400] text="Welcome" clickable=false
I/OH_InputBridge: VT Button rect=[100,200 400x300] id=ok text="OK" clickable=true
I/WestlakeWSA: OH_WSA-relayout 1080x2400
"""

GOOD_VIEW_TREE = [
    "com.goody.MainActivity rect=[0,0 1080x2400] text=\"Welcome\" clickable=false",
    "Button rect=[100,200 400x300] id=ok text=\"OK\" clickable=true",
]

GAP_MAP = {
    "rows": [
        {"category": "app-framework", "id": "af:start-activity",
         "item": "start activity: NullPointerException"},
        {"category": "system-services", "id": "ss:wifi-null",
         "item": "WifiManager.getConnectionInfo on null service"},
    ],
}


class TestStages(unittest.TestCase):
    """P2/P3/P4a/P4b, each judged by its own oracle."""

    def test_crash_before_activity(self) -> None:
        verdict = stages.judge(CRASH_LOG, view_tree=[], rs_visible_nodes=0)
        self.assertEqual(verdict["P2"], stages.PASS)   # bound before it died
        self.assertEqual(verdict["P3"], stages.FAIL)   # activity start failed
        self.assertEqual(verdict["P4a"], stages.FAIL)  # no laid-out widgets
        self.assertEqual(verdict["P4b"], stages.FAIL)  # no visible RS nodes

    def test_stall_after_first_activity(self) -> None:
        verdict = stages.judge(STALL_LOG, view_tree=[], rs_visible_nodes=0)
        self.assertEqual(verdict["P2"], stages.PASS)
        self.assertEqual(verdict["P3"], stages.FAIL)
        self.assertEqual(verdict["P4a"], stages.FAIL)
        self.assertEqual(verdict["P4b"], stages.FAIL)

    def test_clean_run_to_p4b(self) -> None:
        verdict = stages.judge(GOOD_LOG, view_tree=GOOD_VIEW_TREE, rs_visible_nodes=3)
        self.assertEqual(verdict, {"P2": "pass", "P3": "pass", "P4a": "pass", "P4b": "pass"})

    def test_oracle_unavailable_is_not_fail(self) -> None:
        verdict = stages.judge(GOOD_LOG, view_tree=None, rs_visible_nodes=None)
        self.assertEqual(verdict["P4a"], stages.ORACLE_UNAVAILABLE)
        self.assertEqual(verdict["P4b"], stages.ORACLE_UNAVAILABLE)

    def test_view_tree_needs_real_geometry(self) -> None:
        self.assertEqual(stages.p4a(["Loading rect=[0,0 0x0]"]), stages.FAIL)
        self.assertEqual(stages.p4a(GOOD_VIEW_TREE), stages.PASS)


class TestFirstBlocker(unittest.TestCase):
    """First uncaught exception / native crash, mapped to a gap-map row id."""

    def test_process_crash_maps_to_row(self) -> None:
        result = blockers.classify(CRASH_LOG, "", GAP_MAP)
        self.assertEqual(result["source"], "child-log")
        self.assertEqual(result["category"], "app-framework")
        self.assertEqual(result["gap_row"], "af:start-activity")

    def test_faultlog_only_native_crash(self) -> None:
        result = blockers.classify("I/WestlakeRuntime: sBindAppDone=true\n", CRASH_FAULTLOG, GAP_MAP)
        self.assertEqual(result["source"], "faultlog")
        self.assertEqual(result["category"], "native-fault")
        self.assertEqual(result["gap_row"], "unmapped")  # no native-fault row in this map

    def test_unmapped_blocker_is_recorded_not_forced(self) -> None:
        log = "E/x: Error relocating libfoo.so: imaginary_symbol: symbol not found\n"
        result = blockers.classify(log, "", GAP_MAP)
        self.assertEqual(result["category"], "native-symbols")
        self.assertEqual(result["gap_row"], "unmapped")

    def test_no_blocker(self) -> None:
        result = blockers.classify(GOOD_LOG, "", GAP_MAP)
        self.assertIsNone(result["category"])
        self.assertIsNone(result["gap_row"])


class TestRunner(unittest.TestCase):
    """Launcher plumbing: commands, records, and --dry-run."""

    def _args(self, tmp: Path, dry_run: bool = True):
        corpus = tmp / "corpus.json"
        apk = tmp / "app.apk"
        apk.write_bytes(b"fixture-bytes")
        corpus.write_text(json.dumps({"apps": {
            "fixy": {"input": str(apk), "package": "com.fixy", "version": "1.0"},
        }}))
        argv = [
            "--corpus", str(corpus), "--manifest", str(tmp / "manifest"),
            "--workspace", str(tmp), "--westlake-source", str(tmp),
            "--framework-report", str(tmp / "device-report.json"),
            "--hdc", "hdc", "--serials", "SERIAL1", "SERIAL2",
            "--runs", str(tmp / "runs"), "--run-id", "test-run",
        ]
        if dry_run:
            argv.append("--dry-run")
        return argv

    def test_dry_run_prints_commands_without_a_device(self) -> None:
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as td:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = runner.main(self._args(Path(td)))
            self.assertEqual(rc, 0)
            text = out.getvalue()
            self.assertIn("probe_source_app.py", text)
            self.assertIn("--serial SERIAL1", text)
            self.assertIn("dry-run", text)

    def test_view_tree_parsing(self) -> None:
        lines = ["noise line", "Button rect=[1,2 3x4] id=ok", "VT another rect=[0,0 9x9]"]
        self.assertEqual(runner.view_tree_from_log(lines), lines[1:])

    def test_summary_table(self) -> None:
        results = [{"app": "fixy", "verdict": "done",
                    "stages": {"P2": "pass", "P3": "pass", "P4a": "fail", "P4b": "fail"},
                    "first_blocker": {"gap_row": "af:start-activity"}}]
        table = runner.summarize(results)
        self.assertIn("fixy", table)
        self.assertIn("af:start-activity", table)


if __name__ == "__main__":
    unittest.main()
