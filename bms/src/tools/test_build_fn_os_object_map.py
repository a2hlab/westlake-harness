#!/usr/bin/env python3
"""Regression tests for the Fn operating-system object map."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_fn_os_object_map as object_map  # noqa: E402


class FnOsObjectMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = object_map.build_object_map_data()
        cls.by_id = {
            concept["id"]: concept
            for concept in cls.data["concepts"]
        }

    def test_contains_exact_fn01_to_fn12(self) -> None:
        self.assertEqual(
            list(self.by_id),
            [f"Fn{index:02d}" for index in range(1, 13)],
        )

    def test_every_concept_has_three_non_empty_lanes(self) -> None:
        for concept_id, concept in self.by_id.items():
            with self.subTest(concept_id=concept_id):
                self.assertEqual(
                    set(concept["objects"]),
                    {"android", "bridge", "openharmony"},
                )
                for lane in object_map.LANES:
                    self.assertGreater(len(concept["objects"][lane]), 0)

    def test_every_object_has_existing_source_and_unique_id(self) -> None:
        object_ids: set[str] = set()
        for concept in self.data["concepts"]:
            for objects in concept["objects"].values():
                for item in objects:
                    self.assertNotIn(item["id"], object_ids)
                    object_ids.add(item["id"])
                    self.assertTrue((ROOT / item["source"]).exists())

    def test_directions_keep_frozen_meaning(self) -> None:
        fn03 = self.by_id["Fn03"]["neighbors"]
        self.assertTrue(any(edge["neighbor"] == "Fn01" for edge in fn03["up"]))
        self.assertTrue(any(edge["neighbor"] == "Fn06" for edge in fn03["left"]))
        self.assertTrue(any(edge["neighbor"] == "Fn04" for edge in fn03["right"]))
        self.assertTrue(
            any(
                edge["neighbor"] == "Fn04"
                and edge["relation"].startswith("inverse:")
                for edge in fn03["down"]
            )
        )

    def test_route_lens_does_not_promote_unaccepted_or_drifted_routes(self) -> None:
        self.assertEqual(self.by_id["Fn04"]["route"]["selected"], None)
        self.assertEqual(self.by_id["Fn11"]["route"]["binding"], "HASH_DRIFT")
        self.assertEqual(self.by_id["Fn11"]["route"]["selected"], None)
        self.assertEqual(
            self.by_id["Fn12"]["route"]["model"],
            "COMPOSITE_ROUTE_VECTOR",
        )

    def test_generator_and_projection_are_in_source_manifest(self) -> None:
        paths = {item["path"] for item in self.data["source_manifest"]}
        self.assertIn("src/tools/build_fn_os_object_map.py", paths)
        self.assertIn("src/tools/data/fn-os-object-projection.yaml", paths)
        self.assertIn("docs/spec/concept-graph.yaml", paths)

    def test_template_is_fully_rendered(self) -> None:
        rendered = object_map.render_html(self.data)
        self.assertNotIn("__OBJECT_MAP_DATA__", rendered)
        self.assertNotIn("__SOURCE_DIGEST__", rendered)
        self.assertIn("Concept 四向关系罗盘", rendered)
        self.assertIn("Evidence 是审计轨", rendered)
        self.assertIn("不是逐格一对一映射", rendered)
        self.assertIn('new URLSearchParams(location.search)', rendered)
        self.assertIn('next.searchParams.set("fn", activeId)', rendered)


if __name__ == "__main__":
    unittest.main()
