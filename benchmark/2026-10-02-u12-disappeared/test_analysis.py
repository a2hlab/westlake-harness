import hashlib
import json
from pathlib import Path
import unittest

from collect import exit_status

HERE = Path(__file__).resolve().parent


class DisappearanceTests(unittest.TestCase):
    def test_termination_binding_rejects_cleanup_and_notification(self):
        event = dict(line=20, timestamp="10-02 17:00:00.000", pid=100, tag="C02c11/APPSPAWN",
                     message="[appspawn_service.c:114]org.test.app with pid 42 exit with signal:9", text="fixture")
        self.assertEqual(exit_status(event, "org.test.app", {42})["value"], 9)
        self.assertIsNone(exit_status(event, "org.other.app", {42}))
        self.assertIsNone(exit_status(event, "org.test.app", {43}))
        for message in ["ProcessSignal signum:17 pid:42", "OnRemoteDied killReason pid:42", "exit with signal:9"]:
            self.assertIsNone(exit_status(dict(event, message=message), "org.test.app", {42}))
        self.assertIsNone(exit_status(dict(event, tag="AppLog"), "org.test.app", {42}))

    def test_six_keys_seven_actual_pid_statuses(self):
        observations = json.loads((HERE / "observations.json").read_text())
        expected = {"burgerking": [(570, "code", 1)], "cv2-com-kaajjo-libresudoku": [(9435, "code", 0)],
                    "fd-fennec_fdroid": [(25084, "signal", 9)], "firefox": [(25608, "signal", 9)],
                    "ppsspp": [(26744, "code", 255)], "vlc": [(4317, "code", 1), (4353, "code", 1)]}
        self.assertEqual(observations["source_commit"], "2aa6c49df0")
        self.assertEqual(len(observations["rows"]), 6)
        for row in observations["rows"]:
            actual = [(entry["pid"], entry["status"]["kind"], entry["status"]["value"]) for entry in row["pids"]]
            self.assertEqual(actual, expected[row["key"]])
            self.assertTrue(row["run_apk_identity_verified"])
            self.assertEqual(row["original"]["terminal"]["kind"], "process-disappeared")
            self.assertTrue(row["fault_inventory_unchanged"])
            self.assertEqual(row["faultlogs"], [])
            excerpt = (HERE / row["excerpt"]).read_text()
            for entry in row["pids"]:
                self.assertNotEqual(entry["status"]["reporter_pid"], entry["pid"])
                self.assertIn(str(entry["status"]["line"]) + ": ", excerpt)
                for name in ["loader_errors", "last_fe", "last_app_events", "uncaught_markers"]:
                    self.assertTrue(all(event["pid"] == entry["pid"] for event in entry[name]))

    def test_pinned_exit_callers_and_conditional_forecasts(self):
        dex = {row["key"]: row for row in json.loads((HERE / "dex.json").read_text())}

        def method(key, owner, name):
            selected = next(row for row in dex[key]["methods"] if row["owner"] == owner and row["method"] == name)
            return "\n".join(entry["text"] for entry in selected["dexdump_lines"])

        for key in ["fd-fennec_fdroid", "firefox"]:
            text = method(key, "Lmozilla/components/lib/crash/handler/ExceptionHandler;", "uncaughtException")
            self.assertIn("Uncaught exception handled:", text)
            self.assertIn("Process;.killProcess:", text)
            self.assertLess(text.index("UncaughtExceptionHandler;.uncaughtException:"), text.index("Process;.killProcess:"))
        ppsspp = method("ppsspp", "Lorg/ppsspp/ppsspp/PpssppActivity;", "onCreate")
        self.assertIn("#int 3000", ppsspp)
        self.assertIn("#int -1", ppsspp)
        self.assertIn("m_hasNoNativeBinary", ppsspp)
        self.assertIn("m_hasNoNativeBinary", method("ppsspp", "Lorg/ppsspp/ppsspp/PpssppActivity;", "CheckABIAndLoadLibrary"))
        vlc = method("vlc", "Lorg/videolan/libvlc/LibVLC;", "loadLibraries")
        self.assertIn("Can't load vlcjni library:", vlc)
        self.assertIn("System;.exit:", vlc)
        sudoku = method("cv2-com-kaajjo-libresudoku", "Lcom/kaajjo/libresudoku/core/utils/GlobalExceptionHandler;", "uncaughtException")
        self.assertIn("System;.exit:", sudoku)
        self.assertIn("|002f: const/4 v0, #int 0", sudoku)
        result = json.loads((HERE / "results.json").read_text())
        self.assertEqual(len(result["clusters"]), 5)
        self.assertEqual(len(result["predictions"]), 6)
        self.assertEqual(result["predicted_new_lights"], [])
        self.assertEqual(result["exports_only_4698_first_fatal_moved_keys"], [])
        for row in result["predictions"]:
            self.assertEqual(row["next_exact_fatal"], "unknown")
            self.assertEqual(row["t20"], "unknown")
            self.assertTrue(row["evidence_lines"])
        provider = (HERE / "evidence/compat-dynsym.txt").read_text()
        self.assertRegex(provider, r"GLOBAL DEFAULT\s+\d+ __gnu_strerror_r")
        self.assertRegex(provider, r"GLOBAL DEFAULT\s+\d+ android_dlopen_ext")
        self.assertFalse(result["factory_libc"]["symbols"]["__pthread_cleanup_push"])
        self.assertTrue(result["factory_libc"]["symbols"]["_pthread_cleanup_push"])
        for row in result["source_references"]:
            self.assertEqual(hashlib.sha256((HERE / row["evidence"]).read_bytes()).hexdigest(), row["evidence_sha256"])


if __name__ == "__main__":
    unittest.main()
