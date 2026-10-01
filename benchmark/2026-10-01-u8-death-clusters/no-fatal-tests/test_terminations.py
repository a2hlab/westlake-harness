import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/lab"))
import termination_events


def log(message, tag="C02c11/APPSPAWN", pid=100):
    return f"10-01 12:00:00.000 {pid} {pid} I {tag}: {message}"


class MatchingTests(unittest.TestCase):
    def match(self, message, tag="C02c11/APPSPAWN", pid=100):
        return termination_events.analyze([log(message, tag, pid)], {42}, "org.example.app")

    def test_manager_is_not_victim(self):
        event = self.match("org.example.app with pid 42 exit with signal:9")[0]
        self.assertEqual((event["pid"], event["victim_pid"], event["role"]), (100, 42, "wait-result"))
        self.assertFalse(self.match("org.example.app with pid 142 exit with signal:9"))
        self.assertFalse(self.match("xorg.example.app with pid 42 exit with signal:9"))
        self.assertFalse(self.match("org.other.app with pid 42 exit with signal:9"))

    def test_death_cleanup_does_not_become_killer(self):
        self.assertEqual(self.match("kill reason=OnRemoteDied, 42", "C01311/AppMS")[0]["role"], "observation")
        self.assertEqual(self.match("Client died, pid = 42", "C0420f/WMSRecover")[0]["role"], "observation")
        self.assertEqual(self.match("Ability on scheduler died: 'org.example.app.Main'", "C01336/AMS")[0]["role"], "observation")
        self.assertFalse(self.match("Ability on scheduler died: 'org.example.application.Main'", "C01336/AMS"))

    def test_memory_kill_requires_explicit_victim(self):
        self.assertEqual(self.match("killed process pid=42", "C00000/memmgr")[0]["kind"], "memory-kill")
        self.assertFalse(self.match("killed process pid=142", "C00000/memmgr"))
        self.assertFalse(self.match("memory pressure high 42", "C00000/memmgr"))

    def test_exit_zero_is_terminal(self):
        event = self.match("System.exit called, status: 0", "C00f00/appspawn-x", 42)[0]
        self.assertEqual((event["value"], event["role"]), (0, "terminal"))
        self.assertEqual(self.match("System.exit called, status: -1", "C00f00/appspawn-x", 42)[0]["value"], -1)

    def test_assertion_and_abort_are_terminal(self):
        for message in ["ASSERT FAILED msg=Missing required extension", "abort() called from libhwui"]:
            self.assertEqual(self.match(message, "C00f00/hwui_abort", 42)[0]["kind"], "native-abort")
        self.assertFalse(self.match("[IFACE-IF] method=System.exit called, status: 1", "C00f00/appspawn-x", 42))

    def test_handled_signals_and_warning_only_anr(self):
        for signal in [4, 35, 42]:
            self.assertEqual(self.match(f"org.example.app with pid 42 exit with signal:{signal}")[0]["role"], "observation")
        self.assertEqual(self.match("ANR pid=42 timed out", "C00000/watchdog")[0]["role"], "observation")
        self.assertEqual(self.match("ANR killing pid=42", "C00000/watchdog")[0]["role"], "terminal")


class ReportTests(unittest.TestCase):
    def test_eleven_keys_and_group_totals(self):
        report = json.loads((ROOT / "benchmark/2026-10-01-u8-death-clusters/no-fatal-terminations.json").read_text())
        self.assertEqual(report["target_count"], 11)
        self.assertEqual(len({row["key"] for row in report["rows"]}), 11)
        self.assertEqual(sum(group["count"] for group in report["groups"]), 11)
        self.assertEqual(sorted(group["count"] for group in report["groups"]), [1, 1, 1, 2, 6])
        for row in report["rows"]:
            self.assertIn("-seq-", row["source"])
            self.assertEqual(row["signed"]["verdict"], "dead")
            self.assertTrue(row["spawn"])
            self.assertTrue(row["wait_results"])
            self.assertEqual(row["faultlogs"], [])
            self.assertEqual(row["new_fault_inventory"], [])
            self.assertEqual(next(snapshot for snapshot in row["snapshots"] if snapshot["file"] == "processes-t20.txt")["target_rows"], [])
            for digest in row["inputs"].values():
                self.assertRegex(digest, r"^[a-f0-9]{64}$")
            for event in row["events"]:
                replay = termination_events.analyze([event["text"]], set(row["target_pids"]), row["package"])[0]
                for field in ["kind", "role", "victim_pid", "value"]:
                    self.assertEqual(event[field], replay[field])
                self.assertGreater(event["line"], 0)
            if row["group"] == "sigkill-sender-unknown":
                self.assertIsNone(row["terminal"])
            if row["group"] == "java-main-threw-system-exit-1":
                self.assertEqual(row["first_fatal"]["status"], "termination-found")
                self.assertTrue(row["first_fatal"]["root"]["event"])


if __name__ == "__main__":
    unittest.main()
