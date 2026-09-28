#!/usr/bin/env python3

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


SCRIPT = Path(__file__).with_name("check_implementation_provenance.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ImplementationProvenanceTest(unittest.TestCase):
    def fixture(self) -> tuple[Path, Path, dict]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        paths = [
            "docs/spec/project.yaml",
            "docs/spec/concepts/Fn02/route-instance.yaml",
            "docs/spec/atoms/Fn02/A03/DESIGN_SPEC.md",
            "docs/spec/atoms/Fn02/A03/atom.yaml",
            "docs/atoms/Fn02/A03/IMPLEMENTATION_HANDOFF.md",
            "docs/progress.md",
            "var/evidence/atoms/Fn02/A03/build/build.log",
            "src/adapter/example.cpp",
            "src/atoms/Fn02/A03/IMPLEMENTATION.yaml",
        ]
        for value in paths:
            path = root / value
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture {value}\n", encoding="utf-8")
        (root / "docs/spec/project.yaml").write_text(
            yaml.safe_dump(
                {
                    "implementation_provenance_policy": {
                        "policy_id": "BR-IMPLEMENTATION-PROVENANCE-1",
                        "project_root": str(root),
                    }
                }
            ),
            encoding="utf-8",
        )
        strategy = root / "docs/spec/concepts/Fn02/route-instance.yaml"
        design = root / "docs/spec/atoms/Fn02/A03/DESIGN_SPEC.md"
        manifest = {
            "schema_version": "1.0",
            "action_id": "Fn02.A03",
            "changed_files": ["src/adapter/example.cpp"],
            "implementation_provenance": {
                "policy_id": "BR-IMPLEMENTATION-PROVENANCE-1",
                "derivation": "GENERATED_FROM_PROJECT_STRATEGY_AND_ACTION_DESIGN",
                "all_product_code_within_project": True,
                "external_code_as_implementation": False,
                "remote_source_import": False,
                "use_case_ids": ["F02-H01"],
                "strategy_path": "docs/spec/concepts/Fn02/route-instance.yaml",
                "strategy_sha256": sha(strategy),
                "action_design_path": "docs/spec/atoms/Fn02/A03/DESIGN_SPEC.md",
                "action_design_sha256": sha(design),
                "derivation_statement": "Implementation was newly derived from the project Strategy and frozen Action Design without external coding input.",
                "paired_changes": {
                    "spec": ["docs/spec/atoms/Fn02/A03/atom.yaml"],
                    "docs": ["docs/atoms/Fn02/A03/IMPLEMENTATION_HANDOFF.md"],
                    "implementation_handoff": ["src/atoms/Fn02/A03/IMPLEMENTATION.yaml"],
                    "evidence": ["var/evidence/atoms/Fn02/A03/build/build.log"],
                    "progress": ["docs/progress.md"],
                },
            },
        }
        manifest_path = root / "src/atoms/Fn02/A03/IMPLEMENTATION.yaml"
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        return root, manifest_path, manifest

    def run_guard(self, root: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--manifest", str(manifest)],
            text=True,
            capture_output=True,
            check=False,
        )

    def rewrite(self, path: Path, manifest: dict) -> None:
        path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    def test_accepts_project_derived_documented_change(self) -> None:
        root, path, _ = self.fixture()
        result = self.run_guard(root, path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("IMPLEMENTATION_PROVENANCE_PASS", result.stdout)

    def test_rejects_external_implementation_input(self) -> None:
        root, path, manifest = self.fixture()
        manifest["implementation_provenance"]["external_code_as_implementation"] = True
        self.rewrite(path, manifest)
        result = self.run_guard(root, path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("external_code_as_implementation must be false", result.stdout)

    def test_rejects_stale_design_hash(self) -> None:
        root, path, manifest = self.fixture()
        manifest["implementation_provenance"]["action_design_sha256"] = "0" * 64
        self.rewrite(path, manifest)
        result = self.run_guard(root, path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not match current action_design_path", result.stdout)

    def test_rejects_code_only_change(self) -> None:
        root, path, manifest = self.fixture()
        manifest["implementation_provenance"]["paired_changes"]["docs"] = []
        self.rewrite(path, manifest)
        result = self.run_guard(root, path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("paired_changes.docs must be a non-empty list", result.stdout)

    def test_rejects_symlink_escape(self) -> None:
        root, path, manifest = self.fixture()
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "copied.cpp"
            external.write_text("external coding\n", encoding="utf-8")
            link = root / "src/adapter/external.cpp"
            link.symlink_to(external)
            manifest["changed_files"] = ["src/adapter/external.cpp"]
            self.rewrite(path, manifest)
            result = self.run_guard(root, path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("resolved path escapes project", result.stdout)


if __name__ == "__main__":
    unittest.main()
