import copy
import json
from pathlib import Path
import tempfile
import unittest

import build_manifest as builder


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.apk = self.root / "app.apk"
        self.apk.write_bytes(b"test-apk")
        self.record = self.root / "record.json"
        self.record.write_text(json.dumps({"key": "sample", "package": "org.sample",
                                           "apk_sha256": builder.digest(self.apk)}))
        self.app = {"key": "sample", "package": "org.sample", "apk_path": str(self.apk),
                    "apk_sha256": builder.digest(self.apk), "record_path": str(self.record),
                    "record_sha256": builder.digest(self.record)}

    def test_identity_accepts_same_bytes_package_and_signed_record(self):
        result = builder.verify_identity(self.app, lambda path: "org.sample")
        self.assertTrue(result["identity_verified"])

    def test_missing_apk_rejects_named_key(self):
        self.apk.unlink()
        with self.assertRaisesRegex(ValueError, "sample:"):
            builder.verify_identity(self.app, lambda path: "org.sample")

    def test_wrong_apk_sha_rejects_without_writing_manifest(self):
        self.app["version"] = "1"
        metadata = self.root / "metadata.json"
        gallery = self.root / "gallery.json"
        metadata.write_text(json.dumps({"apps": [self.app]}))
        gallery.write_text(json.dumps({"shown": [{"key": "sample", "pkg": "org.sample", "ver": "1"}],
                                       "minimal": [], "errors": []}))
        self.apk.write_bytes(b"corrupted")
        output = self.root / "output.json"
        with self.assertRaisesRegex(ValueError, "sample: APK SHA"):
            builder.build(output, self.root / "identities.json", metadata, gallery,
                          lambda path: "org.sample", include_unlit=False)
        self.assertFalse(output.exists())
        self.assertFalse((self.root / "identities.json").exists())

    def test_wrong_package_rejects(self):
        with self.assertRaisesRegex(ValueError, "sample: APK package"):
            builder.verify_identity(self.app, lambda path: "org.other")

    def test_changed_record_rejects(self):
        self.record.write_text("{}")
        with self.assertRaisesRegex(ValueError, "sample: signed source record SHA"):
            builder.verify_identity(self.app, lambda path: "org.sample")

    def test_portable_does_not_replace_sibling_repo_prefix(self):
        sibling = builder.WORKSPACES / "westlake-harness-u7-executor/evidence.json"
        self.assertEqual(builder.portable(sibling), "$WORKSPACES/westlake-harness-u7-executor/evidence.json")


class FrozenInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = builder.read_json(builder.HERE / "demo-manifest.json")

    def test_package_and_signed_key_coverage(self):
        builder.validate(self.manifest)
        rows = self.manifest["apps"]
        self.assertEqual(len(rows), 128)
        keys = [key for row in rows for key in row["signed_keys"]]
        self.assertEqual(len(keys), 129)
        self.assertEqual(len(set(keys)), 129)
        identities = builder.read_json(builder.HERE / "identity-checks.json")["checks"]
        self.assertEqual({row["key"] for row in identities}, set(keys))
        self.assertTrue(all(row["identity_verified"] for row in identities))

    def test_all_twelve_games_install_even_empty_or_error(self):
        rows = {row["key"]: row for row in self.manifest["apps"]}
        self.assertEqual(len(self.manifest["signed_games"]), 12)
        self.assertTrue(all(rows[key]["install"] for key in self.manifest["signed_games"]))
        for key in ("fd-minetest", "fd-stk"):
            self.assertIn(key, self.manifest["signed_games"])
            self.assertFalse(rows[key]["counts_as_first_content"])

    def test_unknown_taps_do_not_inflate_content(self):
        rows = self.manifest["apps"]
        self.assertEqual(sum(row["counts_as_first_content"] for row in rows), 94)
        empty = [row for row in rows if row["historical_content_status"] == "minimal"]
        self.assertEqual(len(empty), 32)
        self.assertEqual(sum(row["needs_first_tap"] is True for row in empty), 32)
        self.assertEqual(sum(row["first_tap"]["assessment"] == "tap_likely" for row in empty), 26)
        self.assertEqual(sum(row["first_tap"]["assessment"] == "tap_try_or_review" for row in empty), 6)
        for row in empty:
            self.assertTrue(row["first_tap"]["target"])
            self.assertEqual(row["first_tap"]["coordinate_status"], "unverified")
            self.assertFalse(row["first_tap"]["interaction_verified"])
        self.assertFalse(self.manifest["summary"]["target_verified_on_demo_board"])
        bad = copy.deepcopy(self.manifest)
        next(row for row in bad["apps"] if row["historical_content_status"] == "errors")["counts_as_first_content"] = True
        with self.assertRaisesRegex(ValueError, "falsely counted"):
            builder.validate(bad)

    def test_noice_conflict_is_resolved_explicitly(self):
        noice = [row for row in self.manifest["apps"] if row["package"] == "com.github.ashutoshgngwr.noice"]
        self.assertEqual(len(noice), 1)
        self.assertEqual(noice[0]["key"], "fd-noice")
        self.assertEqual(noice[0]["version"], "2.5.7")
        self.assertEqual(noice[0]["signed_keys"], ["fd-noice", "noice"])

    def test_offline_selected_board_and_pending_special_routes(self):
        self.assertFalse(self.manifest["execution_enabled"])
        self.assertEqual(self.manifest["board_choice"]["board"], "61b0657200000000000000000324012c")
        self.assertTrue(all(not row["install"] for row in self.manifest["special_apps"]))
        for row in self.manifest["unlit_games_and_tools"]:
            self.assertFalse(row["install"])
            self.assertTrue(row["first_fatal"] is not None or row["status"] == "unknown-terminal-root")


if __name__ == "__main__":
    unittest.main(verbosity=2)
