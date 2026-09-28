#!/usr/bin/env python3
"""Fail-closed tests for the HelloWorld P0 deploy preflight."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "src/tools/experiments/d600/deploy_fn01_fn03_r18_runtime_d600.sh"
APK = (
    ROOT
    / "var/evidence/runs/helloworld-hanbing-v2-cfi-schema-r4-20260724"
    / "artifacts/HelloWorld.apk"
)
APK_SHA256 = "2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
GENERATION_ID = "1" * 64
SKIA_PROVIDER_SHA256 = (
    "caa86d58671eef0079cdcfa60cf943c6cda6ee7934ecfdf59bf37df754a2abe4"
)


ROLE_PATHS = {
    "appspawn": "appspawn-x",
    "appspawn_config": "appspawn_x.cfg",
    "sandbox_config": "appdata-sandbox.json",
    "hap_domain_wrapper": "system/lib64/libwestlake_hap_domain_wrapper.so",
    "route_a_child_plugin": "system/lib64/appspawn/libwestlake_android_child.z.so",
    "art": "system/android/lib64/libart.so",
    "route_a_runtime_provider": (
        "system/android/lib64/libwestlake_android_runtime_provider.so"
    ),
    "android_runtime": "system/android/lib64/liboh_android_runtime.so",
    "adapter_bridge": "system/android/lib64/liboh_adapter_bridge.so",
    "hwui": "system/android/lib64/libhwui.so",
    "hwui_shim": "system/android/lib64/liboh_hwui_shim.so",
    "skia_rtti_shim": "system/android/lib64/liboh_skia_rtti_shim.so",
    "androidfw": "system/android/lib64/libandroidfw.so",
    "minikin": "system/android/lib64/libminikin.so",
    "profile": "system/android/lib64/libprofile.so",
    "unwindstack": "system/android/lib64/libunwindstack.so",
    "fonts_config": "system/android/etc/fonts.xml",
    "framework_jar": "system/android/framework/oh-adapter-framework.jar",
    "boot_art": "system/android/framework/arm64/boot.art",
    "boot_oat": "system/android/framework/arm64/boot.oat",
    "boot_vdex": "system/android/framework/arm64/boot.vdex",
    "appms": "system/lib64/libappms.z.so",
    "appspawn_client": "system/lib64/libappspawn_client.z.so",
    "bms": "system/lib64/libbms.z.so",
    "installs": "system/lib64/libinstalls.z.so",
    "apk_installer": "system/lib64/libapk_installer.so",
    "abilityms": "system/lib64/platformsdk/libabilityms.z.so",
    "lzma": "system/android/lib64/liblzma.so",
    "shared_libz": "system/android/lib64/libshared_libz.z.so",
    "thread_guard_registry": (
        "system/android/lib64/libwestlake_thread_guard_registry.so"
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def destinations(role: str, relative_path: str) -> list[str]:
    if relative_path.startswith("system/android/"):
        return [f"/{relative_path}"]
    mappings = {
        "appspawn": ["/system/bin/appspawn-x"],
        "appspawn_config": ["/system/etc/init/appspawn_x.cfg"],
        "sandbox_config": ["/system/etc/sandbox/appdata-sandbox.json"],
        "hap_domain_wrapper": ["/system/lib64/libwestlake_hap_domain_wrapper.so"],
        "route_a_child_plugin": [
            "/system/lib64/appspawn/libwestlake_android_child.z.so"
        ],
        "appms": [
            "/system/lib64/libappms.z.so",
            "/system/lib64/platformsdk/libappms.z.so",
        ],
        "appspawn_client": [
            "/system/lib64/libappspawn_client.z.so",
            "/system/lib64/platformsdk/libappspawn_client.z.so",
        ],
        "bms": [
            "/system/lib64/libbms.z.so",
            "/system/lib64/platformsdk/libbms.z.so",
        ],
        "installs": [
            "/system/lib64/libinstalls.z.so",
            "/system/lib64/platformsdk/libinstalls.z.so",
        ],
        "apk_installer": [
            "/system/lib64/libapk_installer.so",
            "/system/lib64/platformsdk/libapk_installer.so",
        ],
        "abilityms": ["/system/lib64/platformsdk/libabilityms.z.so"],
    }
    return mappings[role]


class DeployFixture:
    def __init__(self, base: Path) -> None:
        self.candidate_root = base / "candidate"
        self.manifest_path = base / "deploy-manifest.json"
        self.hashes_path = base / "expected-hashes.json"
        self.candidate_root.mkdir()

        artifacts = []
        candidate_files = {}
        for role, relative_path in ROLE_PATHS.items():
            path = self.candidate_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"fixture:{role}\n".encode())
            digest = sha256(path)
            candidate_files[relative_path] = digest
            artifacts.append(
                {
                    "role": role,
                    "path": relative_path,
                    "destinations": destinations(role, relative_path),
                    "sha256": digest,
                }
            )

        namespace_sha = "a" * 64
        self.manifest = {
            "schema_version": "bridge.helloworld-p0.deploy.v1",
            "generation_id": GENERATION_ID,
            "apk": {
                "sha256": APK_SHA256,
                "package_name": "com.example.helloworld",
                "activity_name": "com.example.helloworld.MainActivity",
            },
            "artifacts": artifacts,
            "skia_provider": {
                "device_path": "/system/lib64/libskia_canvaskit.z.so",
                "sha256": SKIA_PROVIDER_SHA256,
                "soname": "libskia_canvaskit.z.so",
                "policy": "PRESERVE_DEVICE_BASELINE",
            },
            "namespace_manifest": {
                "device_path": "/system/etc/ld-musl-namespace-aarch64.ini",
                "sha256": namespace_sha,
                "selected_section": "systemscence",
                "provider_search_paths": ["/system/lib64"],
                "mutation": "UNCHANGED",
            },
        }
        self.hashes = {
            "schema_version": "bridge.helloworld-p0.expected-hashes.v1",
            "generation_id": GENERATION_ID,
            "apk_sha256": APK_SHA256,
            "candidate_files": candidate_files,
            "device_files": {
                "/system/lib64/libskia_canvaskit.z.so": SKIA_PROVIDER_SHA256,
                "/system/etc/ld-musl-namespace-aarch64.ini": namespace_sha,
                "/system/lib/ld-musl-aarch64.so.1": (
                    "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2"
                ),
            },
        }
        self.write()

    def write(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.hashes_path.write_text(
            json.dumps(self.hashes, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def run(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(SCRIPT),
                "--p0",
                "--serial",
                "fixture-d600",
                "--candidate-root",
                str(self.candidate_root),
                "--apk",
                str(APK),
                "--deploy-manifest",
                str(self.manifest_path),
                "--expected-hashes",
                str(self.hashes_path),
                "--preflight-only",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )


class DeployHelloWorldGenerationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = DeployFixture(Path(self.tempdir.name))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def assert_rejected(self, code: str) -> None:
        result = self.fixture.run()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(code, result.stderr + result.stdout)

    def test_accepts_exact_same_generation_preflight_without_hdc(self) -> None:
        result = self.fixture.run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"P0_PREFLIGHT_OK generation_id={GENERATION_ID}", result.stdout)

    def test_rejects_mixed_generation(self) -> None:
        self.fixture.hashes["generation_id"] = "2" * 64
        self.fixture.write()
        self.assert_rejected("MIXED_GENERATION")

    def test_rejects_missing_skia_provider_contract(self) -> None:
        del self.fixture.manifest["skia_provider"]
        self.fixture.write()
        self.assert_rejected("MISSING_SKIA_PROVIDER")

    def test_rejects_wrong_namespace_manifest(self) -> None:
        self.fixture.manifest["namespace_manifest"]["selected_section"] = "default"
        self.fixture.write()
        self.assert_rejected("INVALID_NAMESPACE_MANIFEST")

    def test_rejects_candidate_hash_drift(self) -> None:
        bridge = self.fixture.candidate_root / ROLE_PATHS["adapter_bridge"]
        bridge.write_bytes(b"mixed bridge from another generation\n")
        self.assert_rejected("CANDIDATE_HASH_MISMATCH")

    def test_rejects_attempt_to_deploy_skia_provider(self) -> None:
        relative_path = "system/android/lib64/libskia_canvaskit.z.so"
        provider = self.fixture.candidate_root / relative_path
        provider.write_bytes(b"link stub must never become the device provider\n")
        digest = sha256(provider)
        self.fixture.manifest["artifacts"].append(
            {
                "role": "skia_provider",
                "path": relative_path,
                "destinations": ["/system/lib64/libskia_canvaskit.z.so"],
                "sha256": digest,
            }
        )
        self.fixture.hashes["candidate_files"][relative_path] = digest
        self.fixture.write()
        self.assert_rejected("PROVIDER_MUST_NOT_BE_DEPLOYED")


if __name__ == "__main__":
    unittest.main()
