#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fn01_generation_provenance as provenance  # noqa: E402


BOOT_ID = "11111111-2222-3333-4444-555555555555"


class GenerationProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / "src").mkdir()
        (self.root / "src/input.txt").write_text("source-v1\n", encoding="utf-8")
        (self.root / "scripts").mkdir()
        self.stage = self.root / "scripts/stage.py"
        self.stage.write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "output = Path(sys.argv[1])\n"
            "output.parent.mkdir(parents=True, exist_ok=True)\n"
            "output.write_bytes(sys.argv[2].encode())\n",
            encoding="utf-8",
        )
        self.config_path = self.root / "config.json"
        self.run_dir = self.root / "var/evidence/run"
        self.config = {
            "schema_version": provenance.CONFIG_SCHEMA,
            "action_id": "Fn01.A04",
            "target": {
                "os": "OpenHarmony",
                "version": "6.1.0.31",
                "arch": "AArch64",
            },
            "source_paths": ["src", "scripts/stage.py"],
            "builder_identity_probes": [
                {
                    "name": "python_version",
                    "command": [sys.executable, "--version"],
                }
            ],
            "stages": [
                {
                    "name": "host_test",
                    "scope": "host",
                    "command": [
                        sys.executable,
                        "scripts/stage.py",
                        "out/host.bin",
                        "host-result",
                    ],
                },
                {
                    "name": "target_build",
                    "scope": "target",
                    "command": [
                        sys.executable,
                        "scripts/stage.py",
                        "out/target.bin",
                        "target-result",
                    ],
                },
            ],
            "artifacts": [
                {
                    "role": "target_binary",
                    "kind": "file",
                    "local_path": "out/target.bin",
                    "device_path": "/system/test/target.bin",
                    "producer_stage": "target_build",
                }
            ],
        }
        self.write_config()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_config(self) -> None:
        self.config_path.write_text(
            json.dumps(self.config, sort_keys=True), encoding="utf-8"
        )

    def build(self) -> dict:
        return provenance.produce_build_receipt(
            self.root, self.config_path, self.run_dir
        )

    def make_device_receipt(
        self, build: dict, *, deployed_sha: str | None = None
    ) -> tuple[Path, dict]:
        build_path = self.run_dir / "build-receipt.json"
        identity_path = self.run_dir / "generation-identity.json"
        closure_path = self.run_dir / "closure-manifest.sha256"
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        artifact = build["artifacts"][0]
        receipt = {
            "schema_version": provenance.DEVICE_SCHEMA,
            "action_id": build["action_id"],
            "generation_id": build["generation_id"],
            "captured_at": provenance.utc_now(),
            "build_receipt": {
                "path": str(build_path),
                "sha256": provenance.sha256_file(build_path),
                "body_sha256": build["receipt_body_sha256"],
            },
            "generation_identity": {
                "path": str(identity_path),
                "sha256": provenance.sha256_file(identity_path),
                "body_sha256": identity["receipt_body_sha256"],
            },
            "closure_manifest": {
                "path": str(closure_path),
                "sha256": provenance.sha256_file(closure_path),
            },
            "collector": {
                "hdc_path": "/fixture/hdc",
                "hdc_sha256": "1" * 64,
                "hdc_version": "fixture",
            },
            "device": {
                "serial": "fixture-serial",
                "boot_id_before": BOOT_ID,
                "boot_id_after": BOOT_ID,
                "os_version": "OpenHarmony 6.1.0.31",
                "security_mode": "Enforcing",
            },
            "deployed_artifacts": [
                {
                    "role": artifact["role"],
                    "device_path": artifact["device_path"],
                    "sha256": deployed_sha or artifact["sha256"],
                    "bytes": artifact["bytes"],
                }
            ],
            "status": {
                "read_only_capture_complete": True,
                "target_deployment_generation_bound": False,
                "device_verified": False,
                "formal_verdict": "NOT_ISSUED",
            },
            "semantics": {
                "capture_performed_no_deployment": True,
                "deployment_byte_match_is_not_action_behavior_verification": True,
            },
        }
        provenance.add_body_digest(receipt)
        path = self.run_dir / "device-receipt.json"
        provenance.write_json(path, receipt)
        return path, receipt

    def test_build_and_exact_device_match_pass_provenance_only(self) -> None:
        build = self.build()
        device_path, _ = self.make_device_receipt(build)
        report = provenance.gate_report(
            self.root,
            self.run_dir / "build-receipt.json",
            device_path,
            "fixture-serial",
        )
        self.assertEqual(report["gate_status"], "PASS")
        self.assertTrue(report["status"]["target_deployment_generation_bound"])
        self.assertFalse(report["status"]["device_verified"])
        self.assertEqual(report["status"]["formal_verdict"], "NOT_ISSUED")

    def test_device_hash_mismatch_fails(self) -> None:
        build = self.build()
        device_path, _ = self.make_device_receipt(build, deployed_sha="0" * 64)
        report = provenance.gate_report(
            self.root, self.run_dir / "build-receipt.json", device_path
        )
        self.assertEqual(report["gate_status"], "FAIL")
        self.assertIn(
            "DEPLOYED_SHA_MISMATCH",
            {failure["code"] for failure in report["failures"]},
        )
        self.assertFalse(report["status"]["device_verified"])

    def test_current_source_drift_fails(self) -> None:
        build = self.build()
        device_path, _ = self.make_device_receipt(build)
        (self.root / "src/input.txt").write_text("source-v2\n", encoding="utf-8")
        report = provenance.gate_report(
            self.root, self.run_dir / "build-receipt.json", device_path
        )
        self.assertEqual(report["gate_status"], "FAIL")
        self.assertIn(
            "CURRENT_LOCAL_STATE_MISMATCH",
            {failure["code"] for failure in report["failures"]},
        )

    def test_source_change_during_build_is_rejected(self) -> None:
        mutator = self.root / "scripts/mutate.py"
        mutator.write_text(
            "from pathlib import Path\n"
            "Path('src/input.txt').write_text('changed-during-build\\n')\n"
            "Path('out').mkdir(exist_ok=True)\n"
            "Path('out/target.bin').write_bytes(b'target-result')\n",
            encoding="utf-8",
        )
        self.config["source_paths"].append("scripts/mutate.py")
        self.config["stages"][1]["command"] = [sys.executable, "scripts/mutate.py"]
        self.write_config()
        with self.assertRaisesRegex(provenance.ProvenanceError, "source closure changed"):
            self.build()

    def test_stage_failure_writes_failure_not_build_receipt(self) -> None:
        self.config["stages"][1]["command"] = [
            sys.executable,
            "-c",
            "raise SystemExit(7)",
        ]
        self.write_config()
        with self.assertRaisesRegex(provenance.ProvenanceError, "rc=7"):
            self.build()
        self.assertTrue((self.run_dir / "build-failure.json").is_file())
        self.assertFalse((self.run_dir / "build-receipt.json").is_file())

    def test_tampered_build_receipt_is_rejected(self) -> None:
        self.build()
        build_path = self.run_dir / "build-receipt.json"
        value = json.loads(build_path.read_text(encoding="utf-8"))
        value["target"]["version"] = "tampered"
        provenance.write_json(build_path, value)
        with self.assertRaisesRegex(provenance.ProvenanceError, "body digest mismatch"):
            provenance.validate_build_receipt(provenance.load_json(build_path))

    def test_tampered_sealed_artifact_breaks_closure(self) -> None:
        build = self.build()
        sealed = self.root / build["artifacts"][0]["local_path"]
        sealed.write_bytes(b"tampered")
        with self.assertRaisesRegex(
            provenance.ProvenanceError, "closure member hash mismatch"
        ):
            provenance.verify_generation_closure(
                self.run_dir / "build-receipt.json", build
            )

    def test_generation_identity_rejects_caller_hash_rewrite(self) -> None:
        build = self.build()
        identity_path = self.run_dir / "generation-identity.json"
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        identity["artifacts"][0]["sha256"] = "0" * 64
        del identity["receipt_body_sha256"]
        provenance.add_body_digest(identity)
        provenance.write_json(identity_path, identity)
        (self.run_dir / "generation-identity.sha256").write_text(
            f"{provenance.sha256_file(identity_path)}  generation-identity.json\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            provenance.ProvenanceError, "identity artifact mismatch"
        ):
            provenance.verify_generation_closure(
                self.run_dir / "build-receipt.json", build
            )

    def test_capture_device_is_read_only_and_binds_boot(self) -> None:
        build = self.build()
        artifact = build["artifacts"][0]
        fake_hdc = self.root / "fake-hdc"
        fake_hdc.write_text(
            "#!/bin/sh\n"
            "if [ \"$1 $2\" = \"list targets\" ]; then echo fixture-serial; exit 0; fi\n"
            "if [ \"$1\" = \"-v\" ]; then echo 'hdc fixture 1'; exit 0; fi\n"
            "cmd=\"$4\"\n"
            f"case \"$cmd\" in\n"
            f"  'cat /proc/sys/kernel/random/boot_id') echo '{BOOT_ID}' ;;\n"
            "  'param get const.product.software.version 2>/dev/null || param get const.ohos.fullname') echo 'OpenHarmony 6.1.0.31' ;;\n"
            "  'getenforce 2>/dev/null || cat /sys/fs/selinux/enforce') echo 'Enforcing' ;;\n"
            f"  'stat -c %s /system/test/target.bin') echo '{artifact['bytes']}' ;;\n"
            f"  'sha256sum /system/test/target.bin') echo '{artifact['sha256']}  /system/test/target.bin' ;;\n"
            "  *) echo \"unexpected:$cmd\" >&2; exit 9 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_hdc.chmod(fake_hdc.stat().st_mode | stat.S_IXUSR)
        output = self.run_dir / "captured-device.json"
        receipt = provenance.capture_device_receipt(
            self.run_dir / "build-receipt.json",
            "fixture-serial",
            fake_hdc,
            output,
        )
        self.assertTrue(output.is_file())
        self.assertEqual(receipt["device"]["boot_id_before"], BOOT_ID)
        self.assertTrue(receipt["semantics"]["capture_performed_no_deployment"])
        self.assertFalse(receipt["status"]["device_verified"])

    def test_config_rejects_artifact_without_producer(self) -> None:
        invalid = copy.deepcopy(self.config)
        invalid["artifacts"][0]["producer_stage"] = "missing_stage"
        with self.assertRaisesRegex(provenance.ProvenanceError, "unknown producer"):
            provenance.validate_config(invalid, self.root)


if __name__ == "__main__":
    unittest.main()
