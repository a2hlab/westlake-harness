#!/usr/bin/env python3
"""Small non-blocking controller for an independent AX demo swarm.

The legacy ``tick``/``claim`` commands remain available as read-mostly
building blocks.  ``autoloop`` is the lightweight persistent controller: it
holds one file lock, consumes attempt-bound one-line results, atomically updates
the parent workflow, asks the existing ``ax_task.py render`` command to refresh
the dashboards, and refills dependency-ready non-conflicting Orca terminals.
It deliberately does not create Orca orchestration lifecycle objects.

Workers only write ``<task>.result`` as one UTF-8 line:

    TASK|completed|summary
    TASK|human-blocked|minimal human action
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

MAX_REFILL_SECONDS = 30
RESULT_STATES = {"completed", "human-blocked"}
FULL_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
MAIN_BINDING_RE = re.compile(r"\bmain@([0-9a-f]{40})\b")
SERIAL_RESOURCE_PREFIXES = ("device:", "file:", "path:")
ACTIVE_TASK_STATES = {"created", "dispatched", "running"}
TERMINAL_TASK_STATES = {"completed", "blocked"}
DEFAULT_AX_TASK = (
    Path(__file__).parents[1]
    / ".agents"
    / "skills"
    / "ax-task"
    / "scripts"
    / "ax_task.py"
)


class ControlError(RuntimeError):
    pass


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ControlError(f"cannot read {path}: {exc}") from exc


def write_json(path: Path, value: dict, *, sort_keys: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=sort_keys)
        + "\n"
    )
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(value)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


@contextmanager
def controller_lock(path: Path) -> Iterator[None]:
    """Hold the sole controller lock until the loop exits."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ControlError(f"another controller holds {path}") from exc
        stream.seek(0)
        stream.truncate()
        stream.write(f"{os.getpid()}\n")
        stream.flush()
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def task_map(workflow: dict) -> dict[str, dict]:
    tasks = workflow.get("tasks")
    if not isinstance(tasks, list):
        raise ControlError("workflow.tasks must be a list")
    mapped = {}
    for task in tasks:
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id or task_id in mapped:
            raise ControlError(f"invalid or duplicate task id: {task_id!r}")
        mapped[task_id] = task
    for task_id, task in mapped.items():
        for dep in task.get("deps", []):
            if dep not in mapped:
                raise ControlError(f"{task_id} has unknown dependency {dep}")
    return mapped


def resolve_canonical_base(
    workflow: dict, explicit_base: str | None = None
) -> str | None:
    """Resolve one exact promotion base without inheriting an old constant."""

    candidates: set[str] = set()
    declared = workflow.get("canonical_base")
    if declared is not None:
        if not isinstance(declared, str) or not FULL_COMMIT_RE.fullmatch(declared):
            raise ControlError("workflow.canonical_base must be an exact 40-hex commit")
        candidates.add(declared)
    runtime = workflow.get("runtime")
    if isinstance(runtime, dict) and runtime.get("canonical_base") is not None:
        runtime_base = runtime["canonical_base"]
        if (
            not isinstance(runtime_base, str)
            or not FULL_COMMIT_RE.fullmatch(runtime_base)
        ):
            raise ControlError(
                "workflow.runtime.canonical_base must be an exact 40-hex commit"
            )
        candidates.add(runtime_base)
    candidates.update(
        MAIN_BINDING_RE.findall(
            json.dumps(workflow, ensure_ascii=False, sort_keys=True)
        )
    )
    if len(candidates) > 1:
        raise ControlError(
            "workflow contains conflicting canonical main bindings: "
            + ", ".join(sorted(candidates))
        )
    workflow_base = next(iter(candidates), None)
    if explicit_base is not None:
        if not FULL_COMMIT_RE.fullmatch(explicit_base):
            raise ControlError("--canonical-base must be an exact 40-hex commit")
        if workflow_base is not None and workflow_base != explicit_base:
            raise ControlError(
                "explicit canonical base disagrees with the workflow binding"
            )
        return explicit_base
    return workflow_base


def current_plan_sha256(workflow: dict) -> str | None:
    """Match ax_task.py's frozen-plan projection without importing it."""

    required = ("schema_version", "workflow_id", "title", "project_root")
    if not all(key in workflow for key in required):
        return None
    projected_tasks = []
    for task in workflow.get("tasks", []):
        if not all(
            key in task
            for key in (
                "id",
                "title",
                "spec",
                "deps",
                "resources",
                "execution",
                "conditions",
            )
        ):
            return None
        projected_tasks.append(
            {
                "id": task["id"],
                "title": task["title"],
                "spec": task["spec"],
                "deps": task["deps"],
                "resources": task["resources"],
                "execution": task["execution"],
                "conditions": task["conditions"],
            }
        )
    payload = {
        "schema_version": workflow["schema_version"],
        "workflow_id": workflow["workflow_id"],
        "title": workflow["title"],
        "project_root": workflow["project_root"],
        "tasks": projected_tasks,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def inspect_plan_hash(
    workflow: dict, *, allow_drift: bool = False
) -> dict[str, Any]:
    current = current_plan_sha256(workflow)
    approval = workflow.get("approval")
    declared = (
        approval.get("plan_sha256") if isinstance(approval, dict) else None
    )
    if current is None or not isinstance(declared, str):
        return {
            "declared": declared,
            "current": current,
            "drift": None,
            "authorized": False,
        }
    drift = current != declared
    if drift and not allow_drift:
        raise ControlError(
            f"confirmed plan hash drift: declared {declared}, current {current}"
        )
    return {
        "declared": declared,
        "current": current,
        "drift": drift,
        "authorized": bool(drift and allow_drift),
    }


def verify_local_main(
    workflow: dict, canonical_base: str | None, repo: Path | None = None
) -> str | None:
    if canonical_base is None:
        return None
    project_root = repo or workflow.get("project_root")
    if project_root is None:
        return None
    project_root = Path(project_root)
    try:
        resolved_base = subprocess.run(
            [
                "git",
                "-C",
                str(project_root),
                "rev-parse",
                "--verify",
                f"{canonical_base}^{{commit}}",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
        local_main = subprocess.run(
            [
                "git",
                "-C",
                str(project_root),
                "rev-parse",
                "--verify",
                "refs/heads/main^{commit}",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ControlError(
            f"cannot resolve canonical base/local main in {project_root}: {exc}"
        ) from exc
    if resolved_base != canonical_base:
        raise ControlError("canonical base did not resolve to its exact commit")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(project_root),
            "merge-base",
            "--is-ancestor",
            canonical_base,
            local_main,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if ancestry.returncode != 0:
        raise ControlError(
            f"workflow canonical base {canonical_base} is not in local main "
            f"{local_main} history"
        )
    return local_main


def new_state(workflow: dict, canonical_base: str | None = None) -> dict:
    return {
        "workflow_id": workflow.get("workflow_id"),
        "canonical_base": canonical_base,
        "active": {},
        "pending": {},
        "results": {},
        "consumed_attempts": {},
        "routes": {},
        "promotions": {},
    }


def load_state(
    path: Path, workflow: dict, canonical_base: str | None = None
) -> dict:
    if canonical_base is None:
        canonical_base = resolve_canonical_base(workflow)
    state = (
        read_json(path)
        if path.exists()
        else new_state(workflow, canonical_base=canonical_base)
    )
    if state.get("workflow_id") != workflow.get("workflow_id"):
        raise ControlError("state belongs to a different workflow")
    bound_base = state.get("canonical_base")
    if bound_base is not None and canonical_base is not None:
        if bound_base != canonical_base:
            raise ControlError("state canonical base differs from current workflow")
    elif bound_base is not None:
        raise ControlError("workflow no longer supplies the state canonical base")
    elif bound_base is None:
        state["canonical_base"] = canonical_base
    for key in (
        "active",
        "pending",
        "results",
        "consumed_attempts",
        "routes",
        "promotions",
    ):
        state.setdefault(key, {})
    return state


def parse_result(path: Path, tasks: dict[str, dict]) -> tuple[str, str, str, str]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ControlError(f"invalid UTF-8 result {path}: {exc}") from exc
    if "\r" in text or text.count("\n") > 1:
        raise ControlError(f"{path} must contain exactly one logical line")
    line = text.removesuffix("\n")
    fields = line.split("|", 2)
    if len(fields) != 3 or not all(fields):
        raise ControlError(f"{path} must be TASK|STATUS|SUMMARY")
    task_id, status, summary = fields
    if task_id not in tasks or path.name != f"{task_id}.result":
        raise ControlError(f"{path} task identity mismatch")
    if status not in RESULT_STATES:
        raise ControlError(f"{path} has unsupported status {status!r}")
    digest = hashlib.sha256(raw).hexdigest()
    return task_id, status, summary, digest


def result_fingerprint(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = path.read_bytes()
        stat = path.stat()
    except OSError as exc:
        raise ControlError(f"cannot fingerprint {path}: {exc}") from exc
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }


def fingerprint_equal(
    left: dict[str, Any] | None, right: dict[str, Any] | None
) -> bool:
    return left == right


def consume_results(
    state: dict, results_dir: Path, tasks: dict[str, dict]
) -> list[dict]:
    consumed = []
    if not results_dir.exists():
        return consumed
    for path in sorted(results_dir.glob("*.result")):
        task_id, status, summary, digest = parse_result(path, tasks)
        previous = state["results"].get(task_id)
        if previous:
            if previous["sha256"] != digest:
                raise ControlError(f"consumed result changed: {path}")
            continue
        state["results"][task_id] = {
            "status": status,
            "summary": summary,
            "sha256": digest,
            "path": str(path),
        }
        state["active"].pop(task_id, None)
        consumed.append({"task": task_id, "status": status, "summary": summary})
    return consumed


def adopt_parent_active_tasks(
    workflow: dict,
    state: dict,
    tasks: dict[str, dict],
    results_dir: Path,
) -> bool:
    """Recover parent-dispatched work after a controller restart.

    A result already present for an externally dispatched task is intentionally
    not made the baseline: retry setup must archive the older attempt before
    setting the parent back to ``dispatched``.  Results created by this helper
    are protected by their persisted per-attempt baseline below.
    """

    changed = False
    for task_id, task in tasks.items():
        if task.get("state") not in ACTIVE_TASK_STATES:
            continue
        if task_id in state["active"] or task_id in state["pending"]:
            continue
        worker = task.get("orca", {}).get("worker")
        record = {
            "task": task_id,
            "attempt": int(task.get("attempts", 0)),
            "worker": worker,
            "worktree": workflow.get("project_root"),
            "result_path": str(results_dir / f"{task_id}.result"),
            "resources": task.get("resources", []),
            "baseline": None,
            "adopted": True,
        }
        state["active"][task_id] = record
        changed = True
    return changed


def consume_parent_results(
    workflow: dict,
    state: dict,
    tasks: dict[str, dict],
    results_dir: Path,
) -> tuple[list[dict], bool]:
    """Consume only the active attempt and update parent task truth."""

    consumed: list[dict] = []
    changed = False
    active_ids = sorted(set(state["active"]) | set(state["pending"]))
    for task_id in active_ids:
        is_pending = task_id in state["pending"]
        record = state["pending"].get(task_id) or state["active"].get(task_id)
        task = tasks[task_id]
        attempt = int(record["attempt"])
        parent_attempt = int(task.get("attempts", 0))
        expected_attempts = (
            {parent_attempt, parent_attempt + 1}
            if is_pending
            else {parent_attempt}
        )
        if attempt not in expected_attempts:
            raise ControlError(
                f"{task_id} controller attempt {attempt} disagrees with "
                f"parent attempt {parent_attempt}"
            )
        path = Path(record["result_path"])
        current = result_fingerprint(path)
        if current is None or fingerprint_equal(current, record.get("baseline")):
            continue
        identity = f"{task_id}:{attempt}"
        prior = state["consumed_attempts"].get(identity)
        if prior is not None:
            if not fingerprint_equal(prior, current):
                raise ControlError(
                    f"result for consumed attempt {identity} changed: {path}"
                )
            continue
        parsed_task, status, summary, digest = parse_result(path, tasks)
        if parsed_task != task_id:
            raise ControlError(f"{path} does not belong to active task {task_id}")
        if task.get("state") in TERMINAL_TASK_STATES:
            expected_state = (
                "completed" if status == "completed" else "blocked"
            )
            parent_summary = (task.get("result") or {}).get("summary")
            if (
                task.get("state") != expected_state
                or parent_summary != summary
            ):
                raise ControlError(
                    f"terminal task {task_id} cannot be overwritten by {path}"
                )
        target_state = "completed" if status == "completed" else "blocked"
        task["state"] = target_state
        task["attempts"] = max(int(task.get("attempts", 0)), attempt)
        task.setdefault("orca", {}).update(
            task_id=None,
            dispatch_id=None,
            worker=record.get("worker"),
        )
        task["result"] = {"summary": summary}
        task["blocker"] = (
            None if status == "completed" else f"HUMAN_BLOCKED:{summary}"
        )
        result_record = {
            "attempt": attempt,
            "status": status,
            "summary": summary,
            "sha256": digest,
            "fingerprint": current,
            "path": str(path),
        }
        state["results"][task_id] = result_record
        state["consumed_attempts"][identity] = current
        state["active"].pop(task_id, None)
        state["pending"].pop(task_id, None)
        consumed.append({"task": task_id, "status": status, "summary": summary})
        changed = True
    return consumed, changed


def is_completed(task_id: str, task: dict, state: dict) -> bool:
    local = state["results"].get(task_id, {}).get("status")
    return local == "completed" or task.get("state") == "completed"


def resource_conflicts(left: str, right: str) -> bool:
    if not (
        left.startswith(SERIAL_RESOURCE_PREFIXES)
        and right.startswith(SERIAL_RESOURCE_PREFIXES)
    ):
        return False
    left_kind, left_value = left.split(":", 1)
    right_kind, right_value = right.split(":", 1)
    if left_kind == "device" or right_kind == "device":
        return left_kind == right_kind and left_value == right_value
    if left_kind == right_kind == "file":
        return left_value == right_value
    left_parts = Path(left_value).parts
    right_parts = Path(right_value).parts
    if left_kind == "file":
        return left_parts[: len(right_parts)] == right_parts
    if right_kind == "file":
        return right_parts[: len(left_parts)] == left_parts
    shorter = min(len(left_parts), len(right_parts))
    return left_parts[:shorter] == right_parts[:shorter]


def occupied_resources(
    tasks: dict[str, dict], state: dict
) -> list[tuple[str, str]]:
    occupied: list[tuple[str, str]] = []
    for task_id, task in tasks.items():
        locally_active = task_id in state["active"] or task_id in state["pending"]
        externally_active = task.get("state") in {"dispatched", "running"}
        if not locally_active and not externally_active:
            continue
        if task_id in state["results"]:
            continue
        for resource in task.get("resources", []):
            if not resource.startswith(SERIAL_RESOURCE_PREFIXES):
                continue
            owner = next(
                (
                    other_owner
                    for other_resource, other_owner in occupied
                    if resource_conflicts(resource, other_resource)
                ),
                None,
            )
            if owner is not None and owner != task_id:
                raise ControlError(
                    f"resource {resource} has two active owners: {owner}, {task_id}"
                )
            occupied.append((resource, task_id))
    return occupied


def select_max_concurrent(candidates: list[dict]) -> list[dict]:
    best: list[dict] = []

    def search(index: int, selected: list[dict]) -> None:
        nonlocal best
        if len(selected) + len(candidates) - index <= len(best):
            return
        if index == len(candidates):
            best = list(selected)
            return
        candidate = candidates[index]
        if not any(
            resource_conflicts(left, right)
            for chosen in selected
            for left in candidate["resources"]
            for right in chosen["resources"]
        ):
            selected.append(candidate)
            search(index + 1, selected)
            selected.pop()
        search(index + 1, selected)

    search(0, [])
    return best


def ready_tasks(tasks: dict[str, dict], state: dict) -> list[dict]:
    occupied = occupied_resources(tasks, state)
    candidates = []
    for task_id, task in tasks.items():
        if is_completed(task_id, task, state) or task_id in state["results"]:
            continue
        if (
            task_id in state["active"]
            or task_id in state["pending"]
            or task.get("state") in {"dispatched", "running"}
        ):
            continue
        if task.get("state", "queued") not in {"queued", "pending", "ready"}:
            continue
        if not all(is_completed(dep, tasks[dep], state) for dep in task.get("deps", [])):
            continue
        resources = task.get("resources", [])
        if any(
            resource_conflicts(resource, occupied_resource)
            for resource in resources
            for occupied_resource, _ in occupied
        ):
            continue
        candidates.append(
            {
                "task": task_id,
                "title": task.get("title", ""),
                "execution": task.get("execution", "shared"),
                "resources": resources,
            }
        )
    return select_max_concurrent(candidates)


def human_item_id(workflow_id: str, task_id: str) -> str:
    safe_workflow = re.sub(r"[^A-Za-z0-9-]+", "-", workflow_id).strip("-")
    safe_task = re.sub(r"[^A-Za-z0-9-]+", "-", task_id).strip("-")
    return f"AX-SWARM-{safe_workflow}-{safe_task}".upper()


def refresh_human_todo(
    workflow: dict,
    tasks: dict[str, dict],
    path: Path,
    *,
    results_dir: Path | None = None,
    dry_run: bool = False,
) -> list[str]:
    blocked = [
        task
        for task in tasks.values()
        if task.get("state") == "blocked"
        and str(task.get("blocker", "")).startswith("HUMAN_BLOCKED:")
    ]
    if not blocked:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ControlError(f"cannot refresh human queue {path}: {exc}") from exc
    marker = "## 当前待办\n"
    if marker not in text:
        raise ControlError(f"{path} is missing the current-todo section")
    original_text = text
    updated_ids: list[str] = []
    for task in blocked:
        item_id = human_item_id(workflow["workflow_id"], task["id"])
        summary = task["result"]["summary"]
        descendants = sorted(
            candidate["id"]
            for candidate in tasks.values()
            if task["id"] in candidate.get("deps", [])
            and candidate.get("state") != "completed"
        )
        frontier = ", ".join(descendants) or "none"
        result_path = (results_dir or path.parent) / f"{task['id']}.result"
        entry = f"""- [ ] **{item_id}** · `READY_FOR_OWNER · P0`
  - 需要人类的原因：{summary}
  - Agent 已完成：task `{task['id']}` 已耗尽授权内可执行路径并写回 human-blocked；其他无依赖 lane 继续。
  - result：`{result_path}`。
  - Agent 推荐：执行最小动作：{summary}
  - 备选：若暂时不能执行，保持 `{task['id']}` 及直接依赖前沿 `{frontier}` 阻塞，其他 lane 不暂停。
  - 不处理的影响：仅 `{task['id']}` 的依赖前沿不能继续。
  - 最小回复：`{summary}`
  - 写回：workflow `{workflow['workflow_id']}` task `{task['id']}`。
"""
        pattern = re.compile(
            rf"(?ms)^- \[[ x]\] \*\*{re.escape(item_id)}\*\*.*?"
            rf"(?=^- \[[ x]\] \*\*|\Z)"
        )
        if pattern.search(text):
            text = pattern.sub(entry.rstrip() + "\n\n", text, count=1)
        else:
            text = text.replace(marker, marker + "\n" + entry.rstrip() + "\n\n", 1)
        updated_ids.append(item_id)
    if not dry_run and text != original_text:
        if path.read_text(encoding="utf-8") != original_text:
            raise ControlError(f"{path} changed while the controller refreshed it")
        write_text(path, text)
    return updated_ids


def render_workflow(
    ax_task: Path, workflow_path: Path, project_root: Path
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ax_task),
        "--project-root",
        str(project_root),
        "render",
        "--workflow",
        str(workflow_path),
    ]
    result = subprocess.run(
        command,
        cwd=project_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ControlError(
            "ax_task.py render failed: "
            + (result.stderr.strip() or result.stdout.strip())
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ControlError(f"ax_task.py render returned invalid JSON: {exc}") from exc


def walk_values(value: Any) -> Iterator[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child)


class OrcaTerminalBroker:
    """Direct visible-terminal adapter; no Orca lifecycle objects."""

    def __init__(
        self,
        project_root: Path,
        *,
        command: str = "orca",
        agent_command: str = "codex",
        confirm_seconds: float = 10.0,
    ):
        self.project_root = project_root.resolve()
        self.command = shlex.split(command)
        self.agent_command = agent_command
        self.confirm_seconds = confirm_seconds

    def run(self, args: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
        command = [*self.command, *args, "--json"]
        result = subprocess.run(
            command,
            cwd=self.project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ControlError(
                f"Orca returned invalid JSON for {' '.join(command)}: {exc}"
            ) from exc
        if result.returncode != 0 or not data.get("ok", False):
            if allow_failure:
                return data
            raise ControlError(
                f"Orca command failed: {' '.join(command)}: "
                f"{data.get('error') or result.stderr.strip()}"
            )
        return data

    def list_terminals(self) -> list[dict[str, Any]]:
        data = self.run(
            [
                "terminal",
                "list",
                "--worktree",
                f"path:{self.project_root}",
            ]
        )
        rows = data.get("result", {}).get("terminals", [])
        return rows if isinstance(rows, list) else []

    def show(self, worker: str) -> dict[str, Any] | None:
        data = self.run(
            ["terminal", "show", "--terminal", worker], allow_failure=True
        )
        terminal = data.get("result", {}).get("terminal")
        return terminal if data.get("ok") and isinstance(terminal, dict) else None

    def is_idle(self, worker: str, timeout_ms: int = 1) -> bool:
        data = self.run(
            [
                "terminal",
                "wait",
                "--terminal",
                worker,
                "--for",
                "tui-idle",
                "--timeout-ms",
                str(timeout_ms),
            ],
            allow_failure=True,
        )
        return bool(data.get("ok"))

    def acquire_worker(
        self, excluded: set[str], task_id: str
    ) -> tuple[str, int | None, bool]:
        for row in sorted(
            self.list_terminals(), key=lambda item: str(item.get("handle", ""))
        ):
            worker = row.get("handle")
            if not isinstance(worker, str) or worker in excluded:
                continue
            if Path(row.get("worktreePath", "")).resolve() != self.project_root:
                continue
            shown = self.show(worker)
            if (
                not shown
                or not shown.get("connected")
                or not shown.get("writable")
                or not self.is_idle(worker)
            ):
                continue
            return worker, shown.get("lastOutputAt"), False
        data = self.run(
            [
                "terminal",
                "create",
                "--worktree",
                f"path:{self.project_root}",
                "--title",
                f"AX swarm {task_id}",
                "--command",
                self.agent_command,
            ]
        )
        worker = next(
            (
                item
                for item in walk_values(data)
                if isinstance(item, str) and item.startswith("term_")
            ),
            None,
        )
        if worker is None:
            raise ControlError("Orca terminal create returned no terminal handle")
        deadline = time.monotonic() + self.confirm_seconds
        while time.monotonic() < deadline:
            if self.is_idle(worker, timeout_ms=250):
                shown = self.show(worker) or {}
                return worker, shown.get("lastOutputAt"), True
        raise ControlError(f"new Orca child {worker} did not become idle")

    def send(self, worker: str, prompt: str) -> None:
        self.run(
            [
                "terminal",
                "send",
                "--terminal",
                worker,
                "--text",
                prompt,
                "--enter",
            ]
        )

    def execution_started(
        self,
        worker: str,
        previous_output_at: int | None,
        result_path: Path,
        baseline: dict[str, Any] | None,
        *,
        wait: bool,
    ) -> bool:
        deadline = time.monotonic() + (self.confirm_seconds if wait else 0.0)
        while True:
            if not fingerprint_equal(result_fingerprint(result_path), baseline):
                return True
            shown = self.show(worker)
            if shown and shown.get("connected") and shown.get("writable"):
                current = shown.get("lastOutputAt")
                if current is not None and current != previous_output_at:
                    return True
                if not self.is_idle(worker):
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.25)


def worker_prompt(
    workflow: dict, task: dict, attempt: int, result_path: Path
) -> str:
    return f"""[AX-TASK-SWARM-AUTO workflow={workflow['workflow_id']} task={task['id']} attempt={attempt}]
目标：
{task.get('spec', '')}

Execution mode: {task.get('execution', 'shared')}
Owned resources: {', '.join(task.get('resources', [])) or 'none'}
Shared worktree: {workflow.get('project_root')}
Result path: {result_path}

先读 AGENTS.md 与适用 skill。你在任务边界内有完整执行授权；不要请求内部审批，
不要建立 checkpoint/evidence pack，不要创建 Orca lifecycle，不要修改父 workflow，
不要 push。完成后只原子写一行：
{task['id']}|completed|一行摘要
真实人类专属阻塞才写：
{task['id']}|human-blocked|人类最小动作
写完停止。
"""


def claim(
    state: dict,
    tasks: dict[str, dict],
    task_id: str,
    lane: str,
    worktree: str,
    results_dir: Path,
) -> dict:
    if task_id not in tasks:
        raise ControlError(f"unknown task {task_id}")
    result_path = str(results_dir / f"{task_id}.result")
    existing = state["active"].get(task_id)
    if existing:
        expected = (existing["worktree"], existing["result_path"])
        actual = (worktree, result_path)
        if expected != actual:
            raise ControlError(
                "token continuation must keep the same task/worktree/result"
            )
        existing["lane"] = lane
        return {"action": "resume", **existing}
    if task_id not in {item["task"] for item in ready_tasks(tasks, state)}:
        raise ControlError(f"{task_id} is not dependency/resource ready")
    record = {
        "task": task_id,
        "lane": lane,
        "worktree": worktree,
        "result_path": result_path,
        "resources": tasks[task_id].get("resources", []),
    }
    state["active"][task_id] = record
    return {"action": "dispatch", **record}


def record_route(state: dict, first_bad: str, route: str, task_id: str) -> dict:
    routes = state["routes"].setdefault(first_bad, {})
    if route not in routes and len(routes) >= 3:
        raise ControlError(f"{first_bad} already has three independent routes")
    routes.setdefault(route, task_id)
    if routes[route] != task_id:
        raise ControlError(f"route {route} already belongs to {routes[route]}")
    return {"first_bad": first_bad, "routes": routes}


def promote(
    state: dict,
    first_bad: str,
    generation: str,
    task_id: str,
    worktree: str,
    base_commit: str,
    clean: bool,
    canonical_base: str | None,
) -> dict:
    if canonical_base is None:
        raise ControlError(
            "candidate promotion requires a workflow or explicit canonical base"
        )
    if not clean or base_commit != canonical_base:
        raise ControlError(
            f"candidate promotion requires a clean exact main@{canonical_base} replay lane"
        )
    current = state["promotions"].get(first_bad)
    proposed = {
        "generation": generation,
        "task": task_id,
        "worktree": worktree,
        "base_commit": base_commit,
    }
    if current and current != proposed:
        raise ControlError(
            f"{first_bad} already promoted {current['generation']} from {current['task']}"
        )
    state["promotions"][first_bad] = proposed
    return {"first_bad": first_bad, **proposed}


def verify_consumed_results_unchanged(state: dict) -> None:
    for task_id, record in state["results"].items():
        expected = record.get("fingerprint")
        path_value = record.get("path")
        if expected is None or not path_value:
            continue
        current = result_fingerprint(Path(path_value))
        if not fingerprint_equal(current, expected):
            raise ControlError(
                f"consumed result changed for {task_id}: {path_value}"
            )


def finish_dispatch(
    workflow: dict,
    state: dict,
    tasks: dict[str, dict],
    task_id: str,
) -> dict[str, Any]:
    record = state["pending"].pop(task_id)
    task = tasks[task_id]
    attempt = int(record["attempt"])
    task["state"] = "dispatched"
    task["attempts"] = attempt
    task["result"] = None
    task["blocker"] = None
    task.setdefault("orca", {}).update(
        task_id=None,
        dispatch_id=None,
        worker=record["worker"],
    )
    record["confirmed_at"] = now()
    state["active"][task_id] = record
    return {
        "task": task_id,
        "attempt": attempt,
        "worker": record["worker"],
        "created": bool(record.get("created")),
    }


def update_runtime_projection(workflow: dict, tasks: dict[str, dict]) -> None:
    runtime = workflow.setdefault("runtime", {})
    active = [
        task_id
        for task_id, task in tasks.items()
        if task.get("state") in ACTIVE_TASK_STATES
    ]
    runtime["active_task"] = active[0] if active else None
    if all(task.get("state") == "completed" for task in tasks.values()):
        runtime["phase"] = "completed"
    elif active:
        runtime["phase"] = "running"
    else:
        runtime["phase"] = "confirmed"


def autoloop_cycle(
    workflow_path: Path,
    state_path: Path,
    results_dir: Path,
    human_todo: Path,
    *,
    ax_task: Path = DEFAULT_AX_TASK,
    explicit_base: str | None = None,
    repo: Path | None = None,
    broker: Any | None = None,
    dry_run: bool = False,
    allow_plan_drift: bool = False,
) -> dict[str, Any]:
    workflow = read_json(workflow_path)
    tasks = task_map(workflow)
    plan_hash = inspect_plan_hash(
        workflow, allow_drift=allow_plan_drift
    )
    canonical_base = resolve_canonical_base(workflow, explicit_base)
    local_main = verify_local_main(workflow, canonical_base, repo)
    state = load_state(state_path, workflow, canonical_base)
    if dry_run:
        workflow = copy.deepcopy(workflow)
        tasks = task_map(workflow)
        state = copy.deepcopy(state)
    verify_consumed_results_unchanged(state)
    state_changed = adopt_parent_active_tasks(
        workflow, state, tasks, results_dir
    )

    consumed, workflow_changed = consume_parent_results(
        workflow,
        state,
        tasks,
        results_dir,
    )
    state_changed = state_changed or bool(consumed)
    confirmed: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    # A persisted reservation is never sent twice.  A changed output/result is
    # sufficient confirmation after a process restart.
    if broker is not None and not dry_run:
        for task_id, record in list(state["pending"].items()):
            try:
                if broker.execution_started(
                    record["worker"],
                    record.get("last_output_at"),
                    Path(record["result_path"]),
                    record.get("baseline"),
                    wait=False,
                ):
                    confirmed.append(
                        finish_dispatch(workflow, state, tasks, task_id)
                    )
                    workflow_changed = True
                    state_changed = True
            except ControlError as exc:
                errors.append({"task": task_id, "error": str(exc)})

    ready = ready_tasks(tasks, state)
    planned = [item["task"] for item in ready]
    if broker is not None and not dry_run:
        control_worker = (
            workflow.get("source", {})
            .get("terminal", {})
            .get("identity", {})
            .get("terminal_handle")
        )
        excluded = {
            record.get("worker")
            for records in (state["active"], state["pending"])
            for record in records.values()
            if record.get("worker")
        }
        if control_worker:
            excluded.add(control_worker)
        for item in ready:
            task_id = item["task"]
            task = tasks[task_id]
            attempt = int(task.get("attempts", 0)) + 1
            result_path = results_dir / f"{task_id}.result"
            try:
                worker, last_output_at, created = broker.acquire_worker(
                    excluded, task_id
                )
                excluded.add(worker)
                record = {
                    "task": task_id,
                    "attempt": attempt,
                    "worker": worker,
                    "worktree": str(
                        Path(workflow["project_root"]).resolve()
                    ),
                    "result_path": str(result_path),
                    "resources": task.get("resources", []),
                    "baseline": result_fingerprint(result_path),
                    "last_output_at": last_output_at,
                    "created": created,
                    "reserved_at": now(),
                    "delivered": False,
                    "dispatch_key": (
                        f"{workflow['workflow_id']}:{task_id}:{attempt}"
                    ),
                }
                state["pending"][task_id] = record
                write_json(state_path, state)
                broker.send(
                    worker,
                    worker_prompt(workflow, task, attempt, result_path),
                )
                record["delivered"] = True
                record["delivered_at"] = now()
                write_json(state_path, state)
                if broker.execution_started(
                    worker,
                    last_output_at,
                    result_path,
                    record["baseline"],
                    wait=True,
                ):
                    confirmed.append(
                        finish_dispatch(workflow, state, tasks, task_id)
                    )
                    workflow_changed = True
                else:
                    errors.append(
                        {
                            "task": task_id,
                            "error": (
                                "delivery is pending execution confirmation; "
                                "it will not be sent twice"
                            ),
                        }
                    )
                state_changed = True
            except ControlError as exc:
                # Once a reservation exists, keep it until the terminal/result
                # proves whether delivery started.  Retrying an ambiguous send
                # would violate at-most-once dispatch.
                errors.append({"task": task_id, "error": str(exc)})

    human_items: list[str] = []
    if workflow_changed:
        update_runtime_projection(workflow, tasks)
        workflow["updated_at"] = now()
        if not dry_run:
            write_json(workflow_path, workflow, sort_keys=False)
            render_workflow(
                ax_task,
                workflow_path,
                Path(workflow["project_root"]).resolve(),
            )
    human_items = refresh_human_todo(
        workflow,
        tasks,
        human_todo,
        results_dir=results_dir,
        dry_run=dry_run,
    )
    if state_changed and not dry_run:
        write_json(state_path, state)
    return {
        "workflow_id": workflow.get("workflow_id"),
        "canonical_base": canonical_base,
        "local_main": local_main,
        "plan_hash": plan_hash,
        "dry_run": dry_run,
        "consumed": consumed,
        "confirmed": confirmed,
        "planned": planned,
        "active": list(state["active"].values()),
        "pending": list(state["pending"].values()),
        "human_todo": human_items,
        "errors": errors,
        "next_tick_seconds": MAX_REFILL_SECONDS,
    }


def run_autoloop(
    workflow_path: Path,
    state_path: Path,
    results_dir: Path,
    human_todo: Path,
    lock_path: Path,
    *,
    interval: int,
    once: bool,
    dry_run: bool,
    ax_task: Path,
    explicit_base: str | None,
    repo: Path | None,
    orca_command: str,
    agent_command: str,
    confirm_seconds: float,
    allow_plan_drift: bool,
) -> list[dict[str, Any]]:
    if not 1 <= interval <= MAX_REFILL_SECONDS:
        raise ControlError(
            f"--interval must be between 1 and {MAX_REFILL_SECONDS} seconds"
        )
    project_root = (
        repo
        or Path(read_json(workflow_path).get("project_root", "."))
    ).resolve()
    broker = None
    if not dry_run:
        broker = OrcaTerminalBroker(
            project_root,
            command=orca_command,
            agent_command=agent_command,
            confirm_seconds=confirm_seconds,
        )
    outputs: list[dict[str, Any]] = []
    with controller_lock(lock_path):
        while True:
            output = autoloop_cycle(
                workflow_path,
                state_path,
                results_dir,
                human_todo,
                ax_task=ax_task,
                explicit_base=explicit_base,
                repo=repo,
                broker=broker,
                dry_run=dry_run,
                allow_plan_drift=allow_plan_drift,
            )
            outputs.append(output)
            print(json.dumps(output, ensure_ascii=False, sort_keys=True))
            if once or dry_run:
                break
            time.sleep(interval)
    return outputs


def tick(
    workflow_path: Path,
    state_path: Path,
    results_dir: Path,
    explicit_base: str | None = None,
    repo: Path | None = None,
) -> dict:
    workflow = read_json(workflow_path)
    tasks = task_map(workflow)
    canonical_base = resolve_canonical_base(workflow, explicit_base)
    local_main = verify_local_main(workflow, canonical_base, repo)
    state = load_state(state_path, workflow, canonical_base)
    consumed = consume_results(state, results_dir, tasks)
    output = {
        "workflow_id": workflow.get("workflow_id"),
        "canonical_base": canonical_base,
        "local_main": local_main,
        "consumed": consumed,
        "active": list(state["active"].values()),
        "ready": ready_tasks(tasks, state),
        "human_blocked": [
            {"task": task_id, **result}
            for task_id, result in state["results"].items()
            if result["status"] == "human-blocked"
        ],
        "promotions": state["promotions"],
        "next_tick_seconds": MAX_REFILL_SECONDS,
    }
    write_json(state_path, state)
    return output


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workflow", required=True, type=Path)
    result.add_argument("--state", required=True, type=Path)
    result.add_argument("--results", required=True, type=Path)
    result.add_argument("--canonical-base")
    result.add_argument("--repo", type=Path)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("tick")
    autoloop_parser = commands.add_parser("autoloop")
    autoloop_parser.add_argument("--once", action="store_true")
    autoloop_parser.add_argument("--dry-run", action="store_true")
    autoloop_parser.add_argument(
        "--interval", type=int, default=MAX_REFILL_SECONDS
    )
    autoloop_parser.add_argument("--lock", type=Path)
    autoloop_parser.add_argument("--human-todo", type=Path)
    autoloop_parser.add_argument(
        "--ax-task", type=Path, default=DEFAULT_AX_TASK
    )
    autoloop_parser.add_argument("--orca-command", default="orca")
    autoloop_parser.add_argument("--agent-command", default="codex")
    autoloop_parser.add_argument("--confirm-seconds", type=float, default=10.0)
    autoloop_parser.add_argument(
        "--allow-plan-drift",
        action="store_true",
        help="continue after reporting a drift covered by explicit owner authorization",
    )
    claim_parser = commands.add_parser("claim")
    claim_parser.add_argument("task")
    claim_parser.add_argument("--lane", required=True)
    claim_parser.add_argument("--worktree", required=True)
    route_parser = commands.add_parser("route")
    route_parser.add_argument("--first-bad", required=True)
    route_parser.add_argument("--route", required=True)
    route_parser.add_argument("--task", required=True)
    promote_parser = commands.add_parser("promote")
    promote_parser.add_argument("--first-bad", required=True)
    promote_parser.add_argument("--generation", required=True)
    promote_parser.add_argument("--task", required=True)
    promote_parser.add_argument("--worktree", required=True)
    promote_parser.add_argument("--base-commit", required=True)
    promote_parser.add_argument("--clean", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "tick":
            output = tick(
                args.workflow,
                args.state,
                args.results,
                explicit_base=args.canonical_base,
                repo=args.repo,
            )
            print(json.dumps(output, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "autoloop":
            workflow = read_json(args.workflow)
            project_root = (
                args.repo or Path(workflow.get("project_root", "."))
            ).resolve()
            human_todo = args.human_todo or project_root / ".HumanTodoList.md"
            lock_path = args.lock or args.state.with_suffix(
                args.state.suffix + ".lock"
            )
            if args.confirm_seconds < 0 or args.confirm_seconds > 60:
                raise ControlError(
                    "--confirm-seconds must be between 0 and 60"
                )
            run_autoloop(
                args.workflow,
                args.state,
                args.results,
                human_todo,
                lock_path,
                interval=args.interval,
                once=args.once,
                dry_run=args.dry_run,
                ax_task=args.ax_task,
                explicit_base=args.canonical_base,
                repo=args.repo,
                orca_command=args.orca_command,
                agent_command=args.agent_command,
                confirm_seconds=args.confirm_seconds,
                allow_plan_drift=args.allow_plan_drift,
            )
            return 0
        workflow = read_json(args.workflow)
        tasks = task_map(workflow)
        canonical_base = resolve_canonical_base(workflow, args.canonical_base)
        local_main = verify_local_main(workflow, canonical_base, args.repo)
        state = load_state(args.state, workflow, canonical_base)
        if args.command == "claim":
            consume_results(state, args.results, tasks)
            output = claim(
                state, tasks, args.task, args.lane, args.worktree, args.results
            )
            write_json(args.state, state)
        elif args.command == "route":
            if args.task not in tasks:
                raise ControlError(f"unknown task {args.task}")
            output = record_route(state, args.first_bad, args.route, args.task)
            write_json(args.state, state)
        else:
            if local_main is None:
                raise ControlError(
                    "candidate promotion requires workflow project_root or --repo"
                )
            if args.task not in tasks:
                raise ControlError(f"unknown task {args.task}")
            output = promote(
                state,
                args.first_bad,
                args.generation,
                args.task,
                args.worktree,
                args.base_commit,
                args.clean,
                canonical_base,
            )
            write_json(args.state, state)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 0
    except ControlError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
