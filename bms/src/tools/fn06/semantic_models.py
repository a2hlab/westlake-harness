#!/usr/bin/env python3
"""Route-agnostic Fn06 host semantic models.

These reducers make draft Action oracles executable without selecting a deployment
route.  They are developer tools, not target implementation and not device evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


class SemanticReject(ValueError):
    """Typed fail-closed rejection used by the host models."""


SUPPORTED_EXTRA_TYPES = (bool, int, float, str, bytes)


def explicit_launch(component: str | None, start_rc: int, callback: str | None) -> dict:
    if not component or "/" not in component:
        raise SemanticReject("FAIL_MISSING_OR_BAD_COMPONENT")
    if start_rc != 0:
        raise SemanticReject("FAIL_HOST_REJECTED")
    return {
        "component": component,
        "sync": "START_ACCEPTED",
        "async": "ON_CREATE_OBSERVED" if callback == component else "PENDING",
    }


def typed_extras_roundtrip(values: dict[str, Any]) -> dict[str, Any]:
    unsupported = sorted(
        key for key, value in values.items() if not isinstance(value, SUPPORTED_EXTRA_TYPES)
    )
    if unsupported:
        raise SemanticReject("FAIL_UNSUPPORTED_EXTRA:" + ",".join(unsupported))
    return {key: values[key] for key in sorted(values)}


def move_foreground(tasks: tuple[str, ...], target: str) -> tuple[str, ...]:
    if target not in tasks:
        raise SemanticReject("FAIL_UNKNOWN_TASK")
    return tuple(item for item in tasks if item != target) + (target,)


@dataclass(frozen=True)
class TaskDecision:
    operation: str
    task_id: str | None
    deliver_to: str | None = None


def evaluate_task_policy(
    flags: frozenset[str],
    launch_mode: str,
    affinity: str,
    caller_task: str,
    tasks: dict[str, tuple[str, ...]],
    component: str,
) -> TaskDecision:
    supported = {
        "NEW_TASK", "MULTIPLE_TASK", "SINGLE_TOP", "CLEAR_TOP",
        "CLEAR_TASK", "REORDER_TO_FRONT", "EXCLUDE_FROM_RECENTS",
    }
    unknown = flags - supported
    if unknown:
        raise SemanticReject("UNSUPPORTED_FLAG:" + ",".join(sorted(unknown)))
    if launch_mode not in {"standard", "singleTop"}:
        raise SemanticReject("UNSUPPORTED_LAUNCH_MODE")
    if not affinity:
        raise SemanticReject("FAIL_EMPTY_AFFINITY")
    task_id = affinity if "NEW_TASK" in flags else caller_task
    if "MULTIPLE_TASK" in flags:
        task_id = None
    members = tasks.get(task_id, ()) if task_id is not None else ()
    if "CLEAR_TASK" in flags and "NEW_TASK" not in flags:
        raise SemanticReject("FAIL_CLEAR_TASK_WITHOUT_NEW_TASK")
    if "CLEAR_TOP" in flags and component in members:
        return TaskDecision("CLEAR_ABOVE_AND_DELIVER", task_id, component)
    if ("SINGLE_TOP" in flags or launch_mode == "singleTop") and members[-1:] == (component,):
        return TaskDecision("DELIVER_TO_TOP", task_id, component)
    if "REORDER_TO_FRONT" in flags and component in members:
        return TaskDecision("MOVE_MEMBER_TO_TOP", task_id, component)
    return TaskDecision("CREATE_TASK" if task_id not in tasks else "PUSH", task_id)


@dataclass(frozen=True)
class TaskState:
    generation: int
    members: tuple[str, ...] = ()


def reduce_members(state: TaskState, event: dict[str, Any]) -> TaskState:
    if event.get("generation") != state.generation:
        raise SemanticReject("FAIL_STALE_GENERATION")
    kind, component = event.get("kind"), event.get("component")
    if kind == "PUSH":
        if not component:
            raise SemanticReject("FAIL_MISSING_COMPONENT")
        return replace(state, members=state.members + (component,))
    if kind == "POP":
        if not state.members or state.members[-1] != component:
            raise SemanticReject("FAIL_NOT_TOP")
        return replace(state, members=state.members[:-1])
    if kind == "CLEAR_ABOVE":
        if component not in state.members:
            raise SemanticReject("FAIL_UNKNOWN_MEMBER")
        index = state.members.index(component)
        return replace(state, members=state.members[: index + 1])
    if kind == "MOVE_TO_TOP":
        if component not in state.members:
            raise SemanticReject("FAIL_UNKNOWN_MEMBER")
        return replace(
            state,
            members=tuple(item for item in state.members if item != component) + (component,),
        )
    raise SemanticReject("FAIL_UNKNOWN_EVENT")


@dataclass
class LaunchRegistry:
    generation: int
    records: dict[str, tuple[str, str]]

    def bind(self, record_id: str, token: str, component: str, generation: int) -> None:
        if generation != self.generation:
            raise SemanticReject("FAIL_STALE_GENERATION")
        value = (token, component)
        if record_id in self.records and self.records[record_id] != value:
            raise SemanticReject("FAIL_RECORD_REPLAY_MISMATCH")
        if any(existing[0] == token and key != record_id for key, existing in self.records.items()):
            raise SemanticReject("FAIL_TOKEN_ALIAS")
        self.records[record_id] = value

    def resolve(self, record_id: str, token: str, generation: int) -> str:
        if generation != self.generation:
            raise SemanticReject("FAIL_STALE_GENERATION")
        if record_id not in self.records or self.records[record_id][0] != token:
            raise SemanticReject("FAIL_UNKNOWN_RECORD_TOKEN")
        return self.records[record_id][1]
