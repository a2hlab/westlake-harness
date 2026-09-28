#!/usr/bin/env python3

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import artifact_cache


def digest(number: int) -> str:
    return hashlib.sha256(str(number).encode("ascii")).hexdigest()


class ArtifactCacheTest(unittest.TestCase):
    def component_values(self):
        return {
            name: "sha256:" + digest(index)
            for index, name in enumerate(artifact_cache.COMPONENTS)
        }

    def write_key(self, root: Path):
        manifest = artifact_cache.make_key_manifest(self.component_values())
        path = root / "key.json"
        path.write_bytes(artifact_cache._canonical_json(manifest))
        return manifest, path

    def make_bundle(self, root: Path):
        bundle = root / "bundle"
        (bundle / "lib64").mkdir(parents=True)
        (bundle / "lib64" / "libbridge.so").write_bytes(b"bridge-so")
        apk = bundle / "HelloWorld.apk"
        apk.write_bytes(b"apk")
        manifest, key_path = self.write_key(root)
        key, manifest_sha = artifact_cache.seal_bundle(bundle, key_path)
        return bundle, manifest, key, manifest_sha

    def test_generation_key_uses_all_six_components(self):
        baseline = artifact_cache.make_key_manifest(self.component_values())
        self.assertEqual(
            list(baseline["components"].keys()), list(artifact_cache.COMPONENTS)
        )
        for index, name in enumerate(artifact_cache.COMPONENTS, start=100):
            changed = self.component_values()
            changed[name] = "sha256:" + digest(index)
            candidate = artifact_cache.make_key_manifest(changed)
            self.assertNotEqual(
                baseline["generation_key"], candidate["generation_key"], name
            )

    def test_component_tree_digest_is_content_and_mode_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            file_path = source / "main.cc"
            file_path.write_text("int main() {}\n", encoding="utf-8")
            first = artifact_cache.digest_component_path(str(source))
            file_path.write_text("int main() { return 1; }\n", encoding="utf-8")
            second = artifact_cache.digest_component_path(str(source))
            self.assertNotEqual(first, second)
            file_path.chmod(0o755)
            third = artifact_cache.digest_component_path(str(source))
            self.assertNotEqual(second, third)

    def test_seal_verify_and_tamper_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle, manifest, key, manifest_sha = self.make_bundle(Path(temp))
            verified = artifact_cache.verify_bundle(bundle, key, manifest_sha)
            self.assertEqual(verified["components"], manifest["components"])
            (bundle / "HelloWorld.apk").write_bytes(b"tampered")
            with self.assertRaisesRegex(
                artifact_cache.ArtifactCacheError, "differs"
            ):
                artifact_cache.verify_bundle(bundle, key, manifest_sha)

    def test_extra_payload_and_checksum_rewrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle, _, key, manifest_sha = self.make_bundle(Path(temp))
            (bundle / "unexpected.bin").write_bytes(b"unexpected")
            with self.assertRaises(artifact_cache.ArtifactCacheError):
                artifact_cache.verify_bundle(bundle, key, manifest_sha)
            (bundle / "unexpected.bin").unlink()
            checksum = bundle / artifact_cache.CHECKSUM_NAME
            checksum.write_text(
                checksum.read_text(encoding="utf-8") + ("0" * 64) + "  ghost\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                artifact_cache.ArtifactCacheError, "SHA256SUMS"
            ):
                artifact_cache.verify_bundle(bundle, key, manifest_sha)

    def test_expected_manifest_sha_is_an_external_integrity_anchor(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle, _, key, _ = self.make_bundle(Path(temp))
            with self.assertRaisesRegex(
                artifact_cache.ArtifactCacheError, "manifest SHA-256 mismatch"
            ):
                artifact_cache.verify_bundle(bundle, key, digest(999))

    def test_artifact_traversal_and_local_layout_symlink_are_rejected(self):
        with self.assertRaisesRegex(
            artifact_cache.ArtifactCacheError, "may not traverse"
        ):
            artifact_cache._validate_artifact_relative("../outside")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "local-cache"
            outside = Path(temp) / "outside"
            outside.mkdir()
            root.mkdir()
            (root / "generations").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(
                artifact_cache.ArtifactCacheError, "may not use symlinks"
            ):
                artifact_cache._ensure_local_layout(root)

    def test_local_prune_keeps_current_and_hot_apks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "local-cache"
            generations, _, hot = artifact_cache._ensure_local_layout(root)
            current = "gk1-" + digest(200)
            stale = "gk1-" + digest(201)
            (generations / current).mkdir()
            (generations / stale).mkdir()
            (hot / "G7.apk").write_bytes(b"hot")
            artifact_cache._write_current(root, current)
            removed = artifact_cache.prune_local(root)
            self.assertEqual(removed, [stale])
            self.assertTrue((generations / current).is_dir())
            self.assertEqual((hot / "G7.apk").read_bytes(), b"hot")

    def test_store_config_forbids_mounts_and_pending_readiness(self):
        config_path = (
            Path(__file__).resolve().parents[1]
            / "infra"
            / "demo-artifact-cache.json"
        )
        config = artifact_cache.load_config(config_path)
        self.assertEqual(config["transport"], "rsync+ssh")
        self.assertEqual(
            config["canonical_main"],
            "01ba9e49a92eb8f181660ff19ba6155f46b27f1c",
        )
        self.assertEqual(config["direct_test_transport"], "forbidden")
        self.assertEqual(
            artifact_cache._store(config, "primary")["role"],
            "primary_artifact_store",
        )
        pending = copy.deepcopy(config)
        pending["stores"]["primary"]["readiness"] = "pending_c01"
        with self.assertRaisesRegex(
            artifact_cache.ArtifactCacheError, "not ready"
        ):
            artifact_cache._store(pending, "primary")
        self.assertEqual(
            artifact_cache._store(config, "linux_cache")["role"], "linux_cache"
        )

    def test_schema_has_exact_generation_components(self):
        schema_path = (
            Path(__file__).resolve().parents[1]
            / "spec"
            / "workflow"
            / "artifact-generation.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        components = schema["properties"]["components"]
        self.assertEqual(components["required"], list(artifact_cache.COMPONENTS))
        self.assertFalse(components["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
