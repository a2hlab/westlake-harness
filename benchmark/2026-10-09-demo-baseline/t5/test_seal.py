import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from build_seal import SERIAL, build


HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[3]))
MASTER = WORKSPACES / "westlake-harness"
REPO = HERE.parents[2]
SELF_CHECK = REPO / "scripts/lab/demo_selfcheck.sh"
if not SELF_CHECK.is_file():
    SELF_CHECK = MASTER / "scripts/lab/demo_selfcheck.sh"


def fixture():
    runtime = "/system/android/lib64/liboh_android_runtime.so"
    boot = "/system/android/framework/arm64/boot.art"
    installer = "/system/lib64/libinstalls.z.so"
    apk = "/data/app/el1/bundle/public/org.demo/android/base.apk"
    groups = {"runtime": {runtime: "a" * 64}, "boot": {boot: "b" * 64},
              "installation": {installer: "c" * 64}, "overlays": {}}
    package = {"package": "org.demo", "version_code": 3, "version_name": "1.0", "apk_path": apk, "apk_sha256": "d" * 64}
    snapshot = {"schema": "demo-seal-snapshot/v1", "mode": "live-readonly", "serial": SERIAL,
                "captured_at": "2026-10-09T21:00:00+08:00", "boot_before": "boot-fixture", "boot_after": "boot-fixture",
                "remote_write_operations": 0, "lock_operations": 0, "errors": [], "files": groups,
                "fingerprint_lines": {group: [sha + "  " + path for path, sha in groups[group].items()] for group in ("runtime", "boot")},
                "system_params": {"const.ohos.fullname": "OpenHarmony-6.1.0.31"}, "packages": [package],
                "apk_hashes": {apk: "d" * 64}, "package_inventory_complete": True, "file_inventory_complete": True,
                "inventories": [{"patterns": ["/system/android/lib64/*.so"], "paths": [runtime]}]}
    overlays = {"schema": "demo-overlays/v1", "seal_stage": "v1", "items": [{"id": name, "state": "absent", "reason": "fixture excluded", "files": []}
                                                         for name in ("toutiao-route-b", "boatattack")]}
    manifest = {"apps": [{"key": "demo", "package": "org.demo", "install": True, "version_code": 3,
                          "version": "1.0", "apk_sha256": "d" * 64}]}
    add_overlays(snapshot, overlays, include_boat=False)
    return snapshot, overlays, manifest


def add_overlays(snapshot, overlays, include_boat=True):
    if include_boat:
        overlays["seal_stage"] = "v2"
    for row in overlays["items"]:
        name = row["id"]
        if row["state"] == "active" or (name == "boatattack" and not include_boat):
            continue
        row.update(state="active", package="org." + name.replace("-", "."), route="B",
                   apk_sha256="f" * 64, version_code=1, version_name="1.0",
                   source={"path": "$WORKSPACES/source.json", "sha256": "e" * 64},
                   rollback={"path": "$WORKSPACES/rollback.json", "sha256": "f" * 64})
        roles = ["admitted-member"] if name == "boatattack" else ["ttbundle"]
        row["files"] = [{"role": role, "target": f"/data/demo/{name}/{index}.bin", "sha256": "e" * 64} for index, role in enumerate(roles)]
        if name == "toutiao-route-b":
            row.update(launch_kind="embedded-in-hap", host_package="org.westlake.imehost", payload_path=f"/data/demo/{name}/toutiao.apk")
            row["files"][0].update(target=row["payload_path"], sha256="f" * 64)
        else:
            row["admission"] = {"path": "$WORKSPACES/boat-v2-approval.json", "sha256": "a" * 64}
        snapshot["files"]["overlays"].update({member["target"]: member["sha256"] for member in row["files"]})
        apk = f"/data/demo/{name}/base.apk"
        registered = row.get("host_package", row["package"])
        snapshot["packages"].append({"package": registered, "version_name": "1.0", "version_code": 1, "apk_path": apk, "apk_sha256": "f" * 64})
        snapshot["apk_hashes"][apk] = "f" * 64


class SealTests(unittest.TestCase):
    def reject(self, mutate, message):
        snapshot, overlays, manifest = fixture()
        mutate(snapshot, overlays, manifest)
        with self.assertRaisesRegex(ValueError, message):
            build(snapshot, overlays, manifest)

    def test_two_generations_identical(self):
        args = fixture()
        self.assertEqual(json.dumps(build(*args), sort_keys=True), json.dumps(build(*copy.deepcopy(args)), sort_keys=True))

    def test_actual_selfcheck_accepts_generated_seal_and_rejects_drift(self):
        snapshot, overlays, manifest = fixture()
        add_overlays(snapshot, overlays)
        seal = build(snapshot, overlays, manifest)
        observed = {"serial": SERIAL, "boot_before": "b", "boot_after": "b", "errors": [],
                    "files": {path: sha for files in seal["files"].values() for path, sha in files.items()},
                    "system_params": seal["system_params"], "packages": {row["package"]: {"version_code": row["version_code"]} for row in seal["packages"]},
                    "inventories": [sorted(row["paths"]) for row in seal["inventories"]]}
        observed["files"].update(snapshot["apk_hashes"])
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "seal.json").write_text(json.dumps(seal))
            for changed, expected in ((False, 0), (True, 1)):
                if changed:
                    observed["files"][overlays["items"][0]["files"][0]["target"]] = "0" * 64
                (folder / "obs.json").write_text(json.dumps(observed))
                result = subprocess.run(["bash", str(SELF_CHECK), "--seal", str(folder / "seal.json"),
                                         "--serial", SERIAL, "--observed", str(folder / "obs.json")], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertIn("OFFLINE_MATCH" if not changed else "DRIFT /data/demo/", result.stdout)

    def test_pending_overlay_refuses_seal(self):
        self.reject(lambda s, o, m: o["items"][0].update(state="pending"), "unresolved")

    def test_v1_cannot_silently_omit_route_b(self):
        self.reject(lambda s, o, m: o["items"][0].update(state="absent"), "active Toutiao")

    def test_boot_changed_refuses(self):
        self.reject(lambda s, o, m: s.update(boot_after="other"), "crosses boot")

    def test_snapshot_error_refuses(self):
        self.reject(lambda s, o, m: s.update(errors=["read failed"]), "read errors")

    def test_wrong_serial_refuses(self):
        self.reject(lambda s, o, m: s.update(serial="5ea"), "wrong demo")

    def test_missing_system_version_refuses(self):
        self.reject(lambda s, o, m: s.update(system_params={}), "system version")

    def test_version_or_apk_mismatch_refuses(self):
        self.reject(lambda s, o, m: m["apps"][0].update(version_code=4), "not installed")
        self.reject(lambda s, o, m: s["apk_hashes"].update({s["packages"][0]["apk_path"]: "0" * 64}), "APK SHA differs")

    def test_fingerprint_member_mismatch_refuses(self):
        self.reject(lambda s, o, m: s["fingerprint_lines"]["runtime"].append("0" * 64 + "  /system/extra.so"), "membership")

    def test_package_inventory_incomplete_refuses(self):
        self.reject(lambda s, o, m: s.update(package_inventory_complete=False), "inventory must")
        self.reject(lambda s, o, m: s.update(file_inventory_complete=False), "inventory must")

    def test_cli_fresh_seal_and_refusal_before_write(self):
        snapshot, overlays, manifest = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for name, value in (("snapshot", snapshot), ("overlays", overlays), ("manifest", manifest)):
                (folder / (name + ".json")).write_text(json.dumps(value))
            output = folder / "seal.json"
            command = ["python3", str(HERE / "build_seal.py"), "--snapshot", str(folder / "snapshot.json"),
                       "--overlays", str(folder / "overlays.json"), "--manifest", str(folder / "manifest.json"), "--out", str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("SEAL_COMPILED_OFFLINE", result.stdout)
            original = output.read_bytes()
            second = folder / "seal-second.json"
            repeated = subprocess.run(command[:-1] + [str(second)], capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 0, repeated.stdout)
            self.assertEqual(original, second.read_bytes())
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output.read_bytes(), original)
            output.unlink()
            overlays["items"][0]["state"] = "pending"
            (folder / "overlays.json").write_text(json.dumps(overlays))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_unsafe_path_refuses(self):
        self.reject(lambda s, o, m: s["files"]["overlays"].update({"/tmp/x;reboot": "a" * 64}), "unsafe")

    def test_boat_members_and_observed_bytes_enforced(self):
        snapshot, overlays, manifest = fixture()
        add_overlays(snapshot, overlays)
        overlays["items"][1]["files"].pop()
        with self.assertRaisesRegex(ValueError, "active overlay files"):
            build(snapshot, overlays, manifest)
        snapshot, overlays, manifest = fixture()
        add_overlays(snapshot, overlays)
        snapshot["files"]["overlays"][overlays["items"][0]["files"][0]["target"]] = "0" * 64
        with self.assertRaisesRegex(ValueError, "effective bytes"):
            build(snapshot, overlays, manifest)

    def test_conflicting_effective_jar_refuses(self):
        snapshot, overlays, manifest = fixture()
        add_overlays(snapshot, overlays)
        path = overlays["items"][1]["files"][0]["target"]
        snapshot["files"]["runtime"][path] = "0" * 64
        with self.assertRaisesRegex(ValueError, "conflicting effective"):
            build(snapshot, overlays, manifest)

    def test_v1_excludes_boat_and_v2_requires_admitted_overlay(self):
        snapshot, overlays, manifest = fixture()
        self.assertEqual(build(snapshot, overlays, manifest)["seal_stage"], "v1")
        add_overlays(snapshot, overlays)
        overlays["seal_stage"] = "v1"
        with self.assertRaisesRegex(ValueError, "absent in v1"):
            build(snapshot, overlays, manifest)
        overlays["seal_stage"] = "v2"
        self.assertEqual(build(snapshot, overlays, manifest)["seal_stage"], "v2")
        del overlays["items"][1]["admission"]
        with self.assertRaisesRegex(ValueError, "pinned admission"):
            build(snapshot, overlays, manifest)
        snapshot, overlays, manifest = fixture()
        overlays["seal_stage"] = "v2"
        with self.assertRaisesRegex(ValueError, "admitted overlay in v2"):
            build(snapshot, overlays, manifest)

    def test_no_legacy_implicit_stage_or_fixed_boat_shape(self):
        snapshot, overlays, manifest = fixture()
        del overlays["seal_stage"]
        with self.assertRaisesRegex(ValueError, "seal_stage"):
            build(snapshot, overlays, manifest)
        snapshot, overlays, manifest = fixture()
        add_overlays(snapshot, overlays)
        self.assertEqual(len(overlays["items"][1]["files"]), 1)
        build(snapshot, overlays, manifest)

    def test_embedded_route_does_not_require_android_bms_registration(self):
        snapshot, overlays, manifest = fixture()
        add_overlays(snapshot, overlays)
        seal = build(snapshot, overlays, manifest)
        self.assertNotIn(overlays["items"][0]["package"], {row["package"] for row in seal["packages"]})
        self.assertIn("org.westlake.imehost", {row["package"] for row in seal["packages"]})
        self.assertEqual(seal["files"]["overlays"][overlays["items"][0]["payload_path"]], "f" * 64)


if __name__ == "__main__":
    unittest.main()
