#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("ax_human_board.py")
SPEC = importlib.util.spec_from_file_location("ax_human_board", MODULE_PATH)
BOARD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BOARD)


def make_task(task_id: str, state: str = "queued", deps: list[str] | None = None, worker: str | None = None):
    return {
        "id": task_id,
        "title": f"title {task_id}",
        "spec": task_id,
        "deps": deps or [],
        "resources": [],
        "execution": "shared",
        "conditions": {"all": []},
        "state": state,
        "attempts": 1 if worker else 0,
        "orca": {"task_id": None, "dispatch_id": None, "worker": worker},
        "checkpoint": None,
        "blocker": None,
    }


def sample_workflow():
    ids = [
        task_id
        for _, milestone_ids in BOARD.AX.HUMAN_FLOW_MILESTONES
        for task_id in milestone_ids
    ] + ["T17"]
    tasks = []
    for task_id in ids:
        state = "completed" if task_id in {"H01", "C01", "C02", "C03"} else "queued"
        worker = None
        if task_id == "C09":
            state, worker = "dispatched", "term-c09"
        if task_id == "T02":
            state, worker = "dispatched", "term-t02"
        tasks.append(make_task(task_id, state=state, worker=worker))
    return {
        "workflow_id": "fast-flow",
        "title": "Fast flow",
        "project_root": "/opt/Bridge",
        "runtime": {"phase": "running", "paused": False},
        "tasks": tasks,
    }


class HumanBoardTest(unittest.TestCase):
    def test_goal_has_seven_milestones_and_excludes_post_target(self):
        flow = BOARD.AX.human_flow_projection(sample_workflow())
        self.assertEqual(7, len(flow["milestones"]))
        self.assertEqual(31, flow["total"])
        self.assertNotIn("T17", flow["goal_ids"])
        self.assertEqual(["T17"], flow["after_target"])

    def test_model_lists_every_active_task_with_exact_terminal(self):
        controller = {
            "active": {
                "C09": {"worker": "term-c09", "attempt": 2},
                "T02": {"worker": "term-t02", "attempt": 1},
            }
        }
        terminals = {
            "term-c09": {"connected": True, "title": "C09"},
            "term-t02": {"connected": True, "title": "T02"},
        }
        model = BOARD.build_model(sample_workflow(), controller, "", terminals, {})
        self.assertEqual(["C09", "T02"], [row["id"] for row in model["active"]])
        self.assertEqual(["term-c09", "term-t02"], [row["worker"] for row in model["active"]])

    def test_human_p0_is_distinct_from_waiting_packet(self):
        raw = (
            "- [ ] **LATER** · `WAITING_ON_AGENT_PACKET`\n"
            "- [ ] **NOW** · `READY_FOR_OWNER · P0`\n"
        )
        self.assertEqual(["NOW"], BOARD.ready_human_items(raw))

    def test_hdc_parser_and_html_explain_remaining_steps(self):
        hdc = "5ea1719200000000000000001123012c USB Connected localhost\n"
        targets = BOARD.parse_hdc(hdc)
        model = BOARD.build_model(sample_workflow(), {"active": {}}, "", {}, targets)
        page = BOARD.render_html(model)
        self.assertIn("后面还剩", page)
        self.assertIn("T16V", page)
        self.assertIn("T17", page)
        self.assertIn("人类无需动作", page)
        self.assertIn("5ea1719200000000000000001123012c", page)

    def test_result_files_are_observer_only_inputs(self):
        model = BOARD.build_model(
            sample_workflow(),
            {"active": {"C09": {"worker": "term-c09", "attempt": 2}}},
            "",
            {},
            {},
            {"C09": "/tmp/C09.result"},
        )
        active = {row["id"]: row for row in model["active"]}
        self.assertTrue(active["C09"]["result_received"])
        self.assertFalse(active["T02"]["result_received"])

    def test_bundle_snapshot_uses_same_projection(self):
        model = BOARD.build_model(
            sample_workflow(),
            {"active": {}},
            "",
            {},
            {},
            {},
        )
        page = BOARD.render_html(model)
        self.assertIn("renderer", page)
        self.assertIn(model["render_host"], page)


if __name__ == "__main__":
    unittest.main()
