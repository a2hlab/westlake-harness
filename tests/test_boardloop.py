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

    def _args(self, tmp: Path, dry_run: bool = True, prepared: bool = True):
        corpus = tmp / "corpus.json"
        apk = tmp / "app.apk"
        apk.write_bytes(b"fixture-bytes")
        corpus.write_text(json.dumps({"apps": {
            "fixy": {"input": str(apk), "package": "com.fixy", "version": "1.0"},
        }}))
        prepared_root = tmp / "app-inputs"
        if prepared:
            (prepared_root / "fixy").mkdir(parents=True)
            (prepared_root / "fixy" / "app-input.json").write_text("{}")
        argv = [
            "--corpus", str(corpus), "--manifest", str(tmp / "manifest"),
            "--workspace", str(tmp), "--westlake-source", str(tmp),
            "--framework-report", str(tmp / "device-report.json"),
            "--hdc", "hdc", "--prepared-root", str(prepared_root),
            "--serials", "SERIAL1", "SERIAL2",
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
            self.assertIn("--app-input", text)
            self.assertIn("fixy", text)
            self.assertIn("dry-run", text)

    def test_dry_run_points_at_the_prepared_directory(self) -> None:
        """--app-input must be the prepare_app.py output dir, not the raw APK path."""
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            out = io.StringIO()
            with redirect_stdout(out):
                runner.main(self._args(tmp))
            command = next(line for line in out.getvalue().splitlines()
                           if "--app-input " in line)
            app_input = command.split("--app-input ")[1].split(" ")[0]
            self.assertEqual(app_input, str(tmp / "app-inputs" / "fixy"))
            self.assertNotIn("app.apk", app_input)

    def test_missing_prepared_directory_is_an_error_not_a_launch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            argv = self._args(tmp, prepared=False)
            import io
            from contextlib import redirect_stderr, redirect_stdout
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = runner.main(argv)
            self.assertEqual(rc, 1)  # pre-flight refusal, not a launch

    def test_preflight_lists_all_missing_before_any_launch(self) -> None:
        """Two missing prepare dirs: both named in one refusal, zero launches."""
        import io
        from contextlib import redirect_stderr, redirect_stdout
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corpus = tmp / "corpus.json"
            apk = tmp / "app.apk"
            apk.write_bytes(b"fixture-bytes")
            corpus.write_text(json.dumps({"apps": {
                "gone1": {"input": str(apk), "package": "com.g1"},
                "here": {"input": str(apk), "package": "com.h"},
                "gone2": {"input": str(apk), "package": "com.g2"},
            }}))
            prepared_root = tmp / "app-inputs"
            (prepared_root / "here").mkdir(parents=True)
            (prepared_root / "here" / "app-input.json").write_text("{}")
            argv = [
                "--corpus", str(corpus), "--manifest", str(tmp / "manifest"),
                "--workspace", str(tmp), "--westlake-source", str(tmp),
                "--framework-report", str(tmp / "device-report.json"),
                "--hdc", "hdc", "--prepared-root", str(prepared_root),
                "--serials", "SERIAL1", "--runs", str(tmp / "runs"),
                "--run-id", "preflight", "--dry-run",
            ]
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = runner.main(argv)
            self.assertEqual(rc, 1)
            self.assertIn("gone1", err.getvalue())
            self.assertIn("gone2", err.getvalue())
            self.assertNotIn("here: no prepared", err.getvalue())
            # no launch command was printed for any app
            self.assertNotIn("probe_source_app.py", out.getvalue())

    def test_dry_run_shows_cleanup_commands(self) -> None:
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as td:
            out = io.StringIO()
            with redirect_stdout(out):
                runner.main(self._args(Path(td)))
            # cleanup is recorded per app; on dry-run nothing is executed
            run_json = Path(td) / "runs" / "test-run" / "fixy.json"
            self.assertFalse(run_json.exists())  # dry-run writes no records
            self.assertEqual(runner.cleanup_commands("hdc", "S1", "com.fixy", None, None),
                             [["hdc", "-t", "S1", "shell",
                               "kill -9 $(pidof com.fixy) 2>/dev/null"]])
            with_pids = runner.cleanup_commands("hdc", "S1", "com.fixy", 4321, 4000)
            # child first, then parent, pidof fallback last
            self.assertEqual(with_pids[0], ["hdc", "-t", "S1", "shell",
                                            "kill -9 4321 2>/dev/null"])
            self.assertEqual(with_pids[1], ["hdc", "-t", "S1", "shell",
                                            "kill -9 4000 2>/dev/null"])
            self.assertIn("pidof com.fixy", with_pids[2][-1])

    def test_worker_survives_timeout_and_records_every_app(self) -> None:
        """One worker, three apps, the first raises TimeoutExpired: three records."""
        import argparse
        import queue
        import subprocess
        import threading
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ns = argparse.Namespace(
                manifest=tmp, workspace=tmp, westlake_source=tmp,
                framework_report=tmp / "r.json", hdc="hdc",
                prepared_root=tmp / "app-inputs", runtime_lock=None, gap_map=None,
                runs=tmp / "runs", launch_timeout=1, vt_wait=0, dry_run=False,
            )
            (tmp / "app-inputs").mkdir()
            jobs: queue.Queue = queue.Queue()
            apps = {}
            for name in ("one", "two", "three"):
                (tmp / "app-inputs" / name).mkdir()
                (tmp / "app-inputs" / name / "app-input.json").write_text("{}")
                apk = tmp / f"{name}.apk"
                apk.write_bytes(name.encode())
                apps[name] = {"input": str(apk), "package": f"com.{name}"}
                jobs.put((name, apps[name]))
            results: list = []
            run_dir = tmp / "runs" / "t1"
            run_dir.mkdir(parents=True)
            # Content-based dispatch: per-app call counts vary (wake/foreground/cleanup),
            # so a fixed list would silently break on any runner change. The first app's
            # launch times out; the other two fail the launch; everything else succeeds.
            launches = iter(["one", "two", "three"])
            def dispatch(cmd, *a, **k):
                joined = " ".join(str(c) for c in cmd)
                if "probe_source_app.py" in joined:
                    if next(launches) == "one":
                        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)
                    return subprocess.CompletedProcess(args=cmd, returncode=1,
                                                       stdout="", stderr="bad")
                return subprocess.CompletedProcess(args=cmd, returncode=0,
                                                   stdout="", stderr="")
            with mock.patch("subprocess.run", side_effect=dispatch):
                runner._worker(ns, "S1", jobs, run_dir, "t1", results, threading.Lock())
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]["verdict"], "launch-timeout")
            self.assertEqual(results[1]["verdict"], "launch-failed")
            self.assertEqual(results[2]["verdict"], "launch-failed")
            summary = runner.summarize(results)
            self.assertIn("total 3", summary)
            self.assertIn("launch-timeout=1", summary)
            self.assertIn("launch-failed=2", summary)
            for name in ("one", "two", "three"):
                self.assertTrue((run_dir / f"{name}.json").exists())


# --- real-board fixtures recorded by the outer loop (toutiao, drive 1) --------------------------

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_LOG = (FIXTURES / "toutiao-drive-1.child.stderr").read_text(errors="replace")
FIXTURE_REPORT = json.loads((FIXTURES / "toutiao-drive-1.device-report.json").read_text())


class TestTapChannelBothNames(unittest.TestCase):
    """scan1 defect: the source-closure board watches the bare namespace symlink, not
    noice_tap.<pid>; the 'v' dump must go to both names so either layout answers."""

    def test_done_run_writes_both_tap_channel_names(self) -> None:
        import argparse
        import subprocess
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ns = argparse.Namespace(
                manifest=tmp, workspace=tmp, westlake_source=tmp,
                framework_report=tmp / "r.json", hdc="hdc",
                prepared_root=tmp / "app-inputs", runtime_lock=None, gap_map=None,
                runs=tmp / "runs", launch_timeout=1, vt_wait=0, dry_run=False,
                webview_input=None,
            )
            (tmp / "app-inputs" / "appx").mkdir(parents=True)
            (tmp / "app-inputs" / "appx" / "app-input.json").write_text("{}")
            apk = tmp / "appx.apk"
            apk.write_bytes(b"appx")
            app = {"input": str(apk), "package": "com.appx"}
            calls: list[str] = []

            def fake_run(cmd, *a, **k):
                joined = " ".join(str(c) for c in cmd)
                calls.append(joined)
                if "probe_source_app.py" in joined:
                    out = Path(cmd[-1])
                    out.mkdir(parents=True, exist_ok=True)
                    (out / "device-report.json").write_text(
                        '{"child": 4321, "parent": 4000, "runtime": "/rt"}')
                    return subprocess.CompletedProcess(args=cmd, returncode=0,
                                                       stdout="", stderr="")
                if "adapter_child" in joined or "faultlog" in joined:
                    # child log: a laid-out view tree in the current 'VT ' format
                    return subprocess.CompletedProcess(
                        args=cmd, returncode=0,
                        stdout="VT DecorView id=- rect=[0,0 1200x1790] c=0\n"
                               "VT Button id=ok rect=[100,200 400x300] c=1\n",
                        stderr="")
                return subprocess.CompletedProcess(args=cmd, returncode=0,
                                                   stdout="", stderr="")

            with mock.patch("subprocess.run", side_effect=fake_run):
                record = runner.run_app(ns, "appx", app, "S1", tmp / "runs", "rid")
            self.assertEqual(record["verdict"], "done")
            self.assertEqual(record["stages"]["P4a"], "pass")  # the scan1 failure mode
            bare = [c for c in calls if "echo v > /data/local/tmp/noice_tap 2>/dev/null" in c]
            per_pid = [c for c in calls if "echo v > /data/local/tmp/noice_tap.4321" in c]
            self.assertTrue(bare, "bare namespace symlink never got the 'v' dump")
            self.assertTrue(per_pid, "per-pid fallback never got the 'v' dump")

    def test_webview_input_flows_into_the_command(self) -> None:
        import argparse
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            prepared = Path(td) / "app-inputs"
            (prepared / "k").mkdir(parents=True)
            (prepared / "k" / "app-input.json").write_text("{}")
            ns = argparse.Namespace(
                manifest=Path(td), workspace=Path(td), westlake_source=Path(td),
                framework_report=Path(td) / "r.json", hdc="hdc",
                prepared_root=prepared, webview_input=Path(td) / "wv",
            )
            command = runner.launch_command(ns, "k", {"extra_args": []}, "S1", Path("/o"))
            self.assertIn("--webview-input " + str(ns.webview_input), " ".join(command))
            ns.webview_input = None
            command = runner.launch_command(ns, "k", {"extra_args": []}, "S1", Path("/o"))
            self.assertNotIn("--webview-input", " ".join(command))


class TestRealBoardAdaptation(unittest.TestCase):
    """#9: log path from the report's runtime, dual-era VT parsing, keep-alive commands."""

    def test_child_log_candidates_prefer_private_tmp_from_runtime(self) -> None:
        """① the private-tmp path is derived from the report's runtime, legacy kept as fallback."""
        runtime = FIXTURE_REPORT["runtime"]
        child = FIXTURE_REPORT["child"]
        candidates = runner.child_log_candidates(child, runtime)
        self.assertEqual(candidates[0],
                         f"{runtime}/private-tmp/adapter_child_{child}.stderr")
        self.assertEqual(candidates[1],
                         f"/data/service/el1/public/appspawnx/adapter_child_{child}.stderr")
        # no runtime -> legacy only
        self.assertEqual(runner.child_log_candidates(child, None),
                         [f"/data/service/el1/public/appspawnx/adapter_child_{child}.stderr"])

    def test_view_tree_parses_consent_dialog_from_real_fixture(self) -> None:
        """② the consent dialog root and the 「同意」 ip4 row's rect parse out of the new format."""
        tree = runner.view_tree_from_log(FIXTURE_LOG.splitlines())
        # the consent dialog's root container is the DecorView at the top of the dump
        self.assertTrue(any("DecorView" in line and "rect=[0,0 1200x1790]" in line
                            for line in tree))
        ip4 = next(line for line in tree if "id=ip4 " in line)
        self.assertIn("rect=[294,1158 612x99]", ip4)
        agree = next(line for line in tree if '"同意"' in line)
        self.assertIn("rect=[564,1183 72x49]", agree)

    def test_p2_passes_on_real_fixture(self) -> None:
        """③ the fixture's `sBindAppDone=true` carries P2."""
        self.assertEqual(stages.p2(FIXTURE_LOG), stages.PASS)

    def test_dry_run_lists_wake_and_foreground_commands(self) -> None:
        """④ dry-run shows wake/keep-alive before each app and `aa start` after the launch."""
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corpus = tmp / "corpus.json"
            apk = tmp / "app.apk"
            apk.write_bytes(b"fixture-bytes")
            corpus.write_text(json.dumps({"apps": {
                "fixy": {"input": str(apk), "package": "com.fixy"},
            }}))
            (tmp / "app-inputs" / "fixy").mkdir(parents=True)
            (tmp / "app-inputs" / "fixy" / "app-input.json").write_text("{}")
            argv = [
                "--corpus", str(corpus), "--manifest", str(tmp / "manifest"),
                "--workspace", str(tmp), "--westlake-source", str(tmp),
                "--framework-report", str(tmp / "device-report.json"),
                "--hdc", "hdc", "--prepared-root", str(tmp / "app-inputs"),
                "--serials", "S1", "--runs", str(tmp / "runs"),
                "--run-id", "wake", "--dry-run",
            ]
            out = io.StringIO()
            with redirect_stdout(out):
                runner.main(argv)
            text = out.getvalue()
            self.assertIn("power-shell wakeup", text)
            self.assertIn("power-shell timeout -o 86400000", text)
            self.assertIn("aa start -b org.westlake.imehost -a EntryAbility", text)

    def test_failed_and_error_records_carry_cleanup(self) -> None:
        """⑤ launch-failed and runner-error records both carry the cleanup field."""
        import argparse
        import subprocess
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ns = argparse.Namespace(
                manifest=tmp, workspace=tmp, westlake_source=tmp,
                framework_report=tmp / "r.json", hdc="hdc",
                prepared_root=tmp / "app-inputs", runtime_lock=None, gap_map=None,
                runs=tmp / "runs", launch_timeout=1, vt_wait=0, dry_run=False,
            )
            (tmp / "app-inputs" / "appx").mkdir(parents=True)
            (tmp / "app-inputs" / "appx" / "app-input.json").write_text("{}")
            apk = tmp / "appx.apk"
            apk.write_bytes(b"appx")
            app = {"input": str(apk), "package": "com.appx"}

            def launch_failed(cmd, *a, **k):
                if "probe_source_app.py" in " ".join(str(c) for c in cmd):
                    return subprocess.CompletedProcess(args=cmd, returncode=1,
                                                       stdout="", stderr="boom")
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

            with mock.patch("subprocess.run", side_effect=launch_failed):
                record = runner.run_app(ns, "appx", app, "S1", tmp / "runs", "rid")
            self.assertEqual(record["verdict"], "launch-failed")
            self.assertIn("cleanup", record)
            self.assertTrue(any("pidof com.appx" in e["command"]
                                for e in record["cleanup"]))

            def evidence_blows_up(cmd, *a, **k):
                joined = " ".join(str(c) for c in cmd)
                if "probe_source_app.py" in joined:
                    out = Path(cmd[-1])
                    out.mkdir(parents=True, exist_ok=True)
                    (out / "device-report.json").write_text('{"child": 1, "parent": 2}')
                    return subprocess.CompletedProcess(args=cmd, returncode=0,
                                                       stdout="", stderr="")
                if "kill -9" in joined or "power-shell" in joined or "aa start" in joined \
                        or "uinput" in joined:
                    return subprocess.CompletedProcess(args=cmd, returncode=0,
                                                       stdout="", stderr="")
                raise OSError("hdc transport died")

            with mock.patch("subprocess.run", side_effect=evidence_blows_up):
                record = runner.run_app(ns, "appx", app, "S1", tmp / "runs", "rid")
            self.assertEqual(record["verdict"], "runner-error")
            self.assertIn("OSError", record["detail"])
            self.assertIn("cleanup", record)
            self.assertTrue(any("kill -9 1" in e["command"] for e in record["cleanup"]))


class TestCleanupEveryExit(unittest.TestCase):
    """#7: every run_app exit cleans up by report pids, after evidence collection."""

    def _ns(self, tmp: Path) -> "argparse.Namespace":
        import argparse
        return argparse.Namespace(
            manifest=tmp, workspace=tmp, westlake_source=tmp,
            framework_report=tmp / "r.json", hdc="hdc",
            prepared_root=tmp / "app-inputs", runtime_lock=None, gap_map=None,
            runs=tmp / "runs", launch_timeout=1, vt_wait=0, dry_run=False,
        )

    def _app(self, tmp: Path, name: str = "appx") -> dict:
        (tmp / "app-inputs" / name).mkdir(parents=True, exist_ok=True)
        (tmp / "app-inputs" / name / "app-input.json").write_text("{}")
        apk = tmp / f"{name}.apk"
        apk.write_bytes(name.encode())
        return {"input": str(apk), "package": f"com.{name}"}

    def _run(self, ns, app, tmp, report, device_side):
        """Drive run_app with subprocess.run mocked: the launch writes the report,
        hdc shell calls answer from device_side, and every call is recorded in order."""
        import json as _json
        import subprocess
        from unittest import mock
        calls: list[list[str]] = []

        def fake_run(cmd, *a, **k):
            calls.append([str(c) for c in cmd])
            joined = " ".join(str(c) for c in cmd)
            if "probe_source_app.py" in joined:
                out = Path(cmd[-1])
                out.mkdir(parents=True, exist_ok=True)
                if report is not None:
                    (out / "device-report.json").write_text(_json.dumps(report))
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
            for marker, reply in device_side.items():
                if marker in joined:
                    return subprocess.CompletedProcess(args=cmd, returncode=0,
                                                       stdout=reply, stderr="")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        with mock.patch("subprocess.run", side_effect=fake_run):
            record = runner.run_app(ns, "appx", app, "S1", tmp / "runs", "rid")
        return record, calls

    def test_done_run_cleans_up_after_evidence_by_report_pids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ns = self._ns(tmp)
            app = self._app(tmp)
            device_side = {
                "adapter_child": GOOD_LOG,
                "hidumper": "node com.appx Visible: 1\n",
            }
            record, calls = self._run(ns, app, tmp,
                                      {"child": 4321, "parent": 4000}, device_side)
            self.assertEqual(record["verdict"], "done")
            self.assertEqual(record["stages"]["P4b"], "pass")
            kills = [c for c in calls if "kill -9" in " ".join(c)]
            self.assertEqual(len(kills), 3)  # child pid, parent pid, pidof fallback
            self.assertIn("kill -9 4321", " ".join(kills[0]))
            self.assertIn("kill -9 4000", " ".join(kills[1]))
            self.assertIn("pidof com.appx", " ".join(kills[2]))
            # cleanup comes AFTER all evidence collection (log/vt/RS/faultlog reads)
            first_kill = calls.index(kills[0])
            evidence = [i for i, c in enumerate(calls)
                        if any(m in " ".join(c) for m in
                               ("adapter_child", "noice_tap", "hidumper", "faultlog"))]
            self.assertTrue(all(i < first_kill for i in evidence))
            self.assertEqual([e["rc"] for e in record["cleanup"]], [0, 0, 0])

    def test_timeout_with_parent_only_report_cleans_parent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ns = self._ns(tmp)
            app = self._app(tmp)
            import subprocess
            from unittest import mock
            calls: list[list[str]] = []

            def fake_run(cmd, *a, **k):
                calls.append([str(c) for c in cmd])
                joined = " ".join(str(c) for c in cmd)
                if "probe_source_app.py" in joined:
                    out = Path(cmd[-1])
                    out.mkdir(parents=True, exist_ok=True)
                    (out / "device-report.json").write_text('{"parent": 4000}')
                    raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

            with mock.patch("subprocess.run", side_effect=fake_run):
                record = runner.run_app(ns, "appx", app, "S1", tmp / "runs", "rid")
            self.assertEqual(record["verdict"], "launch-timeout")
            kills = [" ".join(c) for c in calls if "kill -9" in " ".join(c)]
            self.assertEqual(len(kills), 2)  # parent pid + pidof fallback; no child
            self.assertIn("kill -9 4000", kills[0])
            self.assertIn("pidof com.appx", kills[1])

    def test_no_report_falls_back_to_pidof_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ns = self._ns(tmp)
            app = self._app(tmp)
            record, calls = self._run(ns, app, tmp, report=None, device_side={})
            # launch "succeeded" (rc 0) but wrote no report -> launch-failed
            self.assertEqual(record["verdict"], "launch-failed")
            kills = [" ".join(c) for c in calls if "kill -9" in " ".join(c)]
            self.assertEqual(len(kills), 1)
            self.assertIn("pidof com.appx", kills[0])

    def test_exception_mid_collection_still_cleans_up(self) -> None:
        """#9 changed the contract: the exception is caught inside run_app and returned as
        runner-error, but the finally still cleans up by the report's pids."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            ns = self._ns(tmp)
            app = self._app(tmp)
            import subprocess
            from unittest import mock
            calls: list[list[str]] = []

            def fake_run(cmd, *a, **k):
                calls.append([str(c) for c in cmd])
                joined = " ".join(str(c) for c in cmd)
                if "probe_source_app.py" in joined:
                    out = Path(cmd[-1])
                    out.mkdir(parents=True, exist_ok=True)
                    (out / "device-report.json").write_text('{"child": 4321, "parent": 4000}')
                    return subprocess.CompletedProcess(args=cmd, returncode=0,
                                                       stdout="", stderr="")
                if any(m in joined for m in ("kill -9", "power-shell", "aa start", "uinput")):
                    return subprocess.CompletedProcess(args=cmd, returncode=0,
                                                       stdout="", stderr="")
                raise OSError("hdc transport died")  # evidence collection blows up

            with mock.patch("subprocess.run", side_effect=fake_run):
                record = runner.run_app(ns, "appx", app, "S1", tmp / "runs", "rid")
            self.assertEqual(record["verdict"], "runner-error")
            kills = [" ".join(c) for c in calls if "kill -9" in " ".join(c)]
            self.assertEqual(len(kills), 3)  # cleanup ran despite the exception
            self.assertIn("kill -9 4321", kills[0])
            self.assertIn("kill -9 4000", kills[1])
            self.assertTrue(any("pidof com.appx" in k for k in kills))

    def test_extra_args_flow_into_the_launch_command(self) -> None:
        """Per-app probe flags from the corpus entry reach the command verbatim."""
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corpus = tmp / "corpus.json"
            apk = tmp / "app.apk"
            apk.write_bytes(b"fixture-bytes")
            corpus.write_text(json.dumps({"apps": {
                "toutiao": {"input": str(apk), "package": "com.ss.android.article.news",
                            "extra_args": ["--android-native-target", "libvision_core.so",
                                           "--android-native-target", "libc++_shared.so"]},
            }}))
            prepared_root = tmp / "app-inputs"
            (prepared_root / "toutiao").mkdir(parents=True)
            (prepared_root / "toutiao" / "app-input.json").write_text("{}")
            argv = [
                "--corpus", str(corpus), "--manifest", str(tmp / "manifest"),
                "--workspace", str(tmp), "--westlake-source", str(tmp),
                "--framework-report", str(tmp / "device-report.json"),
                "--hdc", "hdc", "--prepared-root", str(prepared_root),
                "--serials", "S1", "--runs", str(tmp / "runs"),
                "--run-id", "extra-args", "--dry-run",
            ]
            out = io.StringIO()
            with redirect_stdout(out):
                rc = runner.main(argv)
            self.assertEqual(rc, 0)
            command = next(line for line in out.getvalue().splitlines()
                           if "--app-input " in line)
            self.assertIn("--android-native-target libvision_core.so", command)
            self.assertIn("--android-native-target libc++_shared.so", command)

    def test_extra_args_reject_non_strings(self) -> None:
        with self.assertRaises(ValueError):
            runner.extra_args({"extra_args": ["--ok", 42]})

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
