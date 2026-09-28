#!/usr/bin/env python3
"""Focused host tests for the HelloWorld generation packager."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("package_helloworld_generation.py")
SPEC = importlib.util.spec_from_file_location("package_helloworld_generation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PruneSystemAndroidTests(unittest.TestCase):
    def test_prunes_unselected_file_and_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "candidate"
            selected = candidate / "system/android/lib64/libart.so"
            unselected = candidate / "system/android/lib64/compiler/libart-compiler.so"
            selected.parent.mkdir(parents=True)
            unselected.parent.mkdir(parents=True)
            selected.write_bytes(b"runtime")
            unselected.write_bytes(b"compiler")

            MODULE.prune_unselected_system_android(
                candidate, {"system/android/lib64/libart.so"}
            )

            self.assertEqual(selected.read_bytes(), b"runtime")
            self.assertFalse(unselected.exists())
            self.assertFalse(unselected.parent.exists())

    def test_requires_canonical_sha256(self) -> None:
        digest = "a" * 64
        self.assertEqual(MODULE.require_sha256(digest, "fixture"), digest)
        for invalid in ("", "A" * 64, "a" * 63, "g" * 64):
            with self.assertRaises(ValueError):
                MODULE.require_sha256(invalid, "fixture")

    def test_cold_config_rejects_parent_preload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "appspawn_x.cfg"
            payload = {
                "services": [{
                    "name": "appspawn-x",
                    "env": [{"name": "LD_PRELOAD", "value": "liblzma.so"}],
                }]
            }
            config.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "forbids appspawn-x LD_PRELOAD"):
                MODULE.require_cold_appspawn_config(config)

            payload["services"][0]["env"] = [
                {"name": "LD_LIBRARY_PATH", "value": "/system/android/lib64"}
            ]
            config.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(MODULE.require_cold_appspawn_config(config), config)


if __name__ == "__main__":
    unittest.main()
