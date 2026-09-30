import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts/lab"))
import first_fatal as fatal


def event(message, number=1, pid=123, tid=456, tag="AppSpawnXJava"):
    return fatal.classify.parse(f"10-01 04:30:00.000 {pid} {tid} I C00f00/{tag}: {message}", number)


class KnownAnswerTests(unittest.TestCase):
    def test_five_real_runs(self):
        paths = sorted((HERE / "evidence/first-fatal").glob("*.json"))
        self.assertEqual(5, len(paths))
        for path in paths:
            with self.subTest(path=path.name):
                fixture = json.loads(path.read_text())
                events = [fatal.classify.parse(text, number) for number, text in fixture["lines"]]
                result = fatal.analyze(events, set(fixture["pids"]), fixture["reports"], fixture["disappeared"])
                expected = fixture["expected"]
                self.assertEqual(expected["kind"], result["terminal"]["kind"])
                self.assertEqual(expected["terminal_line"], result["terminal"]["event"]["line"])
                root = result["root"]
                self.assertIn(expected["root_needle"], json.dumps([root.get("event"), root["frames"]]))
                if fixture["key"] == "wikipedia":
                    self.assertIn("IncompatibleClassChangeError", root["event"]["message"])
                    self.assertNotIn("DiagnosticCoroutineContextException", root["event"]["message"])
                if fixture["key"] == "mcdonalds":
                    self.assertIn("SplashActivity", result["terminal"]["event"]["message"])
                    self.assertNotIn("libz.so", root["event"]["message"])
                if fixture["key"] == "burgerking":
                    self.assertNotIn("Datadog", root["event"]["message"])
                self.assertEqual(64, len(fixture["source"]["hilog_sha256"]))


class BoundaryTests(unittest.TestCase):
    def test_diagnostic_signals_and_caught_errors_are_not_terminal(self):
        events = [event(f"DFX_SignalHandler :: signo({number})", number=number, tag="DfxSignalHandler") for number in [42, 35, 4]]
        events += [event("java.lang.IllegalStateException: caught SDK error", number=50),
                   event("FATAL EXCEPTION: foreign", number=51, pid=999)]
        self.assertEqual("no-observed-termination", fatal.analyze(events, {123})["status"])
        self.assertIsNone(fatal.terminal_kind(event("at java.lang.System.exit(System.java:1)")))
        self.assertIsNone(fatal.terminal_kind(event("[class_linker.cc:1] FATAL EXCEPTION: metadata")))

    def test_adjacent_same_thread_and_boundary(self):
        root = event("java.lang.IllegalStateException: target", number=2)
        stop = event("System.exit called, status: 1", number=4)
        foreign = event("java.lang.RuntimeException: other", number=3, tid=999)
        self.assertEqual(root, fatal.analyze([root, foreign, stop], {123})["root"]["event"])
        boundary = event("business operation continued successfully", number=3)
        self.assertEqual("unknown", fatal.analyze([root, boundary, stop], {123})["root"]["status"])

    def test_noise_only_trims_context_not_terminal_or_root(self):
        root = event("java.lang.IllegalStateException: target", number=1)
        stop = event("System.exit called, status: 1", number=2)
        registry = dict(context={"generation": "test"}, signatures=[dict(id="bad", signature=fatal.benign.signature(item),
                        distinct_app_count=4, enabled_for_triage=True) for item in [root, stop]])
        result = fatal.analyze([root, stop], {123}, registry=registry, context=registry["context"])
        self.assertEqual(stop, result["terminal"]["event"])
        self.assertEqual(root, result["root"]["event"])
        self.assertIn(stop, result["context"])

    def test_signal_report_requires_subject_pid_tid_and_time(self):
        stop = event("DFX_SignalHandler :: signo(11)", tag="DfxSignalHandler")
        lines = ["Timestamp:2026-10-01 04:30:00.000", "Pid:123", "Fault thread info:", "Tid:456, Name:raster",
                 "#00 pc 0001 /vendor/lib.so(ANativeWindow_getFormat+60)", "Other thread info:", "Tid:999", "#00 pc 0002 wrong"]
        reports = fatal.crash_reports(lines, "faultlogs/cppcrash-test", "0" * 64)
        self.assertEqual(1, len(reports[0]["frames"]))
        result = fatal.analyze([stop], {123}, reports)
        self.assertEqual("fault-thread-stack", result["root"]["status"])
        for field, value in [("pid", 999), ("tid", 999), ("timestamp", "10-01 01:00:00.000")]:
            changed = copy.deepcopy(reports)
            changed[0][field] = value
            self.assertEqual("unknown", fatal.analyze([stop], {123}, changed)["root"]["status"])

    def test_disappearance_and_no_pid_are_unknown_causes(self):
        result = fatal.analyze([], {123}, disappeared=[dict(pid=123, before="t5", after="t20")])
        self.assertEqual("process-disappearance-cause-unknown", result["status"])
        self.assertIsNone(result["root"])
        self.assertEqual("no-observed-termination", fatal.analyze([event("FATAL EXCEPTION: main")], set())["status"])
        self.assertEqual("uncaught-handler", fatal.terminal_kind(event("uncaughtException handler invoked")))
        self.assertEqual("hilog-package-binding", fatal.disappearance([event("binding")], set(), set())[0]["before"])
        self.assertEqual([], fatal.disappearance([event("binding")], set(), None))

    def test_process_snapshot_requires_header_and_matching_uid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "processes-t20.txt"
            self.assertIsNone(fatal.processes(path, 1234))
            path.write_text("PID PPID UID NAME\n123 1 1234 app\n456 1 1235 foreign\n")
            self.assertEqual({123}, fatal.processes(path, 1234))
            path.write_text("PID PPID UID NAME\n456 1 1235 foreign\n")
            self.assertEqual(set(), fatal.processes(path, 1234))
            path.write_text("hdc connection error\n")
            self.assertIsNone(fatal.processes(path, 1234))

    def test_suppressed_chain_is_not_primary_cause(self):
        events = [event("java.lang.IllegalStateException: primary", number=1),
                  event("\tSuppressed: java.lang.RuntimeException: secondary", number=2),
                  event("\tCaused by: java.lang.RuntimeException: suppressed cause", number=3),
                  event("System.exit called, status: 1", number=4)]
        self.assertEqual(events[0], fatal.analyze(events, {123})["root"]["event"])


if __name__ == "__main__":
    unittest.main()
