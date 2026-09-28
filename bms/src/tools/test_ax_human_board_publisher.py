#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("ax_human_board_publisher.py")
SPEC = importlib.util.spec_from_file_location("ax_human_board_publisher", MODULE_PATH)
PUBLISHER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PUBLISHER)


class PublisherTest(unittest.TestCase):
    def test_bundle_contains_only_small_observer_inputs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workflow = root / "workflow.json"
            controller = root / "controller-state.json"
            human = root / "HumanTodo.md"
            results = root / "results"
            results.mkdir()
            workflow.write_text('{"workflow_id":"w","tasks":[]}', encoding="utf-8")
            controller.write_text('{"active":{}}', encoding="utf-8")
            human.write_text("human", encoding="utf-8")
            (results / "T01.result").write_text("completed", encoding="utf-8")
            args = argparse.Namespace(
                workflow=str(workflow),
                controller_state=str(controller),
                human_todo=str(human),
                results=str(results),
                hdc="/fake/hdc",
            )
            with mock.patch.object(PUBLISHER, "command_output", side_effect=["orca", "hdc"]):
                bundle = PUBLISHER.build_bundle(args)
            self.assertEqual("w", bundle["workflow"]["workflow_id"])
            self.assertEqual({"T01": str((results / "T01.result").resolve())}, bundle["results"])
            self.assertEqual("orca", bundle["orca_raw"])
            self.assertEqual("hdc", bundle["hdc_raw"])
            encoded = json.dumps(bundle).encode()
            self.assertLess(len(encoded), 4096)


if __name__ == "__main__":
    unittest.main()
