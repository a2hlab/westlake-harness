#!/usr/bin/env python3
"""Regression tests for the live Pro board projection."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pro_board_render


class FloorViewTest(unittest.TestCase):
    def test_superseded_audit_cannot_overwrite_live_floor(self):
        live = {
            "lane": "fn01-04-pro",
            "status": "RUNNING",
            "floors": {
                "Fn03": {
                    "stage": "research",
                    "stage_status": "BLOCKED",
                    "note": "current Fn03 C2/C3 replay",
                }
            },
        }
        stale = {
            "lane": "global-fn-audit",
            "status": "DONE",
            "authoritative_global_audit": False,
            "phase": "COMPLETED_SNAPSHOT_SUPERSEDED_BY_ACTIVE_GROUP_FRAGMENTS",
            "floors": {
                "Fn03": {
                    "stage": "define",
                    "stage_status": "PASS",
                    "note": "completed historical snapshot",
                }
            },
        }

        view = pro_board_render.floor_view([live, stale])

        self.assertEqual("fn01-04-pro", view["Fn03"]["lane"])
        self.assertEqual("research", view["Fn03"]["stage"])
        self.assertEqual("current Fn03 C2/C3 replay", view["Fn03"]["note"])

    def test_orchestration_fragment_is_not_counted_as_agent_lane(self):
        fragments = [
            {"fragment_type": "orchestration", "status": "RUNNING", "levels": []},
            {"lane": "fn01-04-pro", "status": "RUNNING", "agent": {"cli": "codex"}},
        ]

        lanes = pro_board_render.lane_list(fragments)

        self.assertEqual(["fn01-04-pro"], [lane["id"] for lane in lanes])

    def test_html_renders_orca_task_dag(self):
        orchestration = {
            "levels": [],
            "machine_views": [],
            "validation_axis": {},
            "active_orca_tasks": [{
                "id": "task_design_1",
                "lane": "Fn02.A03 设计纠偏",
                "agent": "Codex",
                "status": "DISPATCHED",
                "boundary": "禁止产品源码与自签 PASS",
            }],
        }

        rendered = pro_board_render.render_html(
            "now", "headline", [], {}, [], [], "", orchestration)

        self.assertIn("Orca 任务 DAG", rendered)
        self.assertIn("task_design_1", rendered)
        self.assertIn("Fn02.A03 设计纠偏", rendered)
        self.assertIn("禁止产品源码与自签 PASS", rendered)

    def test_html_uses_low_frequency_refresh(self):
        rendered = pro_board_render.render_html(
            "now", "headline", [], {}, [], [], "", {})

        self.assertIn('<meta http-equiv="refresh" content="120">', rendered)
        self.assertIn("每 120s 自刷新", rendered)
        self.assertNotIn("每 30s 自刷新", rendered)

    def test_headline_separates_lanes_and_orca_tasks(self):
        lanes = [
            {"id": "horizontal", "status": "RUNNING"},
            {"id": "device", "status": "BLOCKED"},
            {"id": "history", "status": "DONE"},
        ]
        orchestration = {"active_orca_tasks": [
            {"status": "DISPATCHED"},
            {"status": "READY_QUEUED"},
            {"status": "COMPLETED"},
            {"status": "FAILED"},
        ]}

        headline = pro_board_render.build_headline(lanes, orchestration)

        self.assertEqual(
            "LANE 运行 1 / 完成 1；TASK 执行 1 / 排队 1 / 完成 1 / 失败替换 1；设备阻塞 device",
            headline,
        )

    def test_headline_counts_qualified_task_status_families(self):
        orchestration = {"active_orca_tasks": [
            {"status": "COMPLETED_FIRST_BAD"},
            {"status": "COMPLETED_AUTHOR_CORRECTION"},
            {"status": "FAILED_REPLACED"},
            {"status": "PENDING_CAPACITY"},
            {"status": "DISPATCHED_REVIEWING"},
        ]}

        headline = pro_board_render.build_headline([], orchestration)

        self.assertEqual(
            "LANE 运行 0 / 完成 0；TASK 执行 1 / 排队 1 / 完成 2 / 失败替换 1；设备阻塞 无",
            headline,
        )


if __name__ == "__main__":
    unittest.main()
