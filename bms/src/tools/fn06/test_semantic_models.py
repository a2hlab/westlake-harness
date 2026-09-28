import unittest

from semantic_models import (
    LaunchRegistry, SemanticReject, TaskState, evaluate_task_policy,
    explicit_launch, move_foreground, reduce_members, typed_extras_roundtrip,
)


class SemanticModelsTest(unittest.TestCase):
    def test_a01_sync_async_are_distinct(self):
        self.assertEqual(explicit_launch("pkg/A", 0, None)["async"], "PENDING")
        self.assertEqual(explicit_launch("pkg/A", 0, "pkg/A")["async"], "ON_CREATE_OBSERVED")

    def test_a01_bad_component_rejected(self):
        with self.assertRaisesRegex(SemanticReject, "BAD_COMPONENT"):
            explicit_launch("implicit", 0, None)

    def test_a02_types_and_order_survive(self):
        source = {"z": b"x", "b": True, "i": 7, "s": "v", "f": 1.5}
        self.assertEqual(typed_extras_roundtrip(source), dict(sorted(source.items())))

    def test_a02_unsupported_type_rejected(self):
        with self.assertRaisesRegex(SemanticReject, "UNSUPPORTED_EXTRA"):
            typed_extras_roundtrip({"list": [1]})

    def test_a03_only_topology_changes(self):
        self.assertEqual(move_foreground(("t1", "t2"), "t1"), ("t2", "t1"))

    def test_a03_unknown_task_rejected(self):
        with self.assertRaisesRegex(SemanticReject, "UNKNOWN_TASK"):
            move_foreground(("t1",), "t2")

    def test_a05_single_top_delivers(self):
        decision = evaluate_task_policy(
            frozenset({"SINGLE_TOP"}), "standard", "pkg", "t1",
            {"t1": ("pkg/A",)}, "pkg/A",
        )
        self.assertEqual((decision.operation, decision.deliver_to), ("DELIVER_TO_TOP", "pkg/A"))

    def test_a05_unknown_flag_fails_closed(self):
        with self.assertRaisesRegex(SemanticReject, "UNSUPPORTED_FLAG"):
            evaluate_task_policy(
                frozenset({"MAGIC"}), "standard", "pkg", "t1", {}, "pkg/A"
            )

    def test_a05_clear_top(self):
        decision = evaluate_task_policy(
            frozenset({"CLEAR_TOP"}), "standard", "pkg", "t1",
            {"t1": ("pkg/A", "pkg/B")}, "pkg/A",
        )
        self.assertEqual(decision.operation, "CLEAR_ABOVE_AND_DELIVER")

    def test_a06_reducer_sequence(self):
        state = TaskState(3)
        state = reduce_members(state, {"generation": 3, "kind": "PUSH", "component": "A"})
        state = reduce_members(state, {"generation": 3, "kind": "PUSH", "component": "B"})
        state = reduce_members(state, {"generation": 3, "kind": "POP", "component": "B"})
        self.assertEqual(state.members, ("A",))

    def test_a06_stale_event_rejected_without_mutation(self):
        state = TaskState(3, ("A",))
        with self.assertRaisesRegex(SemanticReject, "STALE_GENERATION"):
            reduce_members(state, {"generation": 2, "kind": "PUSH", "component": "B"})
        self.assertEqual(state.members, ("A",))

    def test_a06_clear_above_and_move(self):
        state = TaskState(1, ("A", "B", "C"))
        state = reduce_members(state, {"generation": 1, "kind": "CLEAR_ABOVE", "component": "B"})
        state = reduce_members(state, {"generation": 1, "kind": "MOVE_TO_TOP", "component": "A"})
        self.assertEqual(state.members, ("B", "A"))

    def test_a07_registry_exact_replay(self):
        registry = LaunchRegistry(4, {})
        registry.bind("r1", "t1", "pkg/A", 4)
        registry.bind("r1", "t1", "pkg/A", 4)
        self.assertEqual(registry.resolve("r1", "t1", 4), "pkg/A")

    def test_a07_registry_mismatch_rejected(self):
        registry = LaunchRegistry(4, {})
        registry.bind("r1", "t1", "pkg/A", 4)
        with self.assertRaisesRegex(SemanticReject, "REPLAY_MISMATCH"):
            registry.bind("r1", "t2", "pkg/A", 4)

    def test_a07_token_alias_rejected(self):
        registry = LaunchRegistry(4, {})
        registry.bind("r1", "t1", "pkg/A", 4)
        with self.assertRaisesRegex(SemanticReject, "TOKEN_ALIAS"):
            registry.bind("r2", "t1", "pkg/B", 4)


if __name__ == "__main__":
    unittest.main()
