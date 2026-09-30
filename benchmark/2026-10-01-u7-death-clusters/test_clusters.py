import copy
import json
import unittest

import collect
import report


class EvidenceTests(unittest.TestCase):
    def test_signed_complement_and_terminal_identity(self):
        intake, _, _ = report.load()
        scores = report.read(collect.SCORES / "formal-66/results.json")
        self.assertEqual({row["key"] for row in intake["rows"]}, {row["key"] for row in collect.select(scores)})
        for row in intake["rows"]:
            fatal = row["evidence"]["termination"]
            session = row["session_first_fatal"]
            if session:
                for field in ["status", "terminal", "root"]:
                    self.assertEqual(fatal.get(field), session.get(field))
        seal = next(row for row in intake["rows"] if row["key"] == "fd-seal")
        self.assertEqual(seal["input_error"], "bm dump has no JSON record")
        self.assertFalse(seal["evidence"]["target_pids"])
        self.assertIsNone(seal["evidence"]["t20_sha256"])
        for key, line in [("vlc", 44510), ("ppsspp", 35504)]:
            row = next(row for row in intake["rows"] if row["key"] == key)
            self.assertEqual(row["evidence"]["termination"]["terminal"]["event"]["line"], line)
            self.assertEqual(row["evidence"]["termination"]["root"]["status"], "unknown")

    def test_bad_signed_cohort_refused(self):
        score = report.read(collect.SCORES / "formal-66/results.json")
        score["shards"]["5cd"]["rows"].pop()
        with self.assertRaises(ValueError):
            collect.select(score)


class ThreadTests(unittest.TestCase):
    def test_three_white_tails_are_pid_tid_bound(self):
        result = report.build()
        expected = {"fd-app": (24259, 24284), "fd-shatteredpixeldungeon": (14207, 14230), "termux": (19006, 19031)}
        for key, (pid, tid) in expected.items():
            row = result["main_thread_observations"][key]
            self.assertEqual(row["main_threads"], [dict(pid=pid, tid=tid)])
            self.assertNotEqual(pid, tid)
            self.assertGreater(row["silence_before_capture_seconds"], 13)
            self.assertEqual(row["state_at_t20"], "unknown-no-thread-stack-sample")
            self.assertTrue(all((event["pid"], event["tid"]) == (pid, tid) for event in row["last_main_execution"]))
        self.assertIn("mFinished=true", result["main_thread_observations"]["termux"]["last_main_execution"][-1]["message"])

    def test_wrong_pid_and_after_capture_are_excluded(self):
        event = dict(line=1, pid=10, tid=20, timestamp="10-01 06:00:00.000", message=collect.MAIN, tag="App", level="I", text="binding")
        tail = dict(event, line=2, timestamp="10-01 06:00:02.000", message="onResume done")
        other = dict(tail, line=3, pid=99)
        late = dict(tail, line=4, timestamp="10-01 06:00:30.000")
        result = collect.thread_observations([event, tail, other, late], {10}, "10-01 06:00:01.000", "10-01 06:00:20.000")
        self.assertEqual([item["line"] for item in result["last_main_execution"]], [2])
        self.assertEqual(result["main_threads"], [dict(pid=10, tid=20)])
        self.assertEqual(result["state_at_t20"], "unknown-no-thread-stack-sample")


class ClusterTests(unittest.TestCase):
    def test_partition_sources_and_replay(self):
        result = report.build()
        self.assertEqual(result, report.read(report.HERE / "clusters.json"))
        self.assertEqual(report.markdown(result), (report.HERE / "README.md").read_text())
        counts = [entry["count"] for entry in result["clusters"]]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(sum(counts), 32)
        self.assertEqual(len(result["n8"]["target_keys"]), 11)
        self.assertEqual(result["terminal_counts"]["termination-found"], 23)
        element = next(entry for entry in result["clusters"] if entry["id"] == "private-zlib")
        self.assertEqual(element["n8_in_flight_keys"], ["fd-im-vector-app"])
        white = next(entry for entry in result["clusters"] if entry["id"] == "white-B")
        self.assertEqual([entry["apps"] for entry in white["subclusters"]], [["fd-app", "fd-shatteredpixeldungeon"], ["termux"]])
        self.assertTrue(any(quote["timestamp"] == "2026-10-01T07:33:49" for quote in result["classifications"]))
        self.assertTrue(any(quote["timestamp"] == "2026-10-01T07:42:35" for quote in result["classifications"]))
        self.assertTrue(all(any("IllegalArgumentException" in line["text"] for line in evidence["excerpt"]) for evidence in white["subclusters"][0]["raw_followup_evidence"]))
        flutter = next(entry for entry in result["clusters"] if entry["id"] == "flutter-field-id")
        self.assertIn("exact field unknown", flutter["wall"])
        self.assertTrue(all(any("FlutterJNI.nativeRunBundleAndSnapshotFromLibrary" in evidence["text"] for evidence in app["evidence"]) for app in flutter["apps"]))

    def test_duplicate_app_and_bad_provenance_refused(self):
        _, plan, sources = report.load()
        changed = copy.deepcopy(plan)
        changed["clusters"][0]["apps"].append("fd-app")
        with self.assertRaises(ValueError):
            report.build(plan=changed)
        changed_sources = copy.deepcopy(sources)
        changed_sources["sources"]["hwui-egl"]["commit"] = "unverified"
        with self.assertRaises(ValueError):
            report.build(sources=changed_sources)


if __name__ == "__main__":
    unittest.main()
