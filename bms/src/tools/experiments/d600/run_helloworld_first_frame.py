#!/usr/bin/env python3
"""Config-driven D600 HelloWorld cold-start developer evidence runner.

The default invocation validates configuration only.  Device access requires
the explicit ``--apply`` flag, a HELD lease and a matching device-generation
identity.  All preflight probes use the read-only ``query`` interface; no
``action`` is permitted until every precondition passes.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import shlex
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

import helloworld_first_frame_contract as contract


DEFAULT_CONFIG = Path(__file__).with_name("config") / "helloworld-first-frame.yaml"
DEFAULT_SAMPLE_INTERVAL_SECONDS = 0.075
DEFAULT_DEADLINE_SECONDS = 15.0
DEFAULT_HOLD_SECONDS = 5.0
PACKAGE_TOKEN_RE_TEMPLATE = r"(?<![A-Za-z0-9_.]){package}(?![A-Za-z0-9_.])"


@dataclass(frozen=True)
class LeaseBinding:
    serial: str
    owner: str
    writer_terminal: str
    worktree: str
    acquired_at: str
    status: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "LeaseBinding":
        required = {
            "serial",
            "owner",
            "writer_terminal",
            "worktree",
            "acquired_at",
            "status",
        }
        missing = sorted(required - set(value))
        if missing:
            raise contract.ContractError(f"lease: missing fields {missing}")
        fields: dict[str, str] = {}
        for name in required:
            raw = value[name]
            if not isinstance(raw, str) or not raw.strip():
                raise contract.ContractError(f"lease.{name}: required non-empty string")
            fields[name] = raw.strip()
        return cls(**fields)


DEFAULT_PROBE_COMMANDS = {
    "boot_id": "cat /proc/sys/kernel/random/boot_id",
    "installed_apk_sha256": (
        "sha256sum /data/app/el1/bundle/public/"
        f"{contract.HELLOWORLD_PACKAGE}/android/base.apk"
    ),
    "generation_id": "cat /data/local/tmp/bridge-current-generation.id",
    "generation_readback_sha256": (
        "sha256sum /data/local/tmp/bridge-current-generation-readback.json"
    ),
    # OpenHarmony truncates the Linux comm field for this package, so pidof can
    # miss a live ``com.example.helloworld`` child.  Resolve the bundle PID from
    # AbilityManager and only report it when the exact /proc identity is live.
    "old_pid": (
        "pid=$(aa dump -a 2>/dev/null | "
        "grep -A2 'process name \\[com.example.helloworld\\]' | "
        "grep 'pid #' | sed -n 's/.*pid #\\([0-9][0-9]*\\).*/\\1/p' | "
        "sed -n '1p'); "
        "if [ -n \"$pid\" ] && [ -r \"/proc/$pid/stat\" ]; then echo \"$pid\"; fi"
    ),
    "old_session": "aa dump -a 2>/dev/null || true",
    "home_negative": (
        "if aa dump -a 2>/dev/null | grep -F '"
        f"{contract.HELLOWORLD_PACKAGE}"
        "' >/dev/null; then echo HOME_CONTAMINATED; else echo HOME_NEGATIVE; fi"
    ),
}


DEFAULT_PRE_LAUNCH_ACTIONS = {
    # D600 OH 6.1 exposes the Mali character device as root:root 0660.  The
    # Android child is uid 20010057/group 3099, so EGL reaches the real
    # OHNativeWindow and then fails opening the kernel driver.  The mode may be
    # restored by the system later; prepare it immediately before each guarded
    # launch and fail closed if the expected access was not applied.
    "prepare_gpu_device_access": (
        "chmod 0666 /dev/mali0 && "
        "ls -l /dev/mali0 | grep -q '^crw-rw-rw-'"
    ),
}


@dataclass(frozen=True)
class PreflightExpectations:
    serial: str
    boot_id: str
    apk_sha256: str
    generation_id: str
    generation_readback_sha256: str
    package_name: str
    activity_name: str
    lease: LeaseBinding
    current_worktree: str
    writer_terminal: str
    probe_commands: Mapping[str, str] = field(
        default_factory=lambda: dict(DEFAULT_PROBE_COMMANDS)
    )


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    errors: tuple[str, ...]
    observed: Mapping[str, str]


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    start_ticks: int
    parent_pid: int
    package_name: str


@dataclass(frozen=True)
class FrameObservation:
    role: str
    captured_at_monotonic: float
    non_black: bool
    expected_text_visible: bool
    boot_id: str
    generation_id: str
    process: ProcessIdentity
    window_id: str


@dataclass(frozen=True)
class CrashEvidence:
    signature: str
    first_bad: str
    artifact_refs: tuple[str, ...]


@dataclass(frozen=True)
class CandidateObservation:
    launch_started_at_monotonic: float
    process: ProcessIdentity | None
    process_alive: bool
    on_resume: bool
    app_window_visible: bool
    present_observed: bool
    frames: tuple[FrameObservation, ...]
    crash: CrashEvidence | None = None


@dataclass(frozen=True)
class RuntimeIdentity:
    boot_id: str
    generation_id: str
    process: ProcessIdentity | None


@dataclass(frozen=True)
class SampleResult:
    identities: Mapping[tuple[int, int], ProcessIdentity]
    sample_times: tuple[float, ...]
    elapsed_seconds: float


@dataclass(frozen=True)
class HoldResult:
    stable: bool
    reason: str | None
    elapsed_seconds: float
    last_identity: RuntimeIdentity


@dataclass(frozen=True)
class CandidateTrace:
    preflight_ok: bool
    launch_accepted: bool
    process: ProcessIdentity | None
    process_alive: bool
    on_resume: bool
    app_window_visible: bool
    present_observed: bool
    hello_world_visible: bool
    first_frame_seconds: float | None
    hold_seconds: float
    hold_reason: str | None


@dataclass(frozen=True)
class EvaluatedCandidateObservation:
    trace: CandidateTrace
    frames: tuple[FrameObservation, ...]
    crash_evidence: CrashEvidence | None = None


@dataclass(frozen=True)
class CandidateOutcome:
    terminal_state: str
    errors: tuple[str, ...] = ()
    preflight: PreflightResult | None = None
    trace: CandidateTrace | None = None
    crash_evidence: CrashEvidence | None = None


class DevicePort(Protocol):
    serial: str

    def query(self, name: str, command: str) -> subprocess.CompletedProcess[str]: ...

    def action(self, name: str, command: str) -> subprocess.CompletedProcess[str]: ...


class StreamingDevicePort(DevicePort, Protocol):
    def start_stream(self, name: str, command: str) -> subprocess.Popen[str]: ...


class LiveObserver(Protocol):
    def before_launch(
        self, device: StreamingDevicePort, expectations: PreflightExpectations
    ) -> None: ...

    def after_launch(
        self,
        device: StreamingDevicePort,
        expectations: PreflightExpectations,
        *,
        launch_started_at_monotonic: float,
    ) -> CandidateObservation | EvaluatedCandidateObservation: ...

    def close(self) -> None: ...


class HdcDevice:
    """Explicit D600 transport with separate read-only and mutating methods."""

    def __init__(
        self,
        hdc: str,
        serial: str,
        *,
        raw_output_root: Path | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.hdc = hdc
        self.serial = serial
        self.raw_output_root = raw_output_root
        self.timeout_seconds = timeout_seconds

    def _run(self, kind: str, name: str, command: str) -> subprocess.CompletedProcess[str]:
        argv = [self.hdc, "-t", self.serial, "shell", command]
        try:
            result = subprocess.run(
                argv,
                text=True,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            result = subprocess.CompletedProcess(argv, 124, "", str(error))
        self._record(kind, name, argv, result)
        return result

    def _record(
        self,
        kind: str,
        name: str,
        argv: Sequence[str],
        result: subprocess.CompletedProcess[str],
    ) -> None:
        if self.raw_output_root is None:
            return
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        target = self.raw_output_root / "raw" / f"{kind}-{safe}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "argv": list(argv),
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def query(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
        return self._run("query", name, command)

    def action(self, name: str, command: str) -> subprocess.CompletedProcess[str]:
        return self._run("action", name, command)

    def start_stream(self, name: str, command: str) -> subprocess.Popen[str]:
        """Start a continuous device stream; the caller owns termination."""
        argv = [self.hdc, "-t", self.serial, "shell", command]
        try:
            return subprocess.Popen(
                argv,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            raise RuntimeError(f"cannot start device stream {name}: {error}") from error

    def receive(self, remote_path: str, local_path: Path) -> subprocess.CompletedProcess[str]:
        """Receive a declared device artifact without changing device state."""
        argv = [self.hdc, "-t", self.serial, "file", "recv", remote_path, str(local_path)]
        try:
            result = subprocess.run(
                argv,
                text=True,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            result = subprocess.CompletedProcess(argv, 124, "", str(error))
        self._record("receive", local_path.name, argv, result)
        return result


def _first_token(value: str) -> str:
    fields = value.strip().split()
    return fields[0] if fields else ""


def _same_path(left: str, right: str) -> bool:
    return Path(left).resolve() == Path(right).resolve()


def _package_seen(value: str, package_name: str) -> bool:
    pattern = PACKAGE_TOKEN_RE_TEMPLATE.format(package=re.escape(package_name))
    return re.search(pattern, value) is not None


def validate_lease(expectations: PreflightExpectations, device_serial: str) -> list[str]:
    lease = expectations.lease
    errors: list[str] = []
    if lease.status != "HELD":
        errors.append(f"lease.status: required HELD, observed {lease.status}")
    if lease.serial != expectations.serial:
        errors.append("lease.serial: does not match configured serial")
    if device_serial != expectations.serial:
        errors.append("device.serial: does not match HELD lease serial")
    if not _same_path(lease.worktree, expectations.current_worktree):
        errors.append("lease.worktree: does not match current worktree")
    if lease.writer_terminal != expectations.writer_terminal:
        errors.append("lease.writer_terminal: does not match current writer")
    if not lease.owner.strip() or not lease.acquired_at.strip():
        errors.append("lease: owner and acquired_at are required")
    return errors


def collect_preflight(
    device: DevicePort, expectations: PreflightExpectations
) -> PreflightResult:
    """Collect and validate preconditions without invoking ``device.action``."""
    errors = validate_lease(expectations, device.serial)
    if errors:
        return PreflightResult(False, tuple(errors), {})

    required_probes = (
        "boot_id",
        "installed_apk_sha256",
        "generation_id",
        "generation_readback_sha256",
        "old_pid",
        "old_session",
        "home_negative",
    )
    observed: dict[str, str] = {}
    for name in required_probes:
        command = expectations.probe_commands.get(name)
        if not isinstance(command, str) or not command.strip():
            errors.append(f"probe_commands.{name}: required command")
            continue
        try:
            result = device.query(name, command)
        except Exception as error:  # A fake or transport may fail before returning a receipt.
            errors.append(f"{name}: query raised {type(error).__name__}: {error}")
            continue
        if result.returncode != 0:
            errors.append(
                f"{name}: query failed rc={result.returncode} stderr={result.stderr.strip()!r}"
            )
            continue
        observed[name] = result.stdout.strip()

    if errors:
        return PreflightResult(False, tuple(errors), observed)

    if observed["boot_id"] != expectations.boot_id:
        errors.append(
            f"boot_id: expected {expectations.boot_id}, observed {observed['boot_id']}"
        )
    apk = _first_token(observed["installed_apk_sha256"])
    if apk != expectations.apk_sha256:
        errors.append(f"installed_apk_sha256: expected {expectations.apk_sha256}, observed {apk}")
    generation = _first_token(observed["generation_id"])
    if generation != expectations.generation_id:
        errors.append(
            f"generation_id: expected {expectations.generation_id}, observed {generation}"
        )
    readback = _first_token(observed["generation_readback_sha256"])
    if readback != expectations.generation_readback_sha256:
        errors.append(
            "generation_readback_sha256: expected "
            f"{expectations.generation_readback_sha256}, observed {readback}"
        )
    if observed["old_pid"].strip():
        errors.append(f"old_pid: pre-existing process observed {observed['old_pid']!r}")
    if _package_seen(observed["old_session"], expectations.package_name):
        errors.append("old_session: pre-existing package session observed")
    if observed["home_negative"] != "HOME_NEGATIVE":
        errors.append(
            "home_negative: required exact HOME_NEGATIVE receipt, observed "
            f"{observed['home_negative']!r}"
        )
    return PreflightResult(not errors, tuple(errors), observed)


def parse_proc_stat(text: str, *, package_name: str) -> ProcessIdentity:
    """Parse PID, PPID and starttime without splitting a parenthesized comm."""
    value = text.strip()
    first_space = value.find(" ")
    closing = value.rfind(")")
    if first_space <= 0 or closing <= first_space:
        raise ValueError("malformed /proc/<pid>/stat")
    try:
        pid = int(value[:first_space])
    except ValueError as error:
        raise ValueError("malformed /proc/<pid>/stat pid") from error
    tail = value[closing + 1 :].strip().split()
    # tail[0] is field 3 (state), tail[1] field 4 (ppid), tail[19] field 22.
    if len(tail) < 20:
        raise ValueError("truncated /proc/<pid>/stat")
    try:
        parent_pid = int(tail[1])
        start_ticks = int(tail[19])
    except ValueError as error:
        raise ValueError("malformed /proc/<pid>/stat numeric identity") from error
    if pid <= 0 or parent_pid < 0 or start_ticks < 0:
        raise ValueError("invalid /proc/<pid>/stat identity")
    return ProcessIdentity(pid, start_ticks, parent_pid, package_name)


def same_process(left: ProcessIdentity, right: ProcessIdentity) -> bool:
    return (
        left.pid == right.pid
        and left.start_ticks == right.start_ticks
        and left.package_name == right.package_name
    )


def sample_short_lived_children(
    sample_once: Callable[[], Iterable[ProcessIdentity]],
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    interval_seconds: float = DEFAULT_SAMPLE_INTERVAL_SECONDS,
    deadline_seconds: float = DEFAULT_DEADLINE_SECONDS,
    on_first_identity: Callable[[ProcessIdentity], None] | None = None,
) -> SampleResult:
    """Sample on a monotonic 50-100 ms cadence and retain vanished children."""
    if not 0.05 <= interval_seconds <= 0.1:
        raise ValueError("child sampling interval must be within 50-100 ms")
    if (
        isinstance(deadline_seconds, bool)
        or not isinstance(deadline_seconds, (int, float))
        or not math.isfinite(deadline_seconds)
        or deadline_seconds <= 0
    ):
        raise ValueError("deadline_seconds must be finite and greater than zero")
    start = monotonic()
    identities: dict[tuple[int, int], ProcessIdentity] = {}
    sample_times: list[float] = []
    while True:
        elapsed = max(0.0, monotonic() - start)
        if elapsed > deadline_seconds + 1e-9:
            break
        sample_times.append(min(elapsed, float(deadline_seconds)))
        for identity in sample_once():
            key = (identity.pid, identity.start_ticks)
            if key not in identities:
                identities[key] = identity
                if on_first_identity is not None:
                    on_first_identity(identity)
        elapsed = max(0.0, monotonic() - start)
        if elapsed >= deadline_seconds - 1e-12:
            break
        sleep(min(interval_seconds, deadline_seconds - elapsed))
    return SampleResult(
        identities=identities,
        sample_times=tuple(sample_times),
        elapsed_seconds=min(max(0.0, monotonic() - start), float(deadline_seconds)),
    )


def _identity_change_reason(
    expected: RuntimeIdentity, current: RuntimeIdentity
) -> str | None:
    if current.boot_id != expected.boot_id:
        return "boot_changed"
    if current.generation_id != expected.generation_id:
        return "generation_changed"
    if current.process is None:
        return "process_missing"
    if expected.process is None:
        return "process_unexpected"
    if current.process.pid == expected.process.pid and (
        current.process.start_ticks != expected.process.start_ticks
    ):
        return "process_reused"
    if not same_process(expected.process, current.process):
        return "process_changed"
    return None


def hold_identity(
    probe: Callable[[], RuntimeIdentity],
    expected: RuntimeIdentity,
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    hold_seconds: float = DEFAULT_HOLD_SECONDS,
    check_interval_seconds: float = 0.25,
) -> HoldResult:
    if hold_seconds < DEFAULT_HOLD_SECONDS:
        raise ValueError("hold_seconds must be at least 5 seconds")
    if check_interval_seconds <= 0 or check_interval_seconds > hold_seconds:
        raise ValueError("invalid hold check interval")
    start = monotonic()
    last = expected
    while True:
        last = probe()
        reason = _identity_change_reason(expected, last)
        elapsed = max(0.0, monotonic() - start)
        if reason is not None:
            return HoldResult(False, reason, elapsed, last)
        if elapsed >= hold_seconds - 1e-12:
            return HoldResult(True, None, min(elapsed, hold_seconds), last)
        sleep(min(check_interval_seconds, hold_seconds - elapsed))


SKIA_LOADER_FAILURE_RE = re.compile(
    r"(?:SkPngDecoder|_ZN12SkPngDecoder5IsPng).{0,240}"
    r"(?:symbol not found|undefined symbol|relocating failed)|"
    r"(?:symbol not found|undefined symbol|relocating failed).{0,240}"
    r"(?:SkPngDecoder|_ZN12SkPngDecoder5IsPng)",
    re.IGNORECASE | re.DOTALL,
)


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{time.monotonic_ns()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_outcome(output_root: Path, outcome: CandidateOutcome) -> Path:
    target = output_root / "outcome.json"
    _write_json_atomic(target, asdict(outcome))
    return target


class LiveBaselineObserver:
    """Collect one launch-bound baseline without mutating the device generation.

    The streams are deliberately started only after the caller has completed the
    no-action preflight and before ``aa start``.  PID sampling runs in one device
    shell at a fixed cadence so hdc round-trip latency cannot hide a short-lived
    child.  Content success is intentionally impossible here: visual/OCR review
    belongs to the later candidate flow.
    """

    def __init__(
        self,
        output_root: Path,
        *,
        sample_interval_seconds: float = DEFAULT_SAMPLE_INTERVAL_SECONDS,
        deadline_seconds: float = DEFAULT_DEADLINE_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not 0.05 <= sample_interval_seconds <= 0.1:
            raise ValueError("child sampling interval must be within 50-100 ms")
        if deadline_seconds <= 0 or not math.isfinite(deadline_seconds):
            raise ValueError("observer deadline must be finite and greater than zero")
        self.output_root = output_root
        self.sample_interval_seconds = sample_interval_seconds
        self.deadline_seconds = deadline_seconds
        self.monotonic = monotonic
        self.sleep = sleep
        self._started_at_monotonic: float | None = None
        self._processes: list[subprocess.Popen[str]] = []
        self._threads: list[threading.Thread] = []
        self._identities: dict[tuple[int, int], ProcessIdentity] = {}
        self._candidate_identities: dict[tuple[int, int], ProcessIdentity] = {}
        self._identity_lock = threading.Lock()
        self._package_name = ""
        self._closed = False
        self._hilog_ready = threading.Event()
        self._sampler_ready = threading.Event()

    def _sampling_command(self, package_name: str) -> str:
        interval = f"{self.sample_interval_seconds:.3f}"
        iterations = max(1, math.ceil(self.deadline_seconds / self.sample_interval_seconds) + 2)
        package = shlex.quote(package_name)
        return f"""
package_name={package}
baseline=' '
for parent in $(pidof appspawn-x 2>/dev/null || true); do
  children_file="/proc/$parent/task/$parent/children"
  [ -r "$children_file" ] || continue
  for pid in $(cat "$children_file" 2>/dev/null || true); do
    baseline="$baseline$pid "
  done
done
printf 'BRIDGE_SAMPLER_READY\\n'
i=0
seen=' '
while [ "$i" -lt {iterations} ]; do
  printf 'BRIDGE_SAMPLE\\t%s\\n' "$i"
  candidates=' '
  for parent in $(pidof appspawn-x 2>/dev/null || true); do
    children_file="/proc/$parent/task/$parent/children"
    [ -r "$children_file" ] || continue
    for pid in $(cat "$children_file" 2>/dev/null || true); do
      candidates="$candidates$pid:$parent "
    done
  done
  for pid in $(pidof "$package_name" 2>/dev/null || true); do
    candidates="$candidates$pid:0 "
  done
  round_seen=' '
  for entry in $candidates; do
    pid="${{entry%%:*}}"
    observed_parent="${{entry#*:}}"
    case "$round_seen" in *" $pid "*) continue ;; esac
    round_seen="$round_seen$pid "
    if [ "$observed_parent" != 0 ]; then
      case "$baseline" in *" $pid "*) continue ;; esac
    fi
    procdir="/proc/$pid"
    [ -r "$procdir/stat" ] || continue
    first_arg="$(tr '\\000' '\\n' < "$procdir/cmdline" 2>/dev/null | sed -n '1p')"
    role='appspawn-child'
    case "$first_arg" in
      "$package_name"|"$package_name":*) role='package-bound' ;;
    esac
    printf 'BRIDGE_STAT\\t%s\\t%s\\t%s\\t' "$pid" "$role" "$observed_parent"
    cat "$procdir/stat" 2>/dev/null || true
    printf '\\n'
    snapshot_key="$pid:$role"
    case "$seen" in
      *" $snapshot_key "*) ;;
      *)
          seen="$seen$snapshot_key "
          printf 'BRIDGE_PROC_BEGIN\\t%s\\n' "$pid"
          printf 'BRIDGE_PROC_ROLE\\t%s\\n' "$role"
          printf 'BRIDGE_OBSERVED_PARENT\\t%s\\n' "$observed_parent"
          for name in stat status maps cmdline; do
            printf 'BRIDGE_FILE_BEGIN\\t%s\\n' "$name"
            if [ "$name" = cmdline ]; then
              tr '\\000' ' ' < "$procdir/$name" 2>/dev/null || true
              printf '\\n'
            else
              cat "$procdir/$name" 2>/dev/null || true
            fi
            printf 'BRIDGE_FILE_END\\t%s\\n' "$name"
          done
          printf 'BRIDGE_PROC_END\\t%s\\n' "$pid"
          ;;
    esac
  done
  i=$((i + 1))
  sleep {interval}
done
""".strip()

    def _start_plain_drain(
        self,
        stream: Any,
        target: Path,
        *,
        name: str,
        ready_marker: str | None = None,
        ready_event: threading.Event | None = None,
    ) -> None:
        def drain() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8", errors="replace") as output:
                if stream is not None:
                    for line in stream:
                        if ready_marker is not None and line.rstrip("\r\n") == ready_marker:
                            if ready_event is not None:
                                ready_event.set()
                            continue
                        output.write(line)
                        output.flush()

        thread = threading.Thread(target=drain, name=name, daemon=True)
        thread.start()
        self._threads.append(thread)

    def _save_proc_block(
        self,
        identity: ProcessIdentity | None,
        files: Mapping[str, list[str]],
        role: str,
    ) -> None:
        if identity is None:
            return
        target = self.output_root / "proc" / f"{identity.pid}-{identity.start_ticks}"
        if role == "appspawn-child":
            target /= "appspawn-child"
        target.mkdir(parents=True, exist_ok=True)
        for name in ("stat", "status", "maps", "cmdline"):
            content = "".join(files.get(name, []))
            (target / name).write_text(content, encoding="utf-8", errors="replace")

    def _start_sampler_drain(self, stream: Any, target: Path) -> None:
        def drain() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            current_identity: ProcessIdentity | None = None
            current_role = "appspawn-child"
            current_file: str | None = None
            current_files: dict[str, list[str]] = {}
            with target.open("w", encoding="utf-8", errors="replace") as output:
                if stream is None:
                    return
                for line in stream:
                    if line.rstrip("\r\n") == "BRIDGE_SAMPLER_READY":
                        self._sampler_ready.set()
                        continue
                    output.write(line)
                    output.flush()
                    if line.startswith("BRIDGE_STAT\t"):
                        fields = line.rstrip("\n").split("\t", 4)
                        if len(fields) == 5:
                            try:
                                identity = parse_proc_stat(
                                    fields[4], package_name=self._package_name
                                )
                            except ValueError:
                                continue
                            role = fields[2]
                            with self._identity_lock:
                                destination = (
                                    self._identities
                                    if role == "package-bound"
                                    else self._candidate_identities
                                )
                                destination.setdefault(
                                    (identity.pid, identity.start_ticks), identity
                                )
                            current_identity = identity
                            current_role = role
                    elif line.startswith("BRIDGE_PROC_BEGIN\t"):
                        current_files = {}
                        current_file = None
                    elif line.startswith("BRIDGE_PROC_ROLE\t"):
                        role = line.rstrip("\n").split("\t", 1)[-1]
                        current_role = (
                            role
                            if role in {"appspawn-child", "package-bound"}
                            else "appspawn-child"
                        )
                    elif line.startswith("BRIDGE_OBSERVED_PARENT\t"):
                        continue
                    elif line.startswith("BRIDGE_FILE_BEGIN\t"):
                        candidate = line.rstrip("\n").split("\t", 1)[-1]
                        current_file = candidate if candidate in {"stat", "status", "maps", "cmdline"} else None
                        if current_file is not None:
                            current_files[current_file] = []
                    elif line.startswith("BRIDGE_FILE_END\t"):
                        current_file = None
                    elif line.startswith("BRIDGE_PROC_END\t"):
                        self._save_proc_block(
                            current_identity, current_files, current_role
                        )
                        current_file = None
                        current_files = {}
                    elif current_file is not None:
                        current_files[current_file].append(line)
                if current_files:
                    self._save_proc_block(current_identity, current_files, current_role)

        thread = threading.Thread(target=drain, name="p0-pid-sampler-drain", daemon=True)
        thread.start()
        self._threads.append(thread)

    def before_launch(
        self, device: StreamingDevicePort, expectations: PreflightExpectations
    ) -> None:
        if self._started_at_monotonic is not None:
            raise RuntimeError("live observer already started")
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._package_name = expectations.package_name
        self._started_at_monotonic = self.monotonic()
        self._closed = False
        try:
            hilog = device.start_stream(
                "continuous_hilog",
                "printf 'BRIDGE_HILOG_READY\\n'; exec hilog",
            )
            self._processes.append(hilog)
            self._start_plain_drain(
                hilog.stdout,
                self.output_root / "full-continuous-hilog.txt",
                name="p0-hilog-stdout",
                ready_marker="BRIDGE_HILOG_READY",
                ready_event=self._hilog_ready,
            )
            self._start_plain_drain(
                hilog.stderr,
                self.output_root / "full-continuous-hilog.stderr.txt",
                name="p0-hilog-stderr",
            )
            if not self._hilog_ready.wait(timeout=5.0):
                raise RuntimeError("continuous hilog stream did not become ready")

            sampler_command = self._sampling_command(expectations.package_name)
            sampler = device.start_stream("pid_proc_sampler", sampler_command)
            self._processes.append(sampler)
            self._start_sampler_drain(
                sampler.stdout, self.output_root / "pid-samples.txt"
            )
            self._start_plain_drain(
                sampler.stderr,
                self.output_root / "pid-samples.stderr.txt",
                name="p0-pid-sampler-stderr",
            )
            if not self._sampler_ready.wait(timeout=5.0):
                raise RuntimeError("PID/proc sampler did not become ready")
            _write_json_atomic(
                self.output_root / "observer-start.json",
                {
                    "schema_version": "bridge.p0.live-baseline-observer.v1",
                    "started_at_monotonic": self._started_at_monotonic,
                    "sample_interval_seconds": self.sample_interval_seconds,
                    "deadline_seconds": self.deadline_seconds,
                    "hilog_started_before_launch": True,
                    "sampler_started_before_launch": True,
                    "content_claim_allowed": False,
                },
            )
        except Exception:
            self.close()
            raise

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for process in reversed(self._processes):
            try:
                self._terminate_process(process)
            except (OSError, subprocess.SubprocessError):
                continue
        for thread in self._threads:
            thread.join(timeout=2.0)

    def _first_identity(self, hilog: str) -> ProcessIdentity | None:
        with self._identity_lock:
            bound = next(iter(self._identities.values()), None)
            candidates = tuple(self._candidate_identities.values())
        if bound is not None:
            return bound
        for candidate in candidates:
            pid_pattern = re.compile(rf"(?<![0-9]){candidate.pid}(?![0-9])")
            if any(
                pid_pattern.search(line) is not None
                and _package_seen(line, self._package_name)
                for line in hilog.splitlines()
            ):
                return candidate
        if (
            len(candidates) == 1
            and _package_seen(hilog, self._package_name)
            and SKIA_LOADER_FAILURE_RE.search(hilog) is not None
        ):
            return candidates[0]
        return None

    def _write_candidate_receipt(self) -> None:
        with self._identity_lock:
            candidates = tuple(self._candidate_identities.values())
            bound = tuple(self._identities.values())
        _write_json_atomic(
            self.output_root / "appspawn-child-candidates.json",
            {
                "schema_version": "bridge.p0.appspawn-child-candidates.v1",
                "claim_boundary": "PRE_EXEC_CANDIDATE_UNTIL_PACKAGE_OR_HILOG_BOUND",
                "candidates": [asdict(identity) for identity in candidates],
                "package_bound": [asdict(identity) for identity in bound],
            },
        )

    def _probe_process_alive(
        self, device: StreamingDevicePort, identity: ProcessIdentity
    ) -> bool:
        command = (
            f"if [ -r /proc/{identity.pid}/stat ]; then "
            f"cat /proc/{identity.pid}/stat; printf '\\nBRIDGE_CMDLINE\\t'; "
            f"tr '\\000' ' ' < /proc/{identity.pid}/cmdline 2>/dev/null || true; fi"
        )
        result = device.query("final_process_identity", command)
        if result.returncode != 0:
            return False
        lines = result.stdout.splitlines()
        if not lines:
            return False
        try:
            current = parse_proc_stat(lines[0], package_name=self._package_name)
        except ValueError:
            return False
        return same_process(identity, current) and _package_seen(
            result.stdout, self._package_name
        )

    def _artifact_refs(self) -> tuple[str, ...]:
        paths = [
            self.output_root / "full-continuous-hilog.txt",
            self.output_root / "pid-samples.txt",
            self.output_root / "appspawn-child-candidates.json",
        ]
        proc_root = self.output_root / "proc"
        if proc_root.is_dir():
            paths.extend(sorted(path for path in proc_root.rglob("*") if path.is_file()))
        return tuple(
            path.relative_to(self.output_root).as_posix()
            for path in paths
            if path.is_file()
        )

    def after_launch(
        self,
        device: StreamingDevicePort,
        expectations: PreflightExpectations,
        *,
        launch_started_at_monotonic: float,
    ) -> CandidateObservation:
        deadline = launch_started_at_monotonic + self.deadline_seconds
        while True:
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                break
            self.sleep(min(0.05, remaining))
        self.close()

        hilog_path = self.output_root / "full-continuous-hilog.txt"
        try:
            hilog = hilog_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            hilog = ""
        self._write_candidate_receipt()
        process = self._first_identity(hilog)
        process_alive = process is not None and self._probe_process_alive(device, process)
        failure = SKIA_LOADER_FAILURE_RE.search(hilog)
        crash: CrashEvidence | None = None
        if process is not None and not process_alive and failure is not None:
            failure_line = next(
                (
                    line
                    for line in hilog.splitlines()
                    if re.search(
                        r"SkPngDecoder|_ZN12SkPngDecoder5IsPng", line
                    )
                    and re.search(
                        r"symbol not found|undefined symbol|relocating failed",
                        line,
                        re.IGNORECASE,
                    )
                ),
                failure.group(0),
            )
            signature = " ".join(failure_line.split())[:1000]
            crash = CrashEvidence(
                signature=signature,
                first_bad="TARGET_SKIA_LOADER/MUSL_RELOCATION",
                artifact_refs=self._artifact_refs(),
            )
        on_resume = re.search(r"\bonResume\b", hilog, re.IGNORECASE) is not None
        observation = CandidateObservation(
            launch_started_at_monotonic=launch_started_at_monotonic,
            process=process,
            process_alive=process_alive,
            on_resume=on_resume,
            app_window_visible=False,
            present_observed=False,
            frames=(),
            crash=crash,
        )
        _write_json_atomic(
            self.output_root / "baseline-observation.json",
            asdict(observation),
        )
        return observation


def _validate_crash_evidence(crash: CrashEvidence) -> None:
    if not crash.signature.strip():
        raise contract.ContractError("observation.crash.signature: required string")
    if not crash.first_bad.strip():
        raise contract.ContractError("observation.crash.first_bad: required string")
    if not crash.artifact_refs:
        raise contract.ContractError("observation.crash.artifact_refs: required evidence")
    seen: set[str] = set()
    for index, reference in enumerate(crash.artifact_refs):
        if not isinstance(reference, str) or not reference.strip():
            raise contract.ContractError(
                f"observation.crash.artifact_refs[{index}]: required path"
            )
        path = Path(reference)
        if path.is_absolute() or ".." in path.parts or reference in seen:
            raise contract.ContractError(
                f"observation.crash.artifact_refs[{index}]: unsafe or duplicate path"
            )
        seen.add(reference)


def evaluate_candidate_observation(
    observation: CandidateObservation,
    expectations: PreflightExpectations,
) -> EvaluatedCandidateObservation:
    """Reduce same-run frame/crash facts to the typed T011 state machine."""
    launch_time = observation.launch_started_at_monotonic
    if (
        isinstance(launch_time, bool)
        or not isinstance(launch_time, (int, float))
        or not math.isfinite(launch_time)
        or launch_time < 0
    ):
        raise contract.ContractError(
            "observation.launch_started_at_monotonic: required finite non-negative number"
        )
    for field_name in (
        "process_alive",
        "on_resume",
        "app_window_visible",
        "present_observed",
    ):
        if not isinstance(getattr(observation, field_name), bool):
            raise contract.ContractError(f"observation.{field_name}: required boolean")

    crash = observation.crash
    if crash is not None:
        _validate_crash_evidence(crash)
        if observation.process_alive:
            raise contract.ContractError(
                "observation.crash: process_alive must be false for preserved crash"
            )

    by_role: dict[str, list[FrameObservation]] = {
        "FIRST_FRAME": [],
        "HOLD_END": [],
    }
    identity_reason: str | None = None
    expected_identity = RuntimeIdentity(
        expectations.boot_id,
        expectations.generation_id,
        observation.process,
    )
    for index, frame in enumerate(observation.frames):
        if frame.role not in by_role:
            raise contract.ContractError(
                f"observation.frames[{index}].role: required FIRST_FRAME or HOLD_END"
            )
        if (
            isinstance(frame.captured_at_monotonic, bool)
            or not isinstance(frame.captured_at_monotonic, (int, float))
            or not math.isfinite(frame.captured_at_monotonic)
            or frame.captured_at_monotonic < launch_time
        ):
            raise contract.ContractError(
                f"observation.frames[{index}].captured_at_monotonic: invalid timeline"
            )
        if not isinstance(frame.non_black, bool) or not isinstance(
            frame.expected_text_visible, bool
        ):
            raise contract.ContractError(
                f"observation.frames[{index}]: content results must be boolean"
            )
        if not frame.window_id.strip():
            raise contract.ContractError(
                f"observation.frames[{index}].window_id: required string"
            )
        current_identity = RuntimeIdentity(
            frame.boot_id,
            frame.generation_id,
            frame.process,
        )
        reason = _identity_change_reason(expected_identity, current_identity)
        if identity_reason is None and reason is not None:
            identity_reason = reason
        by_role[frame.role].append(frame)

    first = by_role["FIRST_FRAME"][0] if len(by_role["FIRST_FRAME"]) == 1 else None
    hold = by_role["HOLD_END"][0] if len(by_role["HOLD_END"]) == 1 else None
    first_frame_seconds = (
        float(first.captured_at_monotonic - launch_time) if first is not None else None
    )
    hold_seconds = 0.0
    same_window = False
    content_visible = False
    if first is not None and hold is not None:
        hold_seconds = max(
            0.0, float(hold.captured_at_monotonic - first.captured_at_monotonic)
        )
        same_window = first.window_id == hold.window_id
        content_visible = (
            first.non_black
            and hold.non_black
            and first.expected_text_visible
            and hold.expected_text_visible
        )

    trace = CandidateTrace(
        preflight_ok=True,
        launch_accepted=True,
        process=observation.process,
        process_alive=observation.process_alive,
        on_resume=observation.on_resume,
        app_window_visible=observation.app_window_visible and same_window,
        present_observed=observation.present_observed and first is not None,
        hello_world_visible=content_visible,
        first_frame_seconds=first_frame_seconds,
        hold_seconds=hold_seconds,
        hold_reason=None if crash is not None else identity_reason,
    )
    return EvaluatedCandidateObservation(trace, observation.frames, crash)


def classify_terminal_state(trace: CandidateTrace) -> str:
    if not trace.preflight_ok:
        return "BLOCK_PRECONDITION"
    if trace.hold_reason in {
        "boot_changed",
        "generation_changed",
        "process_reused",
        "process_changed",
        "process_unexpected",
    }:
        return "INVALIDATED_IDENTITY"
    if not trace.launch_accepted:
        return "FAIL_LAUNCH"
    if trace.process is None:
        return "FAIL_NO_PROCESS"
    if not trace.process_alive:
        return "FAIL_PROCESS_CRASH"
    if not trace.on_resume:
        return "FAIL_LIFECYCLE"
    if (
        not trace.app_window_visible
        or not trace.present_observed
        or trace.first_frame_seconds is None
        or trace.first_frame_seconds > DEFAULT_DEADLINE_SECONDS
    ):
        return "FAIL_PRESENT"
    if not trace.hello_world_visible:
        return "FAIL_WRONG_CONTENT"
    if (
        trace.hold_reason == "process_missing"
        or trace.hold_seconds < DEFAULT_HOLD_SECONDS
    ):
        return "FAIL_UNSTABLE_FRAME"
    return "DEVELOPER_OBSERVED_FIRST_FRAME"


def _launch_success(result: subprocess.CompletedProcess[str]) -> bool:
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    return result.returncode == 0 and re.search(
        r"(?:^|\n)\s*error:|failed to start ability", output, re.IGNORECASE
    ) is None


def run_candidate(
    device: DevicePort,
    expectations: PreflightExpectations,
    *,
    observe: Callable[
        [DevicePort, PreflightExpectations],
        CandidateTrace | CandidateObservation | EvaluatedCandidateObservation,
    ]
    | None = None,
    live_observer: LiveObserver | None = None,
    pre_launch_actions: Mapping[str, str] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> CandidateOutcome:
    """Run one candidate, with a hard no-action barrier around preflight."""
    if observe is not None and live_observer is not None:
        raise contract.ContractError("observe and live_observer are mutually exclusive")
    preflight = collect_preflight(device, expectations)
    if not preflight.ok:
        return CandidateOutcome(
            "BLOCK_PRECONDITION", errors=preflight.errors, preflight=preflight
        )

    for name, command in (pre_launch_actions or {}).items():
        if not isinstance(name, str) or not name.strip():
            raise contract.ContractError("pre_launch_actions: action name required")
        if not isinstance(command, str) or not command.strip():
            raise contract.ContractError(
                f"pre_launch_actions.{name}: non-empty command required"
            )
        try:
            prepared = device.action(name, command)
        except Exception as error:
            return CandidateOutcome(
                "BLOCK_PRECONDITION",
                errors=(
                    f"pre_launch_actions.{name}: action raised "
                    f"{type(error).__name__}: {error}",
                ),
                preflight=preflight,
            )
        if prepared.returncode != 0:
            return CandidateOutcome(
                "BLOCK_PRECONDITION",
                errors=(
                    f"pre_launch_actions.{name}: failed rc={prepared.returncode} "
                    f"stderr={prepared.stderr.strip()!r}",
                ),
                preflight=preflight,
            )

    if live_observer is not None:
        if not callable(getattr(device, "start_stream", None)):
            return CandidateOutcome(
                "BLOCK_PRECONDITION",
                errors=("live_observer: device transport does not support streams",),
                preflight=preflight,
            )
        try:
            live_observer.before_launch(device, expectations)  # type: ignore[arg-type]
        except Exception as error:
            live_observer.close()
            return CandidateOutcome(
                "BLOCK_PRECONDITION",
                errors=(
                    f"live_observer.before_launch: {type(error).__name__}: {error}",
                ),
                preflight=preflight,
            )

    launch_command = (
        "aa start "
        f"-a {expectations.activity_name} "
        f"-b {expectations.package_name} -W"
    )
    launch_started_at_monotonic = monotonic()
    try:
        launch = device.action("launch", launch_command)
    except Exception as error:
        if live_observer is not None:
            live_observer.close()
        trace = CandidateTrace(
            True, False, None, False, False, False, False, False, None, 0.0, None
        )
        return CandidateOutcome(
            "FAIL_LAUNCH",
            errors=(f"launch: action raised {type(error).__name__}: {error}",),
            trace=trace,
            preflight=preflight,
        )
    if not _launch_success(launch):
        if live_observer is not None:
            live_observer.close()
        trace = CandidateTrace(
            True, False, None, False, False, False, False, False, None, 0.0, None
        )
        return CandidateOutcome("FAIL_LAUNCH", trace=trace, preflight=preflight)

    if live_observer is not None:
        try:
            raw_observation = live_observer.after_launch(
                device,  # type: ignore[arg-type]
                expectations,
                launch_started_at_monotonic=launch_started_at_monotonic,
            )
        except Exception as error:
            live_observer.close()
            trace = CandidateTrace(
                True, True, None, False, False, False, False, False, None, 0.0, None
            )
            return CandidateOutcome(
                "FAIL_NO_PROCESS",
                errors=(
                    f"live_observer.after_launch: {type(error).__name__}: {error}",
                ),
                preflight=preflight,
                trace=trace,
            )
        finally:
            live_observer.close()
        if isinstance(raw_observation, CandidateObservation):
            evaluated = evaluate_candidate_observation(raw_observation, expectations)
        elif isinstance(raw_observation, EvaluatedCandidateObservation):
            evaluated = raw_observation
        else:
            raise contract.ContractError(
                "live_observer: required CandidateObservation or EvaluatedCandidateObservation"
            )
        trace = evaluated.trace
    elif observe is None:
        # T009/T010 establish the safe runner boundary and state machine.  T011
        # supplies content/lifecycle observation; absence must remain typed.
        trace = CandidateTrace(
            True, True, None, False, False, False, False, False, None, 0.0, None
        )
        evaluated = EvaluatedCandidateObservation(trace, ())
    else:
        raw_observation = observe(device, expectations)
        if isinstance(raw_observation, CandidateTrace):
            evaluated = EvaluatedCandidateObservation(raw_observation, ())
        elif isinstance(raw_observation, CandidateObservation):
            evaluated = evaluate_candidate_observation(raw_observation, expectations)
        elif isinstance(raw_observation, EvaluatedCandidateObservation):
            evaluated = raw_observation
        else:
            raise contract.ContractError(
                "observe: required CandidateTrace or CandidateObservation"
            )
        trace = evaluated.trace
    terminal = classify_terminal_state(trace)
    return CandidateOutcome(
        terminal,
        preflight=preflight,
        trace=trace,
        crash_evidence=evaluated.crash_evidence,
    )


def _parse_scalar(value: str) -> object:
    raw = value.strip()
    if raw == "":
        return {}
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "~"}:
        return None
    if raw.startswith(("'", '"', "[", "{")):
        try:
            return ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            pass
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return raw


def _load_mapping_yaml_subset(text: str) -> dict[str, object]:
    """Load the mapping-only YAML subset used by the P0 config, stdlib-only."""
    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, root)]
    for number, raw_line in enumerate(text.splitlines(), 1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line[: len(raw_line) - len(raw_line.lstrip())]:
            raise contract.ContractError(f"config line {number}: tabs are forbidden")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        content = raw_line.strip()
        if content.startswith("-"):
            raise contract.ContractError(
                f"config line {number}: block arrays are unsupported; use inline JSON arrays"
            )
        if ":" not in content:
            raise contract.ContractError(f"config line {number}: required key: value")
        key, scalar = content.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", key):
            raise contract.ContractError(f"config line {number}: invalid key {key!r}")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise contract.ContractError(f"config line {number}: invalid indentation")
        parent = stack[-1][1]
        if key in parent:
            raise contract.ContractError(f"config line {number}: duplicate key {key}")
        parsed = _parse_scalar(scalar)
        parent[key] = parsed
        if isinstance(parsed, dict) and scalar.strip() == "":
            stack.append((indent, parsed))
    return root


def load_config(path: Path) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise contract.ContractError(f"config: cannot read {path}: {error}") from error
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = _load_mapping_yaml_subset(text)
    if not isinstance(value, dict):
        raise contract.ContractError("config: required object")
    validate_config(value)
    return value


def _config_mapping(config: Mapping[str, object], field: str) -> Mapping[str, object]:
    value = config.get(field)
    if not isinstance(value, Mapping):
        raise contract.ContractError(f"config.{field}: required object")
    return value


def _one_of(mapping: Mapping[str, object], fields: Sequence[str], label: str) -> object:
    for field in fields:
        if field in mapping:
            return mapping[field]
    raise contract.ContractError(f"{label}: required one of {list(fields)}")


def _finite_config_number(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise contract.ContractError(f"{label}: required finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise contract.ContractError(f"{label}: required finite number") from error
    if not math.isfinite(result):
        raise contract.ContractError(f"{label}: required finite number")
    return result


def config_sample_interval_seconds(config: Mapping[str, object]) -> float:
    oracle = _config_mapping(config, "oracle")
    raw = None
    for field in ("sample_interval_ms", "child_sample_interval_ms"):
        if field in oracle:
            raw = oracle[field]
            break
    if raw is None:
        return DEFAULT_SAMPLE_INTERVAL_SECONDS
    interval_ms = _finite_config_number(raw, "config.oracle.sample_interval_ms")
    if not 50.0 <= interval_ms <= 100.0:
        raise contract.ContractError("config.oracle.sample_interval_ms: required 50-100")
    return interval_ms / 1000.0


def candidate_output_root(
    config: Mapping[str, object], run_id: str, candidate_id: str
) -> Path:
    for label, value in (("run_id", run_id), ("candidate_id", candidate_id)):
        if not isinstance(value, str) or contract.ID_RE.fullmatch(value) is None:
            raise contract.ContractError(f"{label}: invalid stable identifier")
    evidence = _config_mapping(config, "evidence")
    configured_root = _one_of(
        evidence,
        ("output_root", "output_root_project_relative"),
        "config.evidence.output_root",
    )
    if not isinstance(configured_root, str) or not configured_root.strip():
        raise contract.ContractError("config.evidence.output_root: required path")
    base = contract.resolve_project_path(configured_root)
    return contract.resolve_project_path(base / run_id / candidate_id)


def validate_config(config: Mapping[str, object]) -> None:
    schema_version = config.get("schema_version")
    if schema_version not in (1, "bridge.p0.helloworld-first-frame-config.v1") or isinstance(
        schema_version, bool
    ):
        raise contract.ContractError(
            "config.schema_version: required 1 or bridge.p0.helloworld-first-frame-config.v1"
        )
    apk = _config_mapping(config, "apk")
    if _one_of(apk, ("sha256", "expected_sha256"), "config.apk.sha256") != contract.HELLOWORLD_APK_SHA256:
        raise contract.ContractError("config.apk.sha256: wrong frozen APK")
    if _one_of(apk, ("package_name", "package"), "config.apk.package_name") != contract.HELLOWORLD_PACKAGE:
        raise contract.ContractError("config.apk.package_name: wrong package")
    if _one_of(apk, ("activity_name", "activity"), "config.apk.activity_name") != contract.HELLOWORLD_ACTIVITY:
        raise contract.ContractError("config.apk.activity_name: wrong activity")
    if apk.get("unmodified", True) is not True:
        raise contract.ContractError("config.apk.unmodified: required true")
    if "frozen_receipt" in apk:
        receipt_path = contract.resolve_project_path(str(apk["frozen_receipt"]))
        frozen = contract.load_frozen_apk(receipt_path)
        configured_path = contract.resolve_project_path(
            str(_one_of(apk, ("project_relative_path", "path"), "config.apk.path")),
            must_exist=True,
        )
        if Path(str(frozen["resolved_path"])) != configured_path:
            raise contract.ContractError("config.apk.path: does not match frozen receipt")
        if "size_bytes" in apk and apk["size_bytes"] != frozen["size_bytes"]:
            raise contract.ContractError("config.apk.size_bytes: does not match frozen receipt")
    generation = _config_mapping(config, "generation")
    generation_id = _one_of(
        generation, ("generation_id", "current_generation"), "config.generation.generation_id"
    )
    if not isinstance(generation_id, str) or contract.SHA256_RE.fullmatch(generation_id) is None:
        raise contract.ContractError("config.generation.generation_id: required SHA-256")
    if "appspawn_sha256" in generation:
        raise contract.ContractError("config.generation.appspawn_sha256: static value forbidden")
    lease = _config_mapping(config, "lease")
    if "serial" in lease:
        raise contract.ContractError("config.lease.serial: static value forbidden")
    builder = _config_mapping(config, "builder")
    for field in ("ip_address", "password", "private_key", "host_key"):
        if field in builder:
            raise contract.ContractError(f"config.builder.{field}: static value forbidden")
    oracle = _config_mapping(config, "oracle")
    deadline = _finite_config_number(
        _one_of(
            oracle,
            ("deadline_seconds", "first_frame_deadline_seconds", "launch_deadline_seconds"),
            "config.oracle.deadline_seconds",
        ),
        "config.oracle.deadline_seconds",
    )
    hold = _finite_config_number(
        _one_of(oracle, ("hold_seconds",), "config.oracle.hold_seconds"),
        "config.oracle.hold_seconds",
    )
    if deadline != DEFAULT_DEADLINE_SECONDS:
        raise contract.ContractError("config.oracle.deadline_seconds: required 15")
    if hold != DEFAULT_HOLD_SECONDS:
        raise contract.ContractError("config.oracle.hold_seconds: required 5")
    config_sample_interval_seconds(config)
    evidence = _config_mapping(config, "evidence")
    output_root = _one_of(
        evidence,
        ("output_root", "output_root_project_relative"),
        "config.evidence.output_root",
    )
    if not isinstance(output_root, str) or not output_root.strip():
        raise contract.ContractError("config.evidence.output_root: required path")
    contract.resolve_project_path(output_root)
    config_pre_launch_actions(config)


def config_pre_launch_actions(config: Mapping[str, object]) -> dict[str, str]:
    raw = config.get("pre_launch_actions", DEFAULT_PRE_LAUNCH_ACTIONS)
    if not isinstance(raw, Mapping) or not raw:
        raise contract.ContractError("config.pre_launch_actions: required non-empty object")
    actions: dict[str, str] = {}
    for name, command in raw.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", name):
            raise contract.ContractError("config.pre_launch_actions: invalid action name")
        if not isinstance(command, str) or not command.strip():
            raise contract.ContractError(
                f"config.pre_launch_actions.{name}: required non-empty command"
            )
        actions[name] = command.strip()
    return actions


def expectations_from_documents(
    config: Mapping[str, object],
    lease_document: Mapping[str, object],
    device_identity: Mapping[str, object],
    *,
    current_worktree: str,
    writer_terminal: str,
) -> PreflightExpectations:
    validate_config(config)
    lease = LeaseBinding.from_mapping(lease_document)
    identity = contract.validate_device_identity(device_identity)
    apk = _config_mapping(config, "apk")
    generation = _config_mapping(config, "generation")
    generation_id = str(
        _one_of(
            generation,
            ("generation_id", "current_generation"),
            "config.generation.generation_id",
        )
    )
    if identity["serial"] != lease.serial:
        raise contract.ContractError("device_identity.serial: does not match lease")
    if identity["generation_id"] != generation_id:
        raise contract.ContractError("device_identity.generation_id: does not match config")
    commands = dict(DEFAULT_PROBE_COMMANDS)
    configured_commands = config.get("preflight_commands")
    if configured_commands is not None:
        if not isinstance(configured_commands, Mapping):
            raise contract.ContractError("config.preflight_commands: required object")
        for name, command in configured_commands.items():
            if name not in commands or not isinstance(command, str) or not command.strip():
                raise contract.ContractError(f"config.preflight_commands.{name}: invalid probe")
            commands[str(name)] = command
    return PreflightExpectations(
        serial=lease.serial,
        boot_id=str(identity["boot_id"]),
        apk_sha256=str(identity["apk_sha256"]),
        generation_id=generation_id,
        generation_readback_sha256=str(identity["device_readback_sha256"]),
        package_name=str(_one_of(apk, ("package_name", "package"), "config.apk.package_name")),
        activity_name=str(_one_of(apk, ("activity_name", "activity"), "config.apk.activity_name")),
        lease=lease,
        current_worktree=current_worktree,
        writer_terminal=writer_terminal,
        probe_commands=commands,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--lease", type=Path)
    parser.add_argument("--device-identity", type=Path)
    parser.add_argument("--writer-terminal")
    parser.add_argument("--worktree", default=str(contract.PROJECT_ROOT))
    parser.add_argument("--serial")
    parser.add_argument("--run-id")
    parser.add_argument("--candidate-id")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--hdc", default="hdc")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the guarded launch; without this flag validation is host-only",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if not args.apply:
        print(json.dumps({"status": "CONFIG_VALID", "config": str(args.config)}, indent=2))
        return 0

    missing = [
        name
        for name, value in (
            ("--lease", args.lease),
            ("--device-identity", args.device_identity),
            ("--writer-terminal", args.writer_terminal),
            ("--run-id", args.run_id),
            ("--candidate-id", args.candidate_id),
        )
        if value is None
    ]
    if missing:
        raise contract.ContractError(f"apply: missing required arguments {missing}")

    lease_document = contract.load_json_object(args.lease, "lease")
    identity = contract.load_device_identity(args.device_identity)
    expectations = expectations_from_documents(
        config,
        lease_document,
        identity,
        current_worktree=args.worktree,
        writer_terminal=args.writer_terminal,
    )
    if args.serial is not None and args.serial != expectations.serial:
        raise contract.ContractError("--serial does not match HELD lease")
    output_root = candidate_output_root(config, args.run_id, args.candidate_id)
    if args.output_root is not None:
        explicit_root = contract.resolve_project_path(
            args.output_root, project_root=contract.PROJECT_ROOT
        )
        if explicit_root != output_root:
            raise contract.ContractError(
                "--output-root must equal config evidence root/run-id/candidate-id"
            )
    device = HdcDevice(args.hdc, expectations.serial, raw_output_root=output_root)
    observer = LiveBaselineObserver(
        output_root,
        sample_interval_seconds=config_sample_interval_seconds(config),
        deadline_seconds=DEFAULT_DEADLINE_SECONDS,
    )
    outcome = run_candidate(
        device,
        expectations,
        live_observer=observer,
        pre_launch_actions=config_pre_launch_actions(config),
    )
    write_outcome(output_root, outcome)
    print(json.dumps(asdict(outcome), ensure_ascii=False, indent=2, default=str))
    return 0 if outcome.terminal_state == "DEVELOPER_OBSERVED_FIRST_FRAME" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"BLOCK_PRECONDITION: {error}", file=sys.stderr)
        raise SystemExit(2)
