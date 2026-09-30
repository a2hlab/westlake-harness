import unittest
from unittest.mock import patch

import report


scan = report.scan


def event(message, line=1, pid=101, time="04:00:05.000", tag="C00f00/OH_DER_VSync"):
    return scan.first_fatal.classify.parse(f"10-01 {time} {pid} 110 I {tag}: {message}", line)


class ScopeTests(unittest.TestCase):
    def test_pid_time_registration_and_substring_contamination(self):
        events = [event("scheduleVsync RequestFrame rc=0"), event("onOhVsync ENTRY ts=12 data=abc", 2),
                  event("present rc=0", 3, pid=999, tag="C00f00/RS"),
                  event("present rc=0", 4, time="04:00:22.000", tag="C00f00/RS"),
                  event("present rc=0", 5, time="03:59:59.000", tag="C00f00/RS"),
                  event("9: void adapter.WindowSessionAdapter.finishDrawing()", 6, tag="C00f00/appspawn-x"),
                  event("[class_linker.cc:8744] finishDrawing", 7, tag="C00f00/appspawn-x"),
                  event("nativeNotifyDrawingCompleted -> fn=0000", 8, tag="C00f00/OH_RegHook"),
                  event("SSLContext provider present", 9, tag="C00f00/AppSpawnXJava"),
                  event("presentationDisplayId=-1", 10, tag="C00f00/MediaRouter")]
        observed = scan.count_events(events, {101}, "10-01 04:00:00.000", "10-01 04:00:20.999")
        self.assertEqual(1, observed["counts"]["vsync_request_ok"])
        self.assertEqual(1, observed["counts"]["vsync_callback"])
        self.assertEqual(0, observed["counts"]["present_event"])
        self.assertEqual(0, observed["counts"]["finish_drawing"])
        self.assertEqual(2, observed["nonexecution_substrings"]["finish_drawing"])
        self.assertIsNone(observed["present_vsync_ratio"])
        self.assertEqual("unknown-no-explicit-marker", observed["present_observability"])
        with self.assertRaises(ValueError):
            scan.count_events(events, set(), None, None)

    def test_explicit_graphics_receipts_and_failed_requests(self):
        events = [event("present failed rc=-1", tag="C00f00/OH_GfxShim"),
                  event("finishDrawing ENTRY window=12", 2, tag="C00f00/WindowSessionAdapter"),
                  event("NotifyDrawingCompleted ENTRY window=12", 3, tag="C00f00/WindowSessionAdapter"),
                  event("scheduleVsync RequestFrame rc=-1", 4)]
        counts = scan.count_events(events, {101}, "10-01 04:00:00.000", "10-01 04:00:20.999")["counts"]
        self.assertEqual((1, 1, 1, 1), tuple(counts[name] for name in ["present_failed", "finish_drawing", "notify_drawing", "vsync_request_failed"]))


class TerminalTests(unittest.TestCase):
    def test_terminal_cutoff_signal_exclusion_and_disappearance(self):
        early = event("[CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: boom", tag="C00f00/appspawn-x")
        late = dict(early, timestamp="10-01 04:00:21.000")
        cutoff = "10-01 04:00:20.999"
        before = scan.first_fatal.analyze([early], {101}, cutoff=cutoff)
        after = scan.first_fatal.analyze([late], {101}, cutoff=cutoff)
        self.assertEqual("observed-termination", scan.eligibility(dict(coverage_ok=True, termination=before), "white"))
        self.assertEqual("candidate-not-proven", scan.eligibility(dict(coverage_ok=True, termination=after), "white"))
        full = scan.first_fatal.analyze([late], {101})
        self.assertEqual("termination-found", full["status"])
        signals = [event(f"signo({number})", number, tag="C00f00/DfxSignalHandler") for number in [4, 35, 42]]
        self.assertEqual("no-observed-termination", scan.first_fatal.analyze(signals, {101}, cutoff=cutoff)["status"])
        gone = scan.first_fatal.analyze([], {101}, disappeared=[dict(pid=101)], cutoff=cutoff)
        self.assertEqual("observed-termination", scan.eligibility(dict(coverage_ok=True, termination=gone), "white"))


class RuleTests(unittest.TestCase):
    def test_score_does_not_look_at_visual_label(self):
        observation = dict(counts=dict(vsync_request_ok=501, vsync_callback=501, present_failed=0))
        score = scan.suspicion(observation)
        self.assertEqual(40, score["score"])
        for visual in ["white", "own-ui", "unknown"]:
            row = dict(coverage_ok=True, termination=dict(status="no-observed-termination"), visual=visual)
            self.assertEqual(score, scan.suspicion(observation))
            self.assertEqual(visual == "white", scan.eligibility(row, visual) == "candidate-not-proven")
        row["coverage_ok"] = False
        self.assertEqual("incomplete-evidence", scan.eligibility(row, "white"))


class ReplayTests(unittest.TestCase):
    def test_complete_cohort_and_controls_reproduce(self):
        result = report.build()
        self.assertEqual(dict(attempts=78, u6=66, t7d=12, target_attempts=9, target_keys=7,
                              negative_control_attempts=34, control_low_score=29, control_high_score_false_alarms=5), result["counts"])
        self.assertEqual({"wikipedia", "fd-noice", "noice", "fd-AppManager", "fd-app", "fd-shatteredpixeldungeon", "termux"}, set(result["n9_target_keys"]))
        self.assertEqual({"antennapod", "fd-auxio", "fd-com-kunzisoft-keepass-libre", "fd-filemanager", "opencamera"}, {row["key"] for row in result["high_score_controls"]})
        for name, content in report.outputs().items():
            self.assertEqual(content, (report.HERE / name).read_text())
        observed = report.read(report.HERE / "evidence/observations.json")["observations"]
        noices = [row for row in observed if row["cohort"] == "t7d" and row["key"] == "fd-noice"]
        self.assertEqual([104, 95, 98], [row["observation"]["counts"]["vsync_request_ok"] for row in noices])
        for row in observed:
            if row["observation"]:
                self.assertEqual(0, row["observation"]["counts"]["present_event"])
                self.assertEqual(0, row["observation"]["counts"]["finish_drawing"])

    def test_tampered_capture_review_is_rejected(self):
        original = report.read
        def changed(path):
            value = original(path)
            if path.name == "review.json":
                value["rows"][0]["t20_sha256"] = "0" * 64
            return value
        with patch.object(report, "read", side_effect=changed), self.assertRaisesRegex(ValueError, "identity changed"):
            report.build()


if __name__ == "__main__":
    unittest.main()
