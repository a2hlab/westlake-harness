#!/usr/bin/env python3
"""Regression tests for the Fn technology route atlas projection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_fn_route_atlas as atlas  # noqa: E402


class FnRouteAtlasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = atlas.build_atlas_data()
        cls.by_id = {
            concept["id"]: concept
            for concept in cls.data["concepts"]
        }

    def test_contains_exact_fn01_to_fn12(self) -> None:
        self.assertEqual(
            list(self.by_id),
            [f"Fn{index:02d}" for index in range(1, 13)],
        )

    def test_only_hash_bound_accepted_routes_are_effective(self) -> None:
        self.assertEqual(
            self.by_id["Fn01"]["decision"]["effective_selected_route"],
            "R2",
        )
        self.assertEqual(
            self.by_id["Fn01"]["decision"]["effective_backup_route"],
            "R3",
        )
        self.assertEqual(
            self.by_id["Fn04"]["decision"]["effective_selected_route"],
            None,
        )

    def test_route_tables_are_not_empty(self) -> None:
        for concept_id, concept in self.by_id.items():
            with self.subTest(concept_id=concept_id):
                self.assertGreater(len(concept["routes"]), 0)

    def test_component_domains_are_not_forced_into_one_route(self) -> None:
        for concept_id in ("Fn08", "Fn09", "Fn10", "Fn11", "Fn12"):
            with self.subTest(concept_id=concept_id):
                self.assertEqual(
                    self.by_id[concept_id]["route_model"],
                    "COMPOSITE_ROUTE_VECTOR",
                )

    def test_generator_is_part_of_source_provenance(self) -> None:
        manifest_paths = {
            item["path"]
            for item in self.data["source_manifest"]
        }
        self.assertIn("src/tools/build_fn_route_atlas.py", manifest_paths)

    def test_advisory_routes_are_visible_but_not_promoted(self) -> None:
        fn03 = self.by_id["Fn03"]["decision"]
        self.assertEqual(fn03["future_upgrade_route"], "R2")
        self.assertIsNone(fn03["effective_backup_route"])

        fn12 = self.by_id["Fn12"]["decision"]
        self.assertIn("Fn12.A10", fn12["proposed_route"])
        self.assertIsNone(fn12["effective_selected_route"])

    def test_template_is_fully_rendered(self) -> None:
        rendered = atlas.render_html(self.data)
        self.assertNotIn("__ATLAS_DATA__", rendered)
        self.assertNotIn("__SOURCE_DIGEST__", rendered)
        self.assertIn("Bridge 多路径技术方案图谱", rendered)
        self.assertIn("未来升级：非备份、非自动切换", rendered)
        self.assertIn("打开 OS 对象地图", rendered)


if __name__ == "__main__":
    unittest.main()
