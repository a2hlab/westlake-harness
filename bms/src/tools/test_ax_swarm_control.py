#!/usr/bin/env python3

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("ax_swarm_control.py")
SPEC = importlib.util.spec_from_file_location("ax_swarm_control", MODULE_PATH)
assert SPEC and SPEC.loader
CONTROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)
TEST_BASE = "1" * 40


class FakeBroker:
    def __init__(self, *, confirms=True):
        self.confirms = confirms
        self.sent = []
        self.acquired = []
        self.counter = 0

    def acquire_worker(self, excluded, task_id):
        self.counter += 1
        worker = f"term_fake_{self.counter}"
        self.acquired.append((task_id, set(excluded)))
        return worker, self.counter, self.counter > 1

    def send(self, worker, prompt):
        self.sent.append((worker, prompt))

    def execution_started(
        self, worker, previous_output_at, result_path, baseline, *, wait
    ):
        return self.confirms


class AxSwarmControlTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.workflow = root / "workflow.json"
        self.state = root / "control" / "state.json"
        self.results = root / "results"
        self.results.mkdir()
        self.workflow.write_text(
            json.dumps(
                {
                    "workflow_id": "new-independent",
                    "canonical_base": TEST_BASE,
                    "tasks": [
                        {
                            "id": "A",
                            "deps": [],
                            "resources": ["device:integration"],
                            "state": "queued",
                        },
                        {
                            "id": "B",
                            "deps": [],
                            "resources": ["device:integration"],
                            "state": "queued",
                        },
                        {
                            "id": "C",
                            "deps": ["A"],
                            "resources": ["truth:candidate"],
                            "state": "queued",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.human_todo = root / ".HumanTodoList.md"
        self.human_todo.write_text(
            "# Human\n\n## 当前待办\n\n- [x] **UNRELATED** · `DONE`\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_tick_claim_resume_result_and_dag(self):
        before = self.workflow.read_bytes()
        first = CONTROL.tick(self.workflow, self.state, self.results)
        self.assertEqual(["A"], [item["task"] for item in first["ready"]])
        state = CONTROL.load_state(self.state, CONTROL.read_json(self.workflow))
        tasks = CONTROL.task_map(CONTROL.read_json(self.workflow))
        dispatched = CONTROL.claim(
            state, tasks, "A", "lane-1", f"/clean/main-{TEST_BASE}", self.results
        )
        resumed = CONTROL.claim(
            state, tasks, "A", "lane-2", f"/clean/main-{TEST_BASE}", self.results
        )
        self.assertEqual("dispatch", dispatched["action"])
        self.assertEqual("resume", resumed["action"])
        self.assertEqual("lane-2", resumed["lane"])
        CONTROL.write_json(self.state, state)
        (self.results / "A.result").write_text(
            "A|completed|built and tested\n", encoding="utf-8"
        )
        second = CONTROL.tick(self.workflow, self.state, self.results)
        self.assertEqual(["B", "C"], [item["task"] for item in second["ready"]])
        self.assertEqual(before, self.workflow.read_bytes())

    def test_continuation_keeps_task_worktree_and_result(self):
        CONTROL.tick(self.workflow, self.state, self.results)
        state = CONTROL.load_state(self.state, CONTROL.read_json(self.workflow))
        tasks = CONTROL.task_map(CONTROL.read_json(self.workflow))
        CONTROL.claim(state, tasks, "A", "lane-1", "/clean/main", self.results)
        resumed = CONTROL.claim(
            state, tasks, "A", "replacement-token", "/clean/main", self.results
        )
        self.assertEqual("resume", resumed["action"])
        self.assertEqual("replacement-token", resumed["lane"])
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.claim(state, tasks, "A", "lane-2", "/dirty/main", self.results)
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.claim(
                state, tasks, "A", "lane-2", "/clean/main", self.results / "other"
            )

    def test_three_routes_and_exact_canonical_promotion(self):
        workflow = CONTROL.read_json(self.workflow)
        state = CONTROL.new_state(workflow, TEST_BASE)
        for route in ("a", "b", "c"):
            CONTROL.record_route(state, "wall-7", route, "A")
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.record_route(state, "wall-7", "d", "A")
        CONTROL.promote(
            state,
            "wall-7",
            "gen-17",
            "C",
            "/clean/lane",
            TEST_BASE,
            True,
            TEST_BASE,
        )
        CONTROL.promote(
            state,
            "wall-7",
            "gen-17",
            "C",
            "/clean/lane",
            TEST_BASE,
            True,
            TEST_BASE,
        )
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.promote(
                state,
                "wall-7",
                "gen-18",
                "C",
                "/clean/lane",
                TEST_BASE,
                True,
                TEST_BASE,
            )
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.promote(
                CONTROL.new_state(workflow, TEST_BASE),
                "wall-8",
                "gen-18",
                "C",
                "/old/wip",
                "2" * 40,
                False,
                TEST_BASE,
            )
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.promote(
                CONTROL.new_state(workflow, TEST_BASE),
                "wall-8",
                "gen-18",
                "C",
                "/clean/lane",
                TEST_BASE + "0",
                True,
                TEST_BASE,
            )

    def test_rejects_multiline_result(self):
        (self.results / "A.result").write_text(
            "A|completed|ok\nextra\n", encoding="utf-8"
        )
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.tick(self.workflow, self.state, self.results)

    def test_maximum_ready_concurrency_only_serializes_path_and_device(self):
        tasks = CONTROL.task_map(
            {
                "tasks": [
                    {"id": "A", "deps": [], "resources": ["truth:x"]},
                    {"id": "B", "deps": [], "resources": ["truth:x"]},
                    {"id": "C", "deps": [], "resources": ["path:src/adapter"]},
                    {"id": "D", "deps": [], "resources": ["path:src/adapter/foo"]},
                    {"id": "E", "deps": [], "resources": ["device:d600-1"]},
                    {"id": "F", "deps": [], "resources": ["device:d600-1"]},
                    {"id": "G", "deps": [], "resources": ["device:d600-2"]},
                    {
                        "id": "H",
                        "deps": [],
                        "resources": ["file:src/adapter/foo/source.cc"],
                    },
                ]
            }
        )
        ready = CONTROL.ready_tasks(tasks, CONTROL.new_state({"workflow_id": "w"}))
        self.assertEqual(["A", "B", "C", "E", "G"], [item["task"] for item in ready])
        greedy_trap = CONTROL.task_map(
            {
                "tasks": [
                    {
                        "id": "DUAL",
                        "deps": [],
                        "resources": ["device:d600-1", "device:d600-2"],
                    },
                    {"id": "ONE", "deps": [], "resources": ["device:d600-1"]},
                    {"id": "TWO", "deps": [], "resources": ["device:d600-2"]},
                ]
            }
        )
        ready = CONTROL.ready_tasks(
            greedy_trap, CONTROL.new_state({"workflow_id": "w"})
        )
        self.assertEqual(["ONE", "TWO"], [item["task"] for item in ready])

    def test_workflow_or_explicit_base_binding_and_local_main(self):
        local_main = subprocess.run(
            [
                "git",
                "-C",
                str(MODULE_PATH.parents[1]),
                "rev-parse",
                "refs/heads/main^{commit}",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        workflow = {
            "workflow_id": "bound",
            "project_root": str(MODULE_PATH.parents[1]),
            "tasks": [
                {
                    "id": "A",
                    "deps": [],
                    "spec": f"clean main@{local_main}",
                }
            ],
        }
        self.assertEqual(local_main, CONTROL.resolve_canonical_base(workflow))
        self.assertEqual(
            local_main,
            CONTROL.resolve_canonical_base(workflow, local_main),
        )
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.resolve_canonical_base(workflow, "2" * 40)
        self.assertEqual(
            local_main, CONTROL.verify_local_main(workflow, local_main)
        )
        parent = subprocess.run(
            [
                "git",
                "-C",
                str(MODULE_PATH.parents[1]),
                "rev-parse",
                "refs/heads/main^",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        self.assertEqual(
            local_main, CONTROL.verify_local_main(workflow, parent)
        )
        with self.assertRaises(CONTROL.ControlError):
            CONTROL.verify_local_main(workflow, "2" * 40)

    def test_human_blocked_result_is_visible(self):
        (self.results / "A.result").write_text(
            "A|human-blocked|connect the named physical device\n", encoding="utf-8"
        )
        output = CONTROL.tick(self.workflow, self.state, self.results)
        self.assertEqual("A", output["human_blocked"][0]["task"])
        self.assertEqual(
            "connect the named physical device",
            output["human_blocked"][0]["summary"],
        )

    def write_autoloop_workflow(self, tasks):
        root = self.workflow.parent
        (root / "AGENTS.md").write_text("test\n", encoding="utf-8")
        self.workflow.write_text(
            json.dumps(
                {
                    "workflow_id": "new-independent",
                    "project_root": str(root),
                    "runtime": {
                        "paused": False,
                        "pause_reason": None,
                        "active_task": None,
                        "phase": "confirmed",
                    },
                    "source": {
                        "terminal": {
                            "identity": {
                                "terminal_handle": "term_controller"
                            }
                        }
                    },
                    "tasks": tasks,
                }
            ),
            encoding="utf-8",
        )

    @staticmethod
    def auto_task(task_id, deps=None, resources=None, state="queued"):
        return {
            "id": task_id,
            "title": task_id,
            "spec": f"execute {task_id}",
            "deps": deps or [],
            "resources": resources or [],
            "execution": "shared",
            "state": state,
            "attempts": 0,
            "orca": {"task_id": None, "dispatch_id": None, "worker": None},
            "result": None,
            "blocker": None,
        }

    def run_cycle(self, broker=None, dry_run=False):
        with mock.patch.object(
            CONTROL, "render_workflow", return_value={"ok": True}
        ) as renderer:
            output = CONTROL.autoloop_cycle(
                self.workflow,
                self.state,
                self.results,
                self.human_todo,
                broker=broker,
                dry_run=dry_run,
            )
        return output, renderer

    def test_autoloop_dispatches_maximum_and_records_only_confirmed_workers(self):
        self.write_autoloop_workflow(
            [
                self.auto_task("A", resources=["file:src/same.cc"]),
                self.auto_task("B", resources=["file:src/same.cc"]),
                self.auto_task("C", resources=["truth:independent"]),
            ]
        )
        broker = FakeBroker()
        output, renderer = self.run_cycle(broker)
        self.assertEqual(["A", "C"], [item["task"] for item in output["confirmed"]])
        workflow = CONTROL.read_json(self.workflow)
        by_id = {task["id"]: task for task in workflow["tasks"]}
        self.assertEqual("dispatched", by_id["A"]["state"])
        self.assertEqual("queued", by_id["B"]["state"])
        self.assertEqual("dispatched", by_id["C"]["state"])
        self.assertEqual("term_fake_1", by_id["A"]["orca"]["worker"])
        self.assertEqual(1, by_id["A"]["attempts"])
        self.assertTrue(renderer.called)
        self.assertIn("workflow=new-independent task=A attempt=1", broker.sent[0][1])
        self.assertIn(str(self.results / "A.result"), broker.sent[0][1])

    def test_pending_delivery_is_not_dispatched_twice(self):
        self.write_autoloop_workflow([self.auto_task("A")])
        broker = FakeBroker(confirms=False)
        first, _ = self.run_cycle(broker)
        self.assertEqual([], first["confirmed"])
        self.assertEqual(1, len(broker.sent))
        second, _ = self.run_cycle(broker)
        self.assertEqual([], second["confirmed"])
        self.assertEqual(1, len(broker.sent))
        self.assertEqual("A", second["pending"][0]["task"])
        self.assertEqual("queued", CONTROL.read_json(self.workflow)["tasks"][0]["state"])

    def test_attempt_baseline_rejects_old_result_but_accepts_rewrite(self):
        self.write_autoloop_workflow([self.auto_task("A")])
        result = self.results / "A.result"
        result.write_text("A|completed|same bytes\n", encoding="utf-8")
        broker = FakeBroker()
        self.run_cycle(broker)
        unchanged, _ = self.run_cycle()
        self.assertEqual([], unchanged["consumed"])
        old_mtime = result.stat().st_mtime_ns
        result.write_text("A|completed|same bytes\n", encoding="utf-8")
        os.utime(result, ns=(old_mtime + 10_000_000, old_mtime + 10_000_000))
        consumed, renderer = self.run_cycle()
        self.assertEqual(["A"], [item["task"] for item in consumed["consumed"]])
        self.assertEqual("completed", CONTROL.read_json(self.workflow)["tasks"][0]["state"])
        self.assertTrue(renderer.called)
        result.write_text("A|completed|overwritten\n", encoding="utf-8")
        with self.assertRaises(CONTROL.ControlError):
            self.run_cycle()

    def test_human_block_only_stops_its_dependency_frontier(self):
        self.write_autoloop_workflow(
            [
                self.auto_task("A"),
                self.auto_task("B", deps=["A"]),
                self.auto_task("C"),
            ]
        )
        self.run_cycle(FakeBroker())
        # A and C were dispatched; keep C active while A becomes human-blocked.
        (self.results / "A.result").write_text(
            "A|human-blocked|plug in the named cable\n", encoding="utf-8"
        )
        output, _ = self.run_cycle()
        workflow = CONTROL.read_json(self.workflow)
        by_id = {task["id"]: task for task in workflow["tasks"]}
        self.assertEqual("blocked", by_id["A"]["state"])
        self.assertEqual("queued", by_id["B"]["state"])
        self.assertEqual("dispatched", by_id["C"]["state"])
        self.assertFalse(workflow["runtime"]["paused"])
        self.assertIn("plug in the named cable", self.human_todo.read_text())
        self.assertEqual(1, len(output["human_todo"]))

    def test_dry_run_consumes_and_plans_without_writes_or_dispatch(self):
        task = self.auto_task("A", state="dispatched")
        task["attempts"] = 1
        task["orca"]["worker"] = "term_existing"
        self.write_autoloop_workflow([task, self.auto_task("B", deps=["A"])])
        (self.results / "A.result").write_text(
            "A|completed|ready\n", encoding="utf-8"
        )
        before_workflow = self.workflow.read_bytes()
        before_human = self.human_todo.read_bytes()
        output, renderer = self.run_cycle(FakeBroker(), dry_run=True)
        self.assertEqual(["A"], [item["task"] for item in output["consumed"]])
        self.assertEqual(["B"], output["planned"])
        self.assertEqual(before_workflow, self.workflow.read_bytes())
        self.assertEqual(before_human, self.human_todo.read_bytes())
        self.assertFalse(self.state.exists())
        self.assertFalse(renderer.called)

    def test_controller_file_lock_rejects_second_controller(self):
        lock = self.workflow.parent / "controller.lock"
        script = (
            "import fcntl,sys,time;"
            "f=open(sys.argv[1],'a+');"
            "fcntl.flock(f,fcntl.LOCK_EX);"
            "print('READY',flush=True);"
            "time.sleep(5)"
        )
        holder = subprocess.Popen(
            ["python3", "-c", script, str(lock)],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual("READY", holder.stdout.readline().strip())
            with self.assertRaises(CONTROL.ControlError):
                with CONTROL.controller_lock(lock):
                    pass
        finally:
            holder.terminate()
            holder.wait(timeout=5)
            holder.stdout.close()

    def test_existing_ax_task_render_refreshes_both_dashboards(self):
        tasks = [
            self.auto_task("A", state="dispatched"),
            self.auto_task("B", state="dispatched"),
        ]
        for task in tasks:
            task.update(
                conditions={"all": []},
                checkpoint=None,
            )
        self.write_autoloop_workflow(tasks)
        workflow = CONTROL.read_json(self.workflow)
        workflow.update(
            schema_version=1,
            title="render smoke",
            approval={"state": "draft", "plan_sha256": None},
        )
        workflow["source"]["terminal"]["fingerprint"] = "test"
        CONTROL.write_json(self.workflow, workflow)
        output = CONTROL.render_workflow(
            CONTROL.DEFAULT_AX_TASK,
            self.workflow,
            self.workflow.parent,
        )
        self.assertEqual("new-independent", output["workflow_id"])
        self.assertIn("MULTIPLE_ACTIVE_TASKS", output["validation_warnings"])
        self.assertTrue((self.workflow.parent / "TASKS.md").is_file())
        self.assertTrue((self.workflow.parent / "BACKLOG.md").is_file())

    def test_plan_hash_drift_is_detected_and_explicitly_authorizable(self):
        task = self.auto_task("A")
        task["conditions"] = {"all": []}
        self.write_autoloop_workflow([task])
        workflow = CONTROL.read_json(self.workflow)
        workflow.update(
            schema_version=1,
            title="plan drift",
            approval={"state": "confirmed", "plan_sha256": "0" * 64},
        )
        CONTROL.write_json(self.workflow, workflow)
        with self.assertRaises(CONTROL.ControlError):
            self.run_cycle(dry_run=True)
        with mock.patch.object(
            CONTROL, "render_workflow", return_value={"ok": True}
        ):
            output = CONTROL.autoloop_cycle(
                self.workflow,
                self.state,
                self.results,
                self.human_todo,
                dry_run=True,
                allow_plan_drift=True,
            )
        self.assertTrue(output["plan_hash"]["drift"])
        self.assertTrue(output["plan_hash"]["authorized"])


if __name__ == "__main__":
    unittest.main()
