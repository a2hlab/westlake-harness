import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import build_runbook
import restore


SERIAL = "61b0657200000000000000000324012c"
SPARE = "5cd1e3dd00000000000000000923012c"
RUNTIME = "/system/android/lib64/liboh_android_runtime.so"
BOOT = "/system/android/framework/arm64/boot.art"
INSTALL = "/system/lib64/libinstalls.z.so"
APK = "/data/app/el1/bundle/public/org.demo/android/base.apk"


def fixture(folder, overlays=False):
    files = {"runtime": {RUNTIME: "runtime"}, "boot": {BOOT: "boot"},
             "installation": {INSTALL: "stock"}, "overlays": {}}
    if overlays:
        files["overlays"] = {"/data/demo/ttbundle.apk": "route-b", "/data/demo/boat.jar": "boat"}
    seal = {"schema": "demo-seal/v1", "serial": SERIAL, "files": {},
            "system_params": {"const.ohos.fullname": "OpenHarmony-6.1.0.31"},
            "packages": [{"package": "org.demo", "version_code": 3, "apk_path": APK, "apk_sha256": ""}]}
    members = []
    for group, values in files.items():
        seal["files"][group] = {}
        for target, content in values.items():
            source = folder / (str(len(members)) + ".bin")
            source.write_bytes(content.encode())
            sha = restore.digest(source)
            seal["files"][group][target] = sha
            members.append({"target": target, "source": {"path": source.name, "sha256": sha},
                            "mode": "verify-only" if group == "installation" else "restore"})
    source = folder / "app.apk"
    source.write_bytes(b"synthetic archived apk")
    seal["packages"][0]["apk_sha256"] = restore.digest(source)
    members.append({"target": APK, "source": {"path": source.name, "sha256": restore.digest(source)}, "mode": "restore"})
    program = folder / "provider.py"
    program.write_text("raise SystemExit('offline mock only; never execute this provider')\n")
    pinned = {"path": program.name, "sha256": restore.digest(program)}
    targets = [row["target"] for row in members if row["mode"] == "restore" and not row["target"].startswith("/data/demo/")]
    providers = [{"layer": "u13", "interpreter": "python3", "program": pinned, "rollback": pinned, "targets": targets}]
    if overlays:
        for layer, target in (("toutiao-route-b", "/data/demo/ttbundle.apk"), ("boatattack", "/data/demo/boat.jar")):
            providers.append({"layer": layer, "interpreter": "python3", "program": pinned, "rollback": pinned, "targets": [target]})
        seal["overlay_deployments"] = [{"id": layer, "state": "active"} for layer in ("toutiao-route-b", "boatattack")]
    deployment = {"schema": "demo-restore-deployment/v1", "execution_enabled": True, "files": members, "providers": providers}
    restore.save(folder / "seal.json", seal)
    restore.save(folder / "deployment.json", deployment)
    observation = {"serial": SERIAL, "boot_before": "known-boot", "boot_after": "known-boot", "errors": [],
                   "files": {target: sha for values in seal["files"].values() for target, sha in values.items()},
                   "system_params": seal["system_params"], "packages": {"org.demo": {"version_code": "3"}}}
    observation["files"][APK] = seal["packages"][0]["apk_sha256"]
    observation["files"][RUNTIME] = "f" * 64
    return seal, deployment, observation


class MockBackend(restore.Backend):
    def __init__(self, folder, seal, deployment, observation):
        output = folder / "logs"
        output.mkdir()
        self.events = []
        self.observation = observation
        self.deployment = deployment
        self.base = folder
        self.boot_change = False
        self.ineffective = False
        self.holder = "cx-t0"
        self.failure = False
        super().__init__(observation["serial"], folder / "seal.json", output, folder / "observation.json")

    def read(self):
        self.events.append("read")
        if self.boot_change and "write" in self.events:
            self.observation.update(boot_before="changed", boot_after="changed")
        restore.save(self.observed, self.observation)
        return super().read()

    def held(self):
        self.events.append("held")
        return self.holder

    def apply(self, provider, program, deployment_path, step):
        self.events.append("write")
        if self.failure:
            raise ValueError("mock provider failed")
        if not self.ineffective:
            for member in self.deployment["files"]:
                if member["target"] in provider["targets"]:
                    self.observation["files"][member["target"]] = restore.digest(restore.expand(member["source"]["path"], self.base))


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.seal, self.deployment, self.observation = fixture(self.folder)
        self.backend = MockBackend(self.folder, self.seal, self.deployment, self.observation)
        self.approval = {"holder": "cx-t0", "boot_id": "known-boot", "valid_until": "2100-01-01T00:00:00+00:00"}

    def run_restore(self, execute=False):
        return restore.restore(self.seal, self.deployment, self.folder / "deployment.json", self.backend, execute, self.approval)

    def test_dry_run_only_reads_and_names_drift(self):
        report = self.run_restore()
        self.assertEqual(self.backend.events, ["read"])
        self.assertEqual(report["remote_write_steps"], 0)
        self.assertEqual(report["before"]["status"], "FAIL")
        self.assertIn(RUNTIME, (self.backend.output / "read-1.stdout.txt").read_text())

    def test_mock_replay_reads_before_writes_and_final_selfcheck_matches(self):
        report = self.run_restore(True)
        self.assertEqual(self.backend.events[0], "read")
        self.assertLess(self.backend.events.index("read"), self.backend.events.index("write"))
        self.assertEqual(report["status"], "restored-selfcheck-equal")
        self.assertEqual(report["after"]["status"], "OFFLINE_MATCH")
        self.assertFalse(report["unlock_attempted"])

    def test_archived_sha_mismatch_rejects_before_read_or_write(self):
        (self.folder / "0.bin").write_bytes(b"drift")
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            self.run_restore(True)
        self.assertEqual(self.backend.events, [])

    def test_document_change_after_precheck_refuses_before_write(self):
        original_held = self.backend.held

        def changed():
            result = original_held()
            restore.save(self.folder / "deployment.json", dict(self.deployment, unexpected="drift"))
            return result

        self.backend.held = changed
        with self.assertRaisesRegex(ValueError, "documents changed"):
            self.run_restore(True)
        self.assertNotIn("write", self.backend.events)

    def test_wrong_sealed_sha_or_incomplete_coverage_rejected(self):
        for change in (lambda value: value["files"][0]["source"].update(sha256="0" * 64),
                       lambda value: value["files"].pop()):
            value = copy.deepcopy(self.deployment)
            change(value)
            with self.assertRaises(ValueError):
                restore.validate(self.seal, value, self.folder)

    def test_immutable_stock_drift_read_failure_and_wrong_holder_do_not_write(self):
        for mutation, reason in ((lambda: self.observation["files"].update({INSTALL: "e" * 64}), "immutable"),
                                 (lambda: self.observation.update(errors=["transport lost"]), "unreliable"),
                                 (lambda: setattr(self.backend, "holder", "other"), "holder")):
            baseline = copy.deepcopy(self.observation)
            mutation()
            with self.assertRaisesRegex(ValueError, reason):
                self.run_restore(True)
            self.assertNotIn("write", self.backend.events)
            self.observation.clear()
            self.observation.update(baseline)
            self.backend.events.clear()

    def test_failed_or_ineffective_provider_does_not_claim_success(self):
        for flag in ("failure", "ineffective"):
            setattr(self.backend, flag, True)
            with self.assertRaises(ValueError):
                self.run_restore(True)
            setattr(self.backend, flag, False)

    def test_cross_boot_refused_even_when_each_individual_read_is_stable(self):
        self.backend.boot_change = True
        with self.assertRaisesRegex(ValueError, "boot changed"):
            self.run_restore(True)

    def test_authorization_exact_object_and_user_only_for_demo_board(self):
        approval = {"schema": "demo-restore-authorization/v1", "authorized": True, "authorized_by": "user",
                    "serial": SERIAL, "seal_sha256": restore.digest(self.folder / "seal.json"),
                    "deployment_sha256": restore.digest(self.folder / "deployment.json"),
                    "valid_until": "2100-01-01T00:00:00+00:00", "holder": "cx-t0"}
        restore.authorize(approval, self.folder / "seal.json", self.folder / "deployment.json", SERIAL, False)
        for field, value in (("authorized_by", "outer(claude)"), ("seal_sha256", "0" * 64),
                             ("valid_until", "2000-01-01T00:00:00+00:00")):
            changed = dict(approval, **{field: value})
            with self.assertRaises(ValueError):
                restore.authorize(changed, self.folder / "seal.json", self.folder / "deployment.json", SERIAL, False)

    def test_actual_wrapper_default_dryrun_and_spare_projection_only(self):
        seal_before = (self.folder / "seal.json").read_bytes()
        observation = dict(self.observation, serial=SPARE)
        restore.save(self.folder / "observed.json", observation)
        result = subprocess.run(["bash", str(restore.REPO / "scripts/lab/demo_restore.sh"),
                                 "--seal", str(self.folder / "seal.json"), "--deployment", str(self.folder / "deployment.json"),
                                 "--serial", SPARE, "--rehearsal", "--observed", str(self.folder / "observed.json"),
                                 "--out", str(self.folder / "cli")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((self.folder / "cli/result.json").read_text())
        self.assertEqual(report["mode"], "dry-run")
        projected = json.loads((self.folder / "cli/serial-projection.json").read_text())
        self.assertEqual(projected, dict(self.seal, serial=SPARE))
        self.assertEqual((self.folder / "seal.json").read_bytes(), seal_before)
        self.assertFalse(report["live_rehearsal_verified"])

    def test_offline_observation_cannot_authorize_execution(self):
        result = subprocess.run(["bash", str(restore.REPO / "scripts/lab/demo_restore.sh"),
                                 "--seal", str(self.folder / "seal.json"), "--deployment", str(self.folder / "deployment.json"),
                                 "--serial", SERIAL, "--execute", "--observed", str(self.folder / "observed.json"),
                                 "--out", str(self.folder / "refused")], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.folder / "refused").exists())

    def test_disabled_unbound_template_refuses(self):
        value = json.loads((restore.HERE / "restore-deployment-template.json").read_text())
        with self.assertRaisesRegex(ValueError, "disabled"):
            restore.validate(self.seal, value, self.folder)

    def test_layer_order_and_all_three_layers_use_one_pipeline(self):
        folder = self.folder / "overlays"
        folder.mkdir()
        seal, deployment, observation = fixture(folder, True)
        backend = MockBackend(folder, seal, deployment, observation)
        report = restore.restore(seal, deployment, folder / "deployment.json", backend, True, self.approval)
        self.assertEqual(report["remote_write_steps"], 3)
        self.assertEqual(report["after"]["status"], "OFFLINE_MATCH")
        deployment["providers"][1:] = list(reversed(deployment["providers"][1:]))
        with self.assertRaisesRegex(ValueError, "layers"):
            restore.validate(seal, deployment, folder)


class RunbookTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((restore.HERE / "runbook-order.json").read_text())
        self.manifest = json.loads((restore.HERE.parent / "demo-manifest.json").read_text())
        self.signoff = json.loads((restore.HERE / "runbook-signoff-input.json").read_text())

    def test_every_exact_lit_key_once_and_ten_lit_games(self):
        expected = {key for key, value in self.signoff["verdicts"].items() if value["verdict"] == "lit"}
        keys = [row["key"] for row in self.report["demo_steps"]]
        self.assertEqual(set(keys), expected)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(self.report["game_keys"]), 10)
        self.assertEqual(self.report["game_keys"], keys[:10])
        self.assertNotIn("fd-stk", keys)
        self.assertNotIn("fd-organicmaps", keys)

    def test_content_first_and_every_skip_points_to_next_entry(self):
        rows = self.report["demo_steps"]
        tiers = [row["tier"] for row in rows]
        self.assertEqual(tiers, sorted(tiers, key=lambda tier: tier != "shown"))
        for index, row in enumerate(rows):
            self.assertTrue(row["fallback"])
            if index + 1 < len(rows):
                self.assertEqual(row["skip_to"], rows[index + 1]["key"])

    def test_appendix_exactly_nonlit_and_runbook_sections(self):
        expected = {key for key, value in self.signoff["verdicts"].items() if value["verdict"] != "lit"}
        self.assertEqual({row["key"] for row in self.report["appendix"]}, expected)
        text = (restore.HERE / "demo-runbook.md").read_text()
        for token in ("10107101", "asx-spawner", "刷新", "文章", "待 PR03 渲染移植验收后补", "fresh", "5a172dd057"):
            self.assertIn(token, text)
        self.assertEqual(text, build_runbook.markdown(self.report))

    def test_two_generations_keep_same_order(self):
        first = build_runbook.build(self.manifest, self.signoff)
        second = build_runbook.build(copy.deepcopy(self.manifest), copy.deepcopy(self.signoff))
        self.assertEqual(first, second)
        saved = {key: value for key, value in self.report.items() if key != "inputs"}
        self.assertEqual(first, saved)


class PublishedDriftTests(unittest.TestCase):
    def test_actual_cli_reports_exact_path_expected_and_actual_sha(self):
        folder = restore.HERE / "fixtures"
        result = subprocess.run(["bash", str(restore.REPO / "scripts/lab/demo_selfcheck.sh"),
                                 "--seal", str(folder / "selfcheck-seal.json"), "--serial", SERIAL,
                                 "--observed", str(folder / "selfcheck-drift.json")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("DRIFT " + RUNTIME + " expected=" + "a" * 64 + " actual=" + "e" * 64, result.stdout)


if __name__ == "__main__":
    unittest.main()
