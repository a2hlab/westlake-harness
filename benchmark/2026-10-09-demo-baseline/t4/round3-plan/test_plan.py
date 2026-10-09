import copy
import importlib.util
from pathlib import Path
import unittest

from prepare import build


BASELINE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("seal_fixtures", BASELINE / "t5/test_seal.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def fixture():
    snapshot, overlays, manifest = fixtures.fixture()
    app = manifest["apps"][0]
    app.update(input_root="$WORKSPACES/inputs", is_game=True, needs_first_tap=True)
    tiers = {"schema": "demo-shot-tiers/v1", "apps": [{"key": "demo", "package": app["package"],
                                                     "apk_sha256": app["apk_sha256"], "screenshot_seconds": 10}]}
    return manifest, tiers, overlays, {}


class PlanTests(unittest.TestCase):
    def test_disabled_reboot_before_ready_before_capture(self):
        result = build(*fixture())
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["rollout_enabled"])
        actions = [row["action"] for row in result["workflow"]]
        self.assertLess(actions.index("reboot-once"), actions.index("wait-readonly-ready"))
        self.assertLess(actions.index("wait-readonly-ready"), actions.index("continuous-launch-and-capture"))
        self.assertEqual(result["workflow"][3]["timeout_seconds"], 600)
        self.assertIn("aborted", result["workflow"][3]["on_timeout"])
        self.assertFalse(result["apps"][0]["install"])
        self.assertIsNone(result["apps"][0]["tap"])

    def test_deterministic(self):
        args = fixture()
        self.assertEqual(build(*args), build(*copy.deepcopy(args)))

    def test_apk_identity_mismatch_rejects(self):
        args = fixture()
        args[1]["apps"][0]["apk_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            build(*args)

    def test_missing_extra_duplicate_tier_rejects(self):
        for mutation in (lambda rows: rows.clear(), lambda rows: rows.append(dict(rows[0], key="extra")), lambda rows: rows.append(rows[0])):
            args = fixture()
            mutation(args[1]["apps"])
            with self.assertRaises(ValueError):
                build(*args)

    def test_pending_overlay_remains_pending_not_skipped(self):
        args = fixture()
        args[2]["items"][0]["state"] = "pending"
        result = build(*args)
        self.assertFalse(result["summary"]["overlays_ready"])
        self.assertTrue(any("resolve both" in line for line in result["pending"]))

    def test_active_specials_always_twenty_seconds(self):
        snapshot, overlays, _ = fixtures.fixture()
        fixtures.add_overlays(snapshot, overlays)
        args = fixture()
        result = build(args[0], args[1], overlays, {})
        self.assertEqual([row["key"] for row in result["apps"]], ["demo", "toutiao", "BoatAttack"])
        self.assertEqual([row["screenshot_seconds"] for row in result["apps"]], [10, 20, 20])
        self.assertTrue(result["summary"]["overlays_ready"])

    def test_invalid_delay_rejects(self):
        args = fixture()
        args[1]["apps"][0]["screenshot_seconds"] = 5
        with self.assertRaisesRegex(ValueError, "delay"):
            build(*args)


if __name__ == "__main__":
    unittest.main()
