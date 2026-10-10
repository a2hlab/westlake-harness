import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("boat_port", HERE / "collect.py")
PORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PORT)


class PortTests(unittest.TestCase):
    def setUp(self):
        self.source = (HERE / "source/android_graphics_compat_shim.cpp").read_text()
        self.changed = PORT.transform(self.source)

    def test_exact_instruction_and_byte_coverage(self):
        rows = json.loads((HERE / "instruction-deltas.json").read_text())
        self.assertEqual(len(rows), 13)
        self.assertEqual(sum(row["changed_bytes"] for row in rows), 47)
        self.assertEqual({row["function"] for row in rows}, set(PORT.FUNCTIONS) - {"BBQ_nativeGetSurface"})
        expected = {
            "0x407a0": "nop", "0x40a04": "nop",
            "0x40c08": "cbz\tw21, 0x40c20 <ANativeWindow_setBuffersGeometry+0x50>",
            "0x41e8c": "mov\tw2, w20", "0x41e94": "mov\tw3, w19",
            "0x41e98": "mov\tw26, w20", "0x41e9c": "mov\tw27, w19",
        }
        for row in rows:
            if row["pc"] in expected:
                self.assertEqual(row["after"]["assembly"], expected[row["pc"]])

    def test_all_four_behaviors_absent_in_u13(self):
        rows = json.loads((HERE / "semantic-deltas.json").read_text())["rows"]
        self.assertEqual([row["u13_already_present"] for row in rows], [False, False, False, False, True])
        self.assertIn('nwfs_apply_window_geometry(nw, "BBQ.update-stamp", b->width, b->height);', self.changed)
        self.assertNotIn('int32_t w = 1200, h = 1920;', self.changed)

    def test_seed_and_from_surface_do_not_mutate(self):
        helper = self.changed.split('extern "C" void nwfs_seed_window_geometry(void* nw, const char* where) {', 1)[1].split('\n}', 1)[0]
        self.assertNotIn("NativeWindowHandleOpt", helper)
        self.assertIn("PRESERVE_BUFFER_GEOMETRY", helper)
        self.assertIn('nwfs_seed_window_geometry(reinterpret_cast<void*>(nativeObj), "STAGE0-handoff");', self.changed)
        self.assertIn('nwfs_seed_window_geometry(nw, "BBQ.getSurface-lazy");', self.changed)

    def test_exact_width_zero_guard_not_positive_or_height_guard(self):
        geometry = self.changed.split('extern "C" int32_t ANativeWindow_setBuffersGeometry(', 1)[1].split('\n}', 1)[0]
        self.assertIn("if (width != 0)", geometry)
        self.assertNotIn("if (height", geometry)
        self.assertNotIn("width > 0", geometry)
        self.assertIn("int32_t rc = 0;", geometry)
        self.assertIn("if (!w) return -1;", geometry)
        self.assertIn("return 0;", geometry)
        self.assertIn("NativeWindowHandleOpt(oh, OH_OP_SET_FORMAT, ohFormat);", geometry)

    def test_preserve_m1_jni_and_format_mapping(self):
        start = self.source.index("void BBQ_nativeUpdate(")
        end = self.source.index('    nwfs_seed_window_geometry(nw, "BBQ.update-stamp");', start)
        self.assertIn(self.source[start:end], self.changed)
        for function in ("android_view_Surface_createFromIGraphicBufferProducer", "androidToOHPixelFormat", "register_android_database_SQLiteConnection"):
            self.assertEqual(self.source.count(function), self.changed.count(function))
        methods = 'const JNINativeMethod kBlastBufferQueueMethods[] = {'
        self.assertEqual(self.source.split(methods, 1)[1].split('};', 1)[0],
                         self.changed.split(methods, 1)[1].split('};', 1)[0])
        self.assertIn("static void nwfs_apply_window_geometry", self.changed)

    def test_bridge_already_correct(self):
        rows = json.loads((HERE / "class-name-check.json").read_text())
        for row in rows:
            self.assertEqual(row["counts"]["187"], {"correct": 1, "wrong": 0})
            self.assertEqual(row["counts"]["9cc"], {"correct": 0, "wrong": 1})
            self.assertEqual(row["counts"]["adc"], {"correct": 1, "wrong": 0})

    def test_source_drift_refused(self):
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            PORT.transform(self.source + "\n")

    def test_draft_applies_to_exact_source_without_build(self):
        self.assertEqual(PORT.patch_text(self.source), (HERE / "u13-geometry-draft.patch").read_text())
        with tempfile.TemporaryDirectory(prefix="boat-port-test-") as directory:
            root = Path(directory)
            (root / "android_graphics_compat_shim.cpp").write_text(self.source)
            result = subprocess.run(["git", "apply", "--check", str(HERE / "u13-geometry-draft.patch")], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
