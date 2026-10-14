import importlib.util
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "sources/api-implementations/shared-native-production"
sys.path.insert(0, str(SOURCE))
from acquire import verify
from build_provider import provider_commands
from restore_provider_inputs import mapped_name, restore
from materialize import materialize


class VerifiedNativeSourceTests(unittest.TestCase):
    def test_archive_sha_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.tar.gz"
            path.write_bytes(b"not the source")
            with self.assertRaisesRegex(ValueError, "SHA_MISMATCH"):
                verify(path, "0" * 64)

    def test_generation_commands_preserve_original_flags(self):
        commands = provider_commands(Path("/new/generation"), Path("/new/output"), SOURCE)
        self.assertEqual(len(commands), 2)
        self.assertIn("--target=aarch64-linux-ohos", commands[0])
        self.assertIn("-Wl,--no-undefined", commands[1])
        self.assertEqual(commands[0][commands[0].index("-c") + 1], "/new/generation/adapter/framework/appspawn-x/src/child_main_after_stock.cpp")
        self.assertEqual(commands[1][commands[1].index("-o") + 1], "/new/output/libwestlake_android_runtime_provider.so")
        self.assertFalse(any("/Users/" in value and not value.startswith(str(SOURCE)) for command in commands for value in command))

    def test_source_contains_real_frozen_implementations(self):
        provider = (SOURCE / "FZ-002/src/child_main_after_stock.cpp").read_text()
        asset = (SOURCE / "FZ-003/src/android_util_AssetManager_aosp.cpp").read_text()
        installer = (SOURCE / "FZ-001/archive-source/base_bundle_installer.cpp").read_text()
        self.assertIn("pthread_attr_setstacksize", provider)
        self.assertIn("[CM-BIGSTACK]", provider)
        self.assertIn("ParcelFileDescriptor", asset)
        self.assertTrue("PreAuthorizationInfo bgPreAuth" in installer, "actual BMS preauthorization implementation absent")

    def test_archive_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "TRAVERSAL"):
            mapped_name("b68-generation/../../escape", "b68-generation")

    def test_unrelated_archive_root_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_ARCHIVE_ROOT"):
            mapped_name("arbitrary/file", "b68-generation")

    def test_exact_auxiliary_header_roots(self):
        name = "prefix/.bridge-payload/oh-source-inputs/global_resource_management/interfaces/inner_api/include/res_common.h"
        self.assertEqual(mapped_name(name, "b68-generation"), "_external/global_resource_management/interfaces/inner_api/include/res_common.h")
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_ARCHIVE_ROOT"):
            mapped_name(name.replace("res_common.h", "unlisted.h"), "b68-generation")
        with self.assertRaisesRegex(ValueError, "TRAVERSAL"):
            mapped_name(name.replace("res_common.h", "../res_common.h"), "b68-generation")

    def test_archive_link_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as stream:
                member = tarfile.TarInfo("prefix/b68-generation/tool")
                member.type = tarfile.SYMTYPE
                member.linkname = "../../external"
                stream.addfile(member)
            output = root / "output"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "LINK_ESCAPE"):
                restore(archive, output, "b68-generation")

    def test_inventory_does_not_claim_historical_production(self):
        lock = json.loads((SOURCE / "dependencies.lock.json").read_text())
        self.assertEqual({row["id"] for row in lock["unresolved"]}, {"bridge8ab", "libandroid9cc_ADC", "FZ003"})
        self.assertTrue(all(len(row["sha256"]) == 64 for row in lock["archives"]))

    def test_exact_original_bytes_materialized(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = materialize("FZ-001/archive-source/adapter", Path(directory) / "adapter")
            self.assertGreater(len(rows), 100)
            index = json.loads((SOURCE / "source-index.json").read_text())["files"]
            original = {row["path"].split("FZ-001/archive-source/adapter/", 1)[1]: row["origin_sha256"] for row in index if row["path"].startswith("FZ-001/archive-source/adapter/")}
            self.assertEqual({row["path"]: row["sha256"] for row in rows}, original)


if __name__ == "__main__":
    unittest.main()
