#!/usr/bin/env python3
"""Fail-closed verifier for a D600 HelloWorld first-frame evidence pack.

The verifier is intentionally read-only.  It binds the candidate to the frozen
APK, an expected device/boot/generation (when supplied), the device readback,
the SHA-256 manifest, the process epoch, both screenshot timestamps, the visual
content-review receipt and the developer-only verdict boundary.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageStat

import helloworld_first_frame_contract as contract


DEFAULT_SCHEMA = (
    contract.PROJECT_ROOT
    / "specs/005-helloworld-first-frame/contracts/cold-start-candidate.schema.json"
)
DEFAULT_VERDICT_CONTRACT = (
    contract.PROJECT_ROOT
    / "specs/005-helloworld-first-frame/contracts/verdict-separation.md"
)
EXPECTED_TEXT = "Hello World!"
CONTENT_REVIEW_SCHEMA = "bridge.p0.helloworld-content-review.v1"
CONTENT_REVIEW_DECISION = "EXPECTED_HELLOWORLD_CONTENT_VISIBLE_AND_STABLE"
SUCCESS_TERMINAL = "DEVELOPER_OBSERVED_FIRST_FRAME"
MANIFEST_LINE = re.compile(r"^(?P<sha>[0-9a-f]{64})  (?P<path>.+)$")


@dataclass(frozen=True)
class ExpectedIdentity:
    apk_sha256: str = contract.HELLOWORLD_APK_SHA256
    serial: str | None = None
    boot_id: str | None = None
    generation_id: str | None = None


@dataclass(frozen=True)
class Mismatch:
    path: str
    message: str
    expected: object | None = None
    observed: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        result: dict[str, object | None] = {"path": self.path, "message": self.message}
        if self.expected is not None:
            result["expected"] = self.expected
        if self.observed is not None:
            result["observed"] = self.observed
        return result


@dataclass(frozen=True)
class VerificationResult:
    verdict: str
    terminal_state: str | None
    checks: tuple[str, ...]
    errors: tuple[Mismatch, ...]
    elapsed_seconds: float
    run_root: str
    schema_path: str
    verdict_contract_path: str

    @property
    def accepted(self) -> bool:
        return self.verdict != "REJECTED"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "bridge.p0.helloworld-evidence-verification.v1",
            "verdict": self.verdict,
            "terminal_state": self.terminal_state,
            "checks": list(self.checks),
            "errors": [error.to_dict() for error in self.errors],
            "error_count": len(self.errors),
            "elapsed_seconds": round(self.elapsed_seconds, 6),
            "run_root": self.run_root,
            "schema_path": self.schema_path,
            "verdict_contract_path": self.verdict_contract_path,
            "claim_boundary": contract.DEVELOPER_CLAIM_BOUNDARY,
            "formal_journey_verdict": contract.FORMAL_VERDICT,
        }


@dataclass
class _Collector:
    errors: list[Mismatch] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)

    def error(
        self,
        path: str,
        message: str,
        *,
        expected: object | None = None,
        observed: object | None = None,
    ) -> None:
        mismatch = Mismatch(path, message, expected, observed)
        if mismatch not in self.errors:
            self.errors.append(mismatch)

    def checked(self, name: str) -> None:
        if name not in self.checks:
            self.checks.append(name)

    def equal(self, path: str, observed: object, expected: object) -> None:
        if observed != expected:
            self.error(
                path,
                "identity mismatch",
                expected=expected,
                observed=observed,
            )


def _load_json(path: Path, label: str, collector: _Collector) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        collector.error(label, f"cannot load JSON: {error}")
        return None
    if not isinstance(value, dict):
        collector.error(label, "required JSON object", observed=type(value).__name__)
        return None
    return value


def _json_type_matches(value: object, kind: str) -> bool:
    if kind == "object":
        return isinstance(value, Mapping)
    if kind == "array":
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes))
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "null":
        return value is None
    return False


def _resolve_schema_ref(root_schema: Mapping[str, Any], reference: str) -> Mapping[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError(f"unsupported non-local schema reference: {reference}")
    value: object = root_schema
    for component in reference[2:].split("/"):
        component = component.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, Mapping) or component not in value:
            raise ValueError(f"unresolved schema reference: {reference}")
        value = value[component]
    if not isinstance(value, Mapping):
        raise ValueError(f"schema reference is not an object: {reference}")
    return value


def _validate_schema_node(
    value: object,
    schema: Mapping[str, Any],
    *,
    root_schema: Mapping[str, Any],
    path: str,
    collector: _Collector,
) -> None:
    if "$ref" in schema:
        try:
            target = _resolve_schema_ref(root_schema, str(schema["$ref"]))
        except ValueError as error:
            collector.error(path, str(error))
            return
        _validate_schema_node(
            value, target, root_schema=root_schema, path=path, collector=collector
        )
        return

    if "oneOf" in schema:
        variants = schema["oneOf"]
        matches = 0
        for variant in variants if isinstance(variants, list) else []:
            trial = _Collector()
            _validate_schema_node(
                value, variant, root_schema=root_schema, path=path, collector=trial
            )
            if not trial.errors:
                matches += 1
        if matches != 1:
            collector.error(path, "schema oneOf mismatch", expected="exactly one variant")
        return

    expected_type = schema.get("type")
    if expected_type is not None:
        kinds = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_json_type_matches(value, str(kind)) for kind in kinds):
            collector.error(path, "schema type mismatch", expected=kinds, observed=type(value).__name__)
            return

    if "const" in schema and value != schema["const"]:
        collector.error(path, "schema const mismatch", expected=schema["const"], observed=value)
    if "enum" in schema and value not in schema["enum"]:
        collector.error(path, "schema enum mismatch", expected=schema["enum"], observed=value)

    if isinstance(value, Mapping):
        required = schema.get("required", [])
        if isinstance(required, list):
            for name in required:
                if name not in value:
                    collector.error(f"{path}.{name}", "required field is missing")
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            properties = {}
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in properties:
                    collector.error(f"{path}.{name}", "additional property is forbidden")
        for name, child_schema in properties.items():
            if name in value and isinstance(child_schema, Mapping):
                _validate_schema_node(
                    value[name],
                    child_schema,
                    root_schema=root_schema,
                    path=f"{path}.{name}",
                    collector=collector,
                )

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(value):
                _validate_schema_node(
                    item,
                    item_schema,
                    root_schema=root_schema,
                    path=f"{path}[{index}]",
                    collector=collector,
                )

    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            collector.error(path, "string is shorter than schema minLength")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.fullmatch(pattern, value) is None:
            collector.error(path, "string does not match schema pattern", expected=pattern, observed=value)
        format_name = schema.get("format")
        if format_name == "uuid":
            try:
                uuid.UUID(value)
            except ValueError:
                collector.error(path, "invalid UUID", observed=value)
        elif format_name == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                collector.error(path, "invalid ISO-8601 date-time", observed=value)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and value < minimum:
            collector.error(path, "number is below schema minimum", expected=minimum, observed=value)


def _contract_error(error: contract.ContractError, collector: _Collector) -> None:
    message = str(error)
    prefix, separator, detail = message.partition(":")
    path = prefix if separator and re.fullmatch(r"[A-Za-z0-9_.\[\]-]+", prefix) else "candidate"
    collector.error(path, detail.strip() if separator else message)


def _safe_path(root: Path, value: str, path: str, collector: _Collector) -> Path | None:
    raw = Path(value)
    if raw.is_absolute():
        collector.error(path, "absolute evidence path is forbidden", observed=value)
        return None
    resolved = (root / raw).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        collector.error(path, "evidence path escapes run root", observed=value)
        return None
    return resolved


def _resolve_reference(
    run_root: Path,
    base_dir: Path,
    value: object,
    path: str,
    collector: _Collector,
) -> Path | None:
    if not isinstance(value, str) or not value:
        collector.error(path, "required non-empty reference")
        return None
    reference, separator, expected_sha = value.rpartition("@")
    if not separator or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None:
        reference, expected_sha = value, ""
    raw = Path(reference)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw.resolve())
    else:
        candidates.extend(((base_dir / raw).resolve(), (run_root / raw).resolve(), (contract.PROJECT_ROOT / raw).resolve()))
    chosen = next((candidate for candidate in candidates if candidate.exists()), None)
    if chosen is None:
        collector.error(path, "referenced file does not exist", observed=reference)
        return None
    try:
        chosen.relative_to(contract.PROJECT_ROOT.resolve())
    except ValueError:
        try:
            chosen.relative_to(run_root.resolve())
        except ValueError:
            collector.error(path, "reference escapes project/run root", observed=str(chosen))
            return None
    if expected_sha and chosen.is_file():
        actual = contract.sha256_file(chosen)
        if actual != expected_sha:
            collector.error(f"{path}.sha256", "reference digest mismatch", expected=expected_sha, observed=actual)
    return chosen


def _load_manifest(run_root: Path, collector: _Collector) -> dict[str, str]:
    path = run_root / "evidence-manifest.sha256"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        collector.error("evidence_manifest", f"cannot read manifest: {error}")
        return {}
    entries: dict[str, str] = {}
    for index, line in enumerate(lines, start=1):
        match = MANIFEST_LINE.fullmatch(line)
        if match is None:
            collector.error(f"evidence_manifest.line[{index}]", "invalid sha256sum line", observed=line)
            continue
        relative = match.group("path")
        expected = match.group("sha")
        if relative in entries:
            collector.error(f"evidence_manifest.{relative}", "duplicate manifest path")
            continue
        artifact = _safe_path(run_root, relative, f"evidence_manifest.{relative}.path", collector)
        if artifact is None:
            continue
        if not artifact.is_file():
            collector.error(f"evidence_manifest.{relative}", "manifest artifact is missing")
            entries[relative] = expected
            continue
        actual = contract.sha256_file(artifact)
        if actual != expected:
            collector.error(
                f"evidence_manifest.{relative}.sha256",
                "artifact digest mismatch",
                expected=expected,
                observed=actual,
            )
        entries[relative] = expected
    collector.checked("evidence_manifest")
    return entries


def _screen_map(candidate: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    observations = candidate.get("observations", {})
    screens = observations.get("screens", []) if isinstance(observations, Mapping) else []
    result: dict[str, Mapping[str, Any]] = {}
    for value in screens if isinstance(screens, list) else []:
        if isinstance(value, Mapping) and isinstance(value.get("role"), str):
            result[str(value["role"])] = value
    return result


def _parse_time(value: object, path: str, collector: _Collector) -> datetime | None:
    if not isinstance(value, str):
        collector.error(path, "required ISO-8601 date-time")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        collector.error(path, "invalid ISO-8601 date-time", observed=value)
        return None
    if parsed.tzinfo is None:
        collector.error(path, "date-time must include timezone", observed=value)
        return None
    return parsed


def _validate_timeline(candidate: Mapping[str, Any], collector: _Collector) -> None:
    launch = candidate.get("launch", {})
    observations = candidate.get("observations", {})
    if not isinstance(launch, Mapping) or not isinstance(observations, Mapping):
        return
    launch_time = _parse_time(launch.get("started_at_utc"), "candidate.launch.started_at_utc", collector)
    screens = _screen_map(candidate)
    pre = screens.get("PRECONDITION")
    first = screens.get("FIRST_FRAME")
    hold = screens.get("HOLD_END")
    if candidate.get("terminal_state") == SUCCESS_TERMINAL and pre is None:
        collector.error("candidate.observations.screens[PRECONDITION]", "success requires one precondition screen")
    if launch_time is None or first is None or hold is None:
        return
    first_time = _parse_time(first.get("captured_at_utc"), "candidate.observations.screens[FIRST_FRAME].captured_at_utc", collector)
    hold_time = _parse_time(hold.get("captured_at_utc"), "candidate.observations.screens[HOLD_END].captured_at_utc", collector)
    pre_time = None
    if pre is not None:
        pre_time = _parse_time(pre.get("captured_at_utc"), "candidate.observations.screens[PRECONDITION].captured_at_utc", collector)
    if pre_time is not None and pre_time >= launch_time:
        collector.error("candidate.observations.screens[PRECONDITION].captured_at_utc", "precondition must precede launch")
    if first_time is not None:
        first_delta = (first_time - launch_time).total_seconds()
        if first_delta < 0 or first_delta > 15:
            collector.error(
                "candidate.observations.screens[FIRST_FRAME].captured_at_utc",
                "first-frame timestamp is outside the launch window",
                expected="0..15 seconds after launch",
                observed=first_delta,
            )
        declared = observations.get("first_frame_seconds")
        if isinstance(declared, (int, float)) and abs(float(declared) - first_delta) > 1.0:
            collector.error("candidate.observations.first_frame_seconds", "declared/UTC first-frame delta mismatch", expected=first_delta, observed=declared)
    if first_time is not None and hold_time is not None:
        hold_delta = (hold_time - first_time).total_seconds()
        if hold_delta < 5:
            collector.error(
                "candidate.observations.screens[HOLD_END].captured_at_utc",
                "hold timestamp is less than five seconds after first frame",
                expected=">=5",
                observed=hold_delta,
            )
        declared = observations.get("hold_seconds")
        if isinstance(declared, (int, float)) and abs(float(declared) - hold_delta) > 1.0:
            collector.error("candidate.observations.hold_seconds", "declared/UTC hold delta mismatch", expected=hold_delta, observed=declared)
    collector.checked("screenshot_timeline")


def _validate_screen_files(
    run_root: Path,
    candidate: Mapping[str, Any],
    manifest: Mapping[str, str],
    collector: _Collector,
) -> None:
    for role, screen in _screen_map(candidate).items():
        relative = screen.get("path")
        if not isinstance(relative, str):
            continue
        path_label = f"candidate.observations.screens[{role}]"
        artifact = _safe_path(run_root, relative, f"{path_label}.path", collector)
        if artifact is None or not artifact.is_file():
            collector.error(f"{path_label}.path", "screenshot file is missing", observed=relative)
            continue
        actual = contract.sha256_file(artifact)
        collector.equal(f"{path_label}.sha256", screen.get("sha256"), actual)
        if relative not in manifest:
            collector.error(f"{path_label}.path", "screenshot is absent from evidence manifest", observed=relative)
        elif manifest[relative] != actual:
            collector.error(f"{path_label}.sha256", "screenshot/manifest digest mismatch", expected=manifest[relative], observed=actual)
        try:
            with Image.open(artifact) as image:
                luminance = image.convert("L")
                histogram = luminance.histogram()
                total = sum(histogram)
                nonblack = sum(histogram[4:])
                extrema = luminance.getextrema()
                ratio = nonblack / total if total else 0.0
                span = extrema[1] - extrema[0] if extrema else 0
                _ = ImageStat.Stat(luminance).mean[0]
        except Exception as error:  # Pillow exposes format-specific exception classes.
            collector.error(f"{path_label}.path", f"cannot decode screenshot: {error}")
            continue
        if role in {"FIRST_FRAME", "HOLD_END"}:
            if ratio < 0.01:
                collector.error(f"{path_label}.pixels", "screenshot is effectively black", observed=ratio)
            if span < 12:
                collector.error(f"{path_label}.pixels", "screenshot is effectively flat", observed=span)
    collector.checked("screenshot_files")


def _parse_proc_stat(path: Path, label: str, collector: _Collector) -> tuple[int, int, int] | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
        left = text.index("(")
        right = text.rindex(")")
        pid = int(text[:left].strip())
        fields = text[right + 1 :].strip().split()
        ppid = int(fields[1])
        start_ticks = int(fields[19])
    except (OSError, UnicodeError, ValueError, IndexError) as error:
        collector.error(label, f"cannot parse /proc stat: {error}")
        return None
    return pid, ppid, start_ticks


def _validate_process_epoch(
    run_root: Path,
    candidate: Mapping[str, Any],
    manifest: Mapping[str, str],
    collector: _Collector,
) -> None:
    if candidate.get("terminal_state") != SUCCESS_TERMINAL:
        return
    process = candidate.get("process", {})
    if not isinstance(process, Mapping):
        return
    first_screen = _screen_map(candidate).get("FIRST_FRAME")
    if first_screen is None or not isinstance(first_screen.get("path"), str):
        return
    raw_dir = (run_root / str(first_screen["path"])).resolve().parent
    snapshots = (
        (raw_dir / "first-frame-proc-stat.txt", "FIRST_FRAME"),
        (raw_dir / "hold-end-proc-stat.txt", "HOLD_END"),
    )
    expected = (
        process.get("pid"),
        process.get("parent_pid"),
        process.get("start_ticks"),
    )
    for path, role in snapshots:
        relative = path.relative_to(run_root.resolve()).as_posix()
        observed = _parse_proc_stat(path, f"candidate.process.{role}.proc_stat", collector)
        if observed is not None and observed != expected:
            names = ("pid", "parent_pid", "start_ticks")
            for name, actual, wanted in zip(names, observed, expected):
                if actual != wanted:
                    collector.error(f"candidate.process.{name}", f"{role} /proc identity mismatch", expected=wanted, observed=actual)
        if relative not in manifest:
            collector.error(f"candidate.process.{role}.proc_stat", "process snapshot is absent from evidence manifest")
    preexisting = raw_dir / "pre-existing-processes.txt"
    try:
        old = preexisting.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        collector.error("candidate.launch.cold_precondition", f"cannot read pre-existing process receipt: {error}")
    else:
        if old:
            collector.error("candidate.launch.cold_precondition", "pre-existing HelloWorld process was recorded", observed=old)
        relative = preexisting.relative_to(run_root.resolve()).as_posix()
        if relative not in manifest:
            collector.error("candidate.launch.cold_precondition", "pre-existing process receipt is absent from manifest")
    collector.checked("process_epoch")


def _validate_device_generation(
    run_root: Path,
    candidate_path: Path,
    candidate: Mapping[str, Any],
    expectations: ExpectedIdentity,
    manifest: Mapping[str, str],
    collector: _Collector,
) -> None:
    device = candidate.get("device", {})
    generation = candidate.get("generation", {})
    apk = candidate.get("apk", {})
    if not all(isinstance(value, Mapping) for value in (device, generation, apk)):
        return
    collector.equal("candidate.apk.sha256", apk.get("sha256"), expectations.apk_sha256)
    for path, observed, expected in (
        ("candidate.device.serial", device.get("serial"), expectations.serial),
        ("candidate.device.boot_id", device.get("boot_id"), expectations.boot_id),
        ("candidate.generation.generation_id", generation.get("generation_id"), expectations.generation_id),
    ):
        if expected is not None:
            collector.equal(path, observed, expected)

    receipt_path = _resolve_reference(
        run_root,
        candidate_path.parent,
        generation.get("device_readback_receipt"),
        "candidate.generation.device_readback_receipt",
        collector,
    )
    if receipt_path is None:
        return
    receipt = _load_json(receipt_path, "device_generation", collector)
    if receipt is None:
        return
    try:
        contract.validate_device_identity(receipt)
    except contract.ContractError as error:
        message = str(error)
        prefix, _, detail = message.partition(":")
        collector.error(prefix or "device_generation", detail.strip() or message)
    for path, observed, expected in (
        ("device_generation.serial", receipt.get("serial"), device.get("serial")),
        ("device_generation.boot_id", receipt.get("boot_id"), device.get("boot_id")),
        ("device_generation.generation_id", receipt.get("generation_id"), generation.get("generation_id")),
        ("device_generation.apk_sha256", receipt.get("apk_sha256"), apk.get("sha256")),
        ("device_generation.oh_version", receipt.get("oh_version"), device.get("oh_version")),
        ("device_generation.selinux", receipt.get("selinux"), device.get("selinux")),
    ):
        collector.equal(path, observed, expected)
    process = candidate.get("process", {})
    parent = receipt.get("appspawn_parent", {})
    if isinstance(process, Mapping) and isinstance(parent, Mapping) and process.get("parent_pid") is not None:
        collector.equal("device_generation.appspawn_parent.pid", parent.get("pid"), process.get("parent_pid"))
    artifacts = receipt.get("artifacts", {})
    if isinstance(artifacts, Mapping):
        if "installed_apk" in artifacts:
            installed = artifacts["installed_apk"]
            if isinstance(installed, Mapping):
                collector.equal("device_generation.artifacts.installed_apk.sha256", installed.get("sha256"), apk.get("sha256"))
            else:
                collector.error("device_generation.artifacts.installed_apk", "required artifact object when supplied")
        child_maps = artifacts.get("child_maps")
        if isinstance(child_maps, Mapping) and isinstance(child_maps.get("path"), str):
            relative = str(child_maps["path"])
            artifact = _safe_path(run_root, relative, "device_generation.artifacts.child_maps.path", collector)
            if artifact is not None and artifact.is_file():
                actual = contract.sha256_file(artifact)
                collector.equal("device_generation.artifacts.child_maps.sha256", child_maps.get("sha256"), actual)
                if relative not in manifest:
                    collector.error("device_generation.artifacts.child_maps.path", "child maps are absent from evidence manifest")
    collector.checked("device_generation")


def _validate_content_review(
    run_root: Path,
    candidate_path: Path,
    candidate: Mapping[str, Any],
    collector: _Collector,
) -> None:
    if candidate.get("terminal_state") != SUCCESS_TERMINAL:
        return
    review_path = run_root / "candidate/content-review.json"
    review = _load_json(review_path, "content_review", collector)
    if review is None:
        return
    collector.equal("content_review.schema_version", review.get("schema_version"), CONTENT_REVIEW_SCHEMA)
    reference = _resolve_reference(run_root, review_path.parent, review.get("candidate_ref"), "content_review.candidate_ref", collector)
    if reference is not None and reference.resolve() != candidate_path.resolve():
        collector.error("content_review.candidate_ref", "content review refers to another candidate", expected=str(candidate_path), observed=str(reference))
    screens = _screen_map(candidate)
    first_screen = screens.get("FIRST_FRAME", {})
    hold_screen = screens.get("HOLD_END", {})
    pre_screen = screens.get("PRECONDITION", {})
    pre = review.get("precondition", {})
    first = review.get("first_frame", {})
    hold = review.get("hold_end", {})
    if not isinstance(pre, Mapping):
        collector.error("content_review.precondition", "required object")
        pre = {}
    if not isinstance(first, Mapping):
        collector.error("content_review.first_frame", "required object")
        first = {}
    if not isinstance(hold, Mapping):
        collector.error("content_review.hold_end", "required object")
        hold = {}
    collector.equal("content_review.precondition.sha256", pre.get("sha256"), pre_screen.get("sha256"))
    collector.equal("content_review.precondition.old_process_count", pre.get("old_process_count"), 0)
    collector.equal("content_review.first_frame.sha256", first.get("sha256"), first_screen.get("sha256"))
    collector.equal("content_review.hold_end.sha256", hold.get("sha256"), hold_screen.get("sha256"))
    visible = first.get("visible_text")
    if not isinstance(visible, list) or not any(
        isinstance(text, str) and EXPECTED_TEXT in text for text in visible
    ):
        collector.error("content_review.first_frame.visible_text", "expected HelloWorld text is absent", expected=EXPECTED_TEXT, observed=visible)
    collector.equal("content_review.hold_end.expected_text_still_visible", hold.get("expected_text_still_visible"), True)
    hold_seconds = hold.get("seconds_after_first_frame")
    if not isinstance(hold_seconds, (int, float)) or isinstance(hold_seconds, bool) or hold_seconds < 5:
        collector.error("content_review.hold_end.seconds_after_first_frame", "content review hold is less than five seconds", expected=">=5", observed=hold_seconds)
    same_process = hold.get("same_process", {})
    process = candidate.get("process", {})
    if isinstance(same_process, Mapping) and isinstance(process, Mapping):
        for name in ("pid", "start_ticks", "parent_pid"):
            collector.equal(f"content_review.hold_end.same_process.{name}", same_process.get(name), process.get(name))
    else:
        collector.error("content_review.hold_end.same_process", "required process identity object")
    same_pixels = first_screen.get("sha256") == hold_screen.get("sha256")
    collector.equal("content_review.hold_end.same_pixels_sha256", hold.get("same_pixels_sha256"), same_pixels)
    collector.equal("content_review.decision", review.get("decision"), CONTENT_REVIEW_DECISION)
    collector.equal("content_review.claim_boundary", review.get("claim_boundary"), contract.DEVELOPER_CLAIM_BOUNDARY)
    collector.equal("content_review.formal_journey_verdict", review.get("formal_journey_verdict"), contract.FORMAL_VERDICT)
    collector.checked("content_review")


def _validate_verdict_contract(
    path: Path, collector: _Collector
) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        collector.error("verdict_contract", f"cannot read verdict separation contract: {error}")
        return
    for token in (
        SUCCESS_TERMINAL,
        contract.DEVELOPER_CLAIM_BOUNDARY,
        contract.FORMAL_VERDICT,
    ):
        if token not in text:
            collector.error("verdict_contract", "required verdict token is absent", expected=token)
    collector.checked("verdict_separation_contract")


def _validate_developer_verdict(
    run_root: Path,
    candidate_path: Path,
    candidate: Mapping[str, Any],
    collector: _Collector,
) -> None:
    path = run_root / "DEVELOPER-VERDICT.json"
    verdict = _load_json(path, "developer_verdict", collector)
    if verdict is None:
        return
    try:
        contract.validate_developer_verdict(verdict, candidate)
    except contract.ContractError as error:
        message = str(error)
        prefix, separator, detail = message.partition(":")
        collector.error(prefix if separator else "developer_verdict", detail.strip() if separator else message)
    reference = _resolve_reference(run_root, path.parent, verdict.get("candidate_ref"), "developer_verdict.candidate_ref", collector)
    if reference is not None and reference.resolve() != candidate_path.resolve():
        collector.error("developer_verdict.candidate_ref", "verdict refers to another candidate", expected=str(candidate_path), observed=str(reference))
    collector.equal("developer_verdict.first_bad", verdict.get("first_bad"), candidate.get("first_bad"))
    collector.checked("developer_verdict")


def verify_evidence_pack(
    run_root: Path,
    *,
    expectations: ExpectedIdentity | None = None,
    schema_path: Path = DEFAULT_SCHEMA,
    verdict_contract_path: Path = DEFAULT_VERDICT_CONTRACT,
) -> VerificationResult:
    started = time.monotonic()
    collector = _Collector()
    root = run_root.resolve()
    expected = expectations or ExpectedIdentity()
    candidate_path = root / "candidate/candidate.json"
    candidate = _load_json(candidate_path, "candidate", collector)
    schema = _load_json(schema_path, "candidate_schema", collector)
    _validate_verdict_contract(verdict_contract_path, collector)
    manifest = _load_manifest(root, collector)
    terminal_state: str | None = None

    if candidate is not None:
        terminal = candidate.get("terminal_state")
        terminal_state = terminal if isinstance(terminal, str) else None
        manifest_path = root / "evidence-manifest.sha256"
        if manifest_path.is_file():
            collector.equal(
                "candidate.evidence_manifest_sha256",
                candidate.get("evidence_manifest_sha256"),
                contract.sha256_file(manifest_path),
            )
        if schema is not None:
            _validate_schema_node(
                candidate,
                schema,
                root_schema=schema,
                path="candidate",
                collector=collector,
            )
            collector.checked("cold_start_candidate_schema")
        try:
            contract.validate_candidate(candidate)
        except contract.ContractError as error:
            _contract_error(error, collector)
        else:
            collector.checked("candidate_semantic_contract")
        _validate_device_generation(root, candidate_path, candidate, expected, manifest, collector)
        _validate_timeline(candidate, collector)
        _validate_screen_files(root, candidate, manifest, collector)
        _validate_process_epoch(root, candidate, manifest, collector)
        _validate_content_review(root, candidate_path, candidate, collector)
        _validate_developer_verdict(root, candidate_path, candidate, collector)

    if collector.errors:
        verdict = "REJECTED"
    elif terminal_state == SUCCESS_TERMINAL:
        verdict = "ACCEPTED_DEVELOPER_OBSERVATION"
    elif terminal_state and terminal_state.startswith(("FAIL_", "BLOCK_")):
        verdict = "ACCEPTED_TYPED_FAILURE"
    elif terminal_state == "INVALIDATED_IDENTITY":
        verdict = "ACCEPTED_INVALIDATION"
    else:
        collector.error("candidate.terminal_state", "pack has no acceptable typed terminal state", observed=terminal_state)
        verdict = "REJECTED"

    return VerificationResult(
        verdict=verdict,
        terminal_state=terminal_state,
        checks=tuple(collector.checks),
        errors=tuple(collector.errors),
        elapsed_seconds=time.monotonic() - started,
        run_root=str(root),
        schema_path=str(schema_path.resolve()),
        verdict_contract_path=str(verdict_contract_path.resolve()),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--verdict-contract", type=Path, default=DEFAULT_VERDICT_CONTRACT)
    parser.add_argument("--expected-apk-sha256", default=contract.HELLOWORLD_APK_SHA256)
    parser.add_argument("--expected-serial")
    parser.add_argument("--expected-boot-id")
    parser.add_argument("--expected-generation-id")
    parser.add_argument(
        "--expect",
        choices=(
            "ACCEPTED_DEVELOPER_OBSERVATION",
            "ACCEPTED_TYPED_FAILURE",
            "ACCEPTED_INVALIDATION",
            "REJECTED",
        ),
        default="ACCEPTED_DEVELOPER_OBSERVATION",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = verify_evidence_pack(
        args.run_root,
        expectations=ExpectedIdentity(
            apk_sha256=args.expected_apk_sha256,
            serial=args.expected_serial,
            boot_id=args.expected_boot_id,
            generation_id=args.expected_generation_id,
        ),
        schema_path=args.schema,
        verdict_contract_path=args.verdict_contract,
    )
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"verdict={result.verdict} terminal_state={result.terminal_state} errors={len(result.errors)} elapsed_seconds={result.elapsed_seconds:.6f}")
        for error in result.errors:
            print(f"MISMATCH {error.path}: {error.message}; expected={error.expected!r}; observed={error.observed!r}")
    return 0 if result.verdict == args.expect else 1


if __name__ == "__main__":
    raise SystemExit(main())
