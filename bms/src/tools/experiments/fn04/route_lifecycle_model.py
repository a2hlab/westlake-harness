#!/usr/bin/env python3
"""Host-only R1b lifecycle model for early Fn04 falsification.

This is an experimental seam, not product code and not device evidence.  It
models the minimum cross-Action invariants shared by A03/A04/A08/A10/A14:
generation-bound identity, ordered lifecycle, buffer/fence ownership, commit,
and teardown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class RouteError(RuntimeError):
    """A typed lifecycle or ownership invariant was rejected."""


class State(Enum):
    NEW = auto()
    ADDED = auto()
    RELAYOUT_READY = auto()
    SURFACE_READY = auto()
    REMOVING = auto()
    DESTROYED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class WindowIdentity:
    generation: str
    android_token: str
    parent_id: int
    child_id: int

    def validate(self) -> None:
        if not self.generation or not self.android_token:
            raise RouteError("INVALID_IDENTITY")
        if self.parent_id <= 0 or self.child_id <= 0:
            raise RouteError("INVALID_SESSION_ID")
        if self.parent_id == self.child_id:
            raise RouteError("PARENT_CHILD_COLLAPSE")


@dataclass
class Frame:
    frame_id: int
    generation: str
    acquire_fence_owned: bool = True
    queued: bool = False
    committed: bool = False
    released: bool = False


@dataclass
class RouteLifecycle:
    identity: WindowIdentity
    state: State = State.NEW
    width: int = 0
    height: int = 0
    surface_id: int | None = None
    frames: dict[int, Frame] = field(default_factory=dict)
    teardown_count: int = 0

    def _same_generation(self, generation: str) -> None:
        if generation != self.identity.generation:
            raise RouteError("STALE_GENERATION")

    def _require(self, *states: State) -> None:
        if self.state not in states:
            raise RouteError(f"INVALID_STATE:{self.state.name}")

    def add(self, generation: str, token: str, *, oh_create_ok: bool = True) -> None:
        self._require(State.NEW)
        self.identity.validate()
        self._same_generation(generation)
        if token != self.identity.android_token:
            raise RouteError("WRONG_TOKEN")
        if not oh_create_ok:
            self.state = State.FAILED
            raise RouteError("OH_CHILD_CREATE_FAILED")
        self.state = State.ADDED

    def relayout(
        self,
        generation: str,
        width: int,
        height: int,
        *,
        oh_apply_ok: bool = True,
    ) -> None:
        self._require(State.ADDED, State.RELAYOUT_READY)
        self._same_generation(generation)
        if width <= 0 or height <= 0:
            raise RouteError("INVALID_LAYOUT")
        if not oh_apply_ok:
            raise RouteError("OH_RELAYOUT_FAILED")
        self.width, self.height = width, height
        self.state = State.RELAYOUT_READY

    def attach_surface(self, generation: str, surface_id: int) -> None:
        self._require(State.RELAYOUT_READY)
        self._same_generation(generation)
        if surface_id <= 0:
            raise RouteError("INVALID_SURFACE")
        self.surface_id = surface_id
        self.state = State.SURFACE_READY

    def dequeue(self, generation: str, frame_id: int) -> Frame:
        self._require(State.SURFACE_READY)
        self._same_generation(generation)
        if frame_id <= 0 or frame_id in self.frames:
            raise RouteError("FRAME_ID_REPLAY")
        frame = Frame(frame_id=frame_id, generation=generation)
        self.frames[frame_id] = frame
        return frame

    def queue(self, generation: str, frame_id: int, *, fence_ok: bool = True) -> None:
        self._require(State.SURFACE_READY)
        self._same_generation(generation)
        frame = self.frames.get(frame_id)
        if frame is None:
            raise RouteError("UNKNOWN_FRAME")
        if frame.generation != generation:
            raise RouteError("STALE_FRAME")
        if frame.queued:
            raise RouteError("DOUBLE_QUEUE")
        if not frame.acquire_fence_owned or not fence_ok:
            raise RouteError("ACQUIRE_FENCE_FAILED")
        frame.acquire_fence_owned = False
        frame.queued = True

    def commit(self, generation: str, frame_id: int, *, rs_ok: bool = True) -> None:
        self._require(State.SURFACE_READY)
        self._same_generation(generation)
        frame = self.frames.get(frame_id)
        if frame is None or not frame.queued:
            raise RouteError("COMMIT_BEFORE_QUEUE")
        if frame.committed:
            raise RouteError("DOUBLE_COMMIT")
        if not rs_ok:
            raise RouteError("RS_COMMIT_FAILED")
        frame.committed = True

    def remove(self, generation: str, *, oh_remove_ok: bool = True) -> None:
        self._require(State.ADDED, State.RELAYOUT_READY, State.SURFACE_READY)
        self._same_generation(generation)
        if not oh_remove_ok:
            raise RouteError("OH_REMOVE_FAILED")
        self.state = State.REMOVING
        for frame in self.frames.values():
            frame.released = True

    def destroy(self, generation: str) -> None:
        self._require(State.REMOVING)
        self._same_generation(generation)
        if self.teardown_count:
            raise RouteError("DOUBLE_TEARDOWN")
        self.teardown_count += 1
        self.surface_id = None
        self.state = State.DESTROYED
