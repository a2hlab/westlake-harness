#!/usr/bin/env python3
"""Verify canonical demo inputs and fail-closed Journey oracle wiring."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
LEGACY_MARKER = "src/AlexBridge"
EXPECTED_ROOTS = {
    "adapter": "/opt/Bridge/src/adapter",
    "android": "/opt/Bridge/src/upstream/aosp-14",
    "openharmony": "/opt/Bridge/src/upstream/openharmony-6.1.0.31",
}
EXPECTED_INPUTS = {
    "HelloWorld": (
        "imports/demo-inputs/G1-helloworld/HelloWorld.apk",
        "2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd",
    ),
    "G6.U00": (
        "imports/unity-games/G6-atomladder-2022.3.62f2/Build/Android-repro/"
        "AtomLadder-U00-ColorFrame-arm64.apk",
        "08c843037ba18a4e696f9807af8f51c867f5eba5f68d4c41532c18a4594dbef9",
    ),
    "G6.U01": (
        "imports/unity-games/G6-atomladder-2022.3.62f2/Build/Android-repro/"
        "AtomLadder-U01-HelloUnity-arm64.apk",
        "ec0808a071381c445a3b90f3899c65a276089232e1e9097a50e057189edf9c83",
    ),
    "G7.APK": (
        "imports/unity-games/G7-slidingpuzzle-2023.2.8f1/apk/Android_1.0.1.apk",
        "f283d691ae6532200f6729467884ee477f8c3219dc2f05ba59e88d40ca815798",
    ),
}
J02_PATH = "docs/spec/journeys/J02-unity-game-running/journey.yaml"
J02_SUBJECT_TO_ARTIFACT = {
    "G6.U00": "G6.U00",
    "G6.U01": "G6.U01",
    "G7": "G7.APK",
}
J02_MEASUREMENT_METHODS = {
    "DISPLAY_RGBA_CAPTURE",
    "APP_WINDOW_RECT",
    "SRGB_COLOR_MATCH",
    "CASE_SENSITIVE_OCR",
    "PROCESS_GENERATION",
    "SURFACE_GENERATION",
    "OH_PRESENT_TIMESTAMP",
    "G7_GRID_STATE",
    "INPUT_CAUSALITY",
}
J02_METHOD_APPLICABILITY = {
    "DISPLAY_RGBA_CAPTURE": {"G6.U00", "G6.U01", "G7"},
    "APP_WINDOW_RECT": {"G6.U00", "G6.U01", "G7"},
    "SRGB_COLOR_MATCH": {"G6.U00", "G6.U01"},
    "CASE_SENSITIVE_OCR": {"G6.U01", "G7"},
    "PROCESS_GENERATION": {"G6.U00", "G6.U01", "G7"},
    "SURFACE_GENERATION": {"G6.U00", "G6.U01", "G7"},
    "OH_PRESENT_TIMESTAMP": {"G6.U00", "G6.U01", "G7"},
    "G7_GRID_STATE": {"G7"},
    "INPUT_CAUSALITY": {"G7"},
}
J02_ANCHORS = {
    "G6.U00": {"U00-COLOR"},
    "G6.U01": {"U01-BACKGROUND", "U01-TEXT"},
    "G7": {"G7-MAIN-MENU", "G7-NUMBER-BOARD"},
}
J02_ANCHOR_METHODS = {
    "U00-COLOR": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "SRGB_COLOR_MATCH",
    },
    "U01-BACKGROUND": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "SRGB_COLOR_MATCH",
    },
    "U01-TEXT": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "CASE_SENSITIVE_OCR",
    },
    "G7-MAIN-MENU": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "CASE_SENSITIVE_OCR",
    },
    "G7-NUMBER-BOARD": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "CASE_SENSITIVE_OCR",
        "G7_GRID_STATE",
    },
}
J02_SOURCE_ANCHORS = {
    "U00-COLOR": (
        "imports/unity-games/G6-atomladder-2022.3.62f2/"
        "Assets/AtomLadder/Editor/AtomLadderBuilder.cs"
    ),
    "U01-BACKGROUND": (
        "imports/unity-games/G6-atomladder-2022.3.62f2/"
        "Assets/AtomLadder/Editor/AtomLadderBuilder.cs"
    ),
    "U01-TEXT": (
        "imports/unity-games/G6-atomladder-2022.3.62f2/"
        "Assets/AtomLadder/Runtime/AtomHelloProbe.cs"
    ),
}
J02_MENU_TEXT = (
    "Sliding Puzzle Game",
    "Instructions",
    "2x2",
    "3x3",
    "4x4",
    "5x5",
    "6x6",
    "7x7",
    "8x8",
    "9x9",
    "Image",
)
J02_SCREENSHOTS = {
    "G7-MAIN-MENU": (
        "imports/unity-games/G7-slidingpuzzle-2023.2.8f1/"
        "src/resources/screenshots/screenshot_1.png",
        "11f50a7b41d8b1be070f87b840f2768194b07b1eae58430dffbbfa391a382b0f",
    ),
    "G7-NUMBER-BOARD": (
        "imports/unity-games/G7-slidingpuzzle-2023.2.8f1/"
        "src/resources/screenshots/screenshot_3.png",
        "e29f204154bd3d92e060c295e98e5db8dc1b8755ccd759cff44c81b13cfce579",
    ),
}
J02_CASES = {
    "positive": {
        "P-G6-U00": {"G6.U00"},
        "P-G6-U01": {"G6.U01"},
        "P-G7-PLAY": {"G7"},
        "P-G7-LIFECYCLE": {"G7"},
    },
    "negative": {
        "N-NON-APK-PIXELS": {"G6.U00", "G6.U01", "G7"},
        "N-STALE-OR-STATIC": {"G6.U00", "G6.U01", "G7"},
        "N-DIAGNOSTIC-INHERITANCE": {"G7"},
        "N-WRONG-INTERACTION": {"G7"},
        "N-LIFECYCLE-SUBSTITUTION": {"G6.U00", "G6.U01", "G7"},
    },
    "failure": {
        "F-IDENTITY": {"G6.U00", "G6.U01", "G7"},
        "F-LAUNCH": {"G6.U00", "G6.U01", "G7"},
        "F-RENDER": {"G6.U00", "G6.U01", "G7"},
        "F-EVIDENCE-GAP": {"G6.U00", "G6.U01", "G7"},
    },
}
J02_CASE_METHODS = {
    "P-G6-U00": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "SRGB_COLOR_MATCH",
        "PROCESS_GENERATION",
        "SURFACE_GENERATION",
        "OH_PRESENT_TIMESTAMP",
    },
    "P-G6-U01": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "SRGB_COLOR_MATCH",
        "CASE_SENSITIVE_OCR",
        "PROCESS_GENERATION",
        "SURFACE_GENERATION",
        "OH_PRESENT_TIMESTAMP",
    },
    "P-G7-PLAY": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "CASE_SENSITIVE_OCR",
        "PROCESS_GENERATION",
        "SURFACE_GENERATION",
        "OH_PRESENT_TIMESTAMP",
        "G7_GRID_STATE",
        "INPUT_CAUSALITY",
    },
    "P-G7-LIFECYCLE": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "CASE_SENSITIVE_OCR",
        "PROCESS_GENERATION",
        "SURFACE_GENERATION",
        "OH_PRESENT_TIMESTAMP",
        "G7_GRID_STATE",
        "INPUT_CAUSALITY",
    },
    "N-NON-APK-PIXELS": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "SRGB_COLOR_MATCH",
        "CASE_SENSITIVE_OCR",
        "PROCESS_GENERATION",
        "SURFACE_GENERATION",
    },
    "N-STALE-OR-STATIC": {
        "DISPLAY_RGBA_CAPTURE",
        "PROCESS_GENERATION",
        "SURFACE_GENERATION",
        "OH_PRESENT_TIMESTAMP",
    },
    "N-DIAGNOSTIC-INHERITANCE": {
        "DISPLAY_RGBA_CAPTURE",
        "APP_WINDOW_RECT",
        "CASE_SENSITIVE_OCR",
        "PROCESS_GENERATION",
        "SURFACE_GENERATION",
    },
    "N-WRONG-INTERACTION": {
        "DISPLAY_RGBA_CAPTURE",
        "G7_GRID_STATE",
        "INPUT_CAUSALITY",
    },
    "N-LIFECYCLE-SUBSTITUTION": {
        "PROCESS_GENERATION",
        "SURFACE_GENERATION",
        "OH_PRESENT_TIMESTAMP",
    },
    "F-IDENTITY": {"PROCESS_GENERATION", "SURFACE_GENERATION"},
    "F-LAUNCH": {"PROCESS_GENERATION", "APP_WINDOW_RECT"},
    "F-RENDER": {
        "DISPLAY_RGBA_CAPTURE",
        "SURFACE_GENERATION",
        "OH_PRESENT_TIMESTAMP",
    },
    "F-EVIDENCE-GAP": set(J02_MEASUREMENT_METHODS),
}


def load_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: YAML root must be a mapping")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mapping(value: object, location: str, failures: list[str]) -> dict:
    if not isinstance(value, dict):
        failures.append(f"J02 {location}: must be a mapping")
        return {}
    return value


def _list(value: object, location: str, failures: list[str]) -> list:
    if not isinstance(value, list):
        failures.append(f"J02 {location}: must be a list")
        return []
    return value


def _validate_method_references(
    value: object, location: str, failures: list[str]
) -> None:
    methods = _list(value, location, failures)
    if not methods:
        failures.append(f"J02 {location}: must not be empty")
        return
    if len(methods) != len(set(methods)):
        failures.append(f"J02 {location}: duplicate method reference")
    unknown = set(methods) - J02_MEASUREMENT_METHODS
    if unknown:
        failures.append(f"J02 {location}: unknown methods {sorted(unknown)}")


def _validate_source_reference(
    root: Path,
    anchor_id: str,
    reference: object,
    failures: list[str],
) -> None:
    ref = _mapping(reference, f"anchor {anchor_id}.source_reference", failures)
    expected_path, expected_sha = J02_SCREENSHOTS[anchor_id]
    if ref.get("path") != expected_path:
        failures.append(f"J02 anchor {anchor_id}: source path drifted")
        return
    if ref.get("sha256") != expected_sha:
        failures.append(f"J02 anchor {anchor_id}: source SHA-256 drifted")
        return
    path = root / expected_path
    if not path.is_file() or path.is_symlink():
        failures.append(f"J02 anchor {anchor_id}: source reference missing")
    elif sha256(path) != expected_sha:
        failures.append(f"J02 anchor {anchor_id}: source payload drifted")


def validate_j02(root: Path, journey: dict, unity: dict) -> list[str]:
    """Return all J02 contract failures; an empty list is the only PASS."""
    failures: list[str] = []
    if journey.get("schema_version") != "1.1":
        failures.append("J02 schema_version must be 1.1")
    if journey.get("status") != "VERIFICATION_CONTRACT_FROZEN":
        failures.append("J02 status must remain VERIFICATION_CONTRACT_FROZEN")
    if (
        unity.get("execution_policy", {}).get("journey_oracle")
        != J02_PATH
    ):
        failures.append("J02 is not the ladder journey_oracle")

    artifacts = {
        artifact.get("id"): artifact
        for goal in unity.get("goals", [])
        for artifact in goal.get("artifacts", [])
        if isinstance(artifact, dict)
    }
    identities = _mapping(
        journey.get("identity_contract", {}).get("immutable_inputs"),
        "identity_contract.immutable_inputs",
        failures,
    )
    if set(identities) != set(J02_SUBJECT_TO_ARTIFACT):
        failures.append("J02 immutable subject set drifted")
    for subject, artifact_id in J02_SUBJECT_TO_ARTIFACT.items():
        identity = _mapping(
            identities.get(subject), f"identity {subject}", failures
        )
        artifact = artifacts.get(artifact_id, {})
        expected_path, expected_sha = EXPECTED_INPUTS[artifact_id]
        if identity.get("apk_path") != expected_path:
            failures.append(f"J02 {subject}: APK path drifted")
        if identity.get("apk_sha256") != expected_sha:
            failures.append(f"J02 {subject}: APK SHA-256 drifted")
        if identity.get("package_name") != artifact.get("package_name"):
            failures.append(f"J02 {subject}: package differs from ladder")
        if artifact.get("journey_oracle_subject") != subject:
            failures.append(f"J02 {subject}: ladder subject wiring drifted")

    methods = _mapping(
        journey.get("measurement_methods"), "measurement_methods", failures
    )
    if set(methods) != J02_MEASUREMENT_METHODS:
        failures.append(
            "J02 measurement method set drifted: "
            f"{sorted(set(methods))} != {sorted(J02_MEASUREMENT_METHODS)}"
        )
    for method_id in J02_MEASUREMENT_METHODS:
        method = _mapping(
            methods.get(method_id), f"measurement {method_id}", failures
        )
        if not isinstance(method.get("kind"), str) or not method.get("kind"):
            failures.append(f"J02 measurement {method_id}: missing kind")
        applicable_subjects = _list(
            method.get("applicable_subjects"),
            f"measurement {method_id}.applicable_subjects",
            failures,
        )
        if set(applicable_subjects) != J02_METHOD_APPLICABILITY[method_id]:
            failures.append(
                f"J02 measurement {method_id}: applicable_subjects drifted"
            )
        receipts = _list(
            method.get("required_receipt_fields"),
            f"measurement {method_id}.required_receipt_fields",
            failures,
        )
        if not receipts or any(not isinstance(item, str) for item in receipts):
            failures.append(
                f"J02 measurement {method_id}: invalid receipt fields"
            )
        if len(receipts) != len(set(receipts)):
            failures.append(
                f"J02 measurement {method_id}: duplicate receipt field"
            )
        if method.get("failure_case") != "F-EVIDENCE-GAP":
            failures.append(
                f"J02 measurement {method_id}: must fail to F-EVIDENCE-GAP"
            )
        if method.get("generic_hilog_accepted") is not False:
            failures.append(
                f"J02 measurement {method_id}: generic hilog must be false"
            )
        source_text = json.dumps(
            method.get("source", {}), sort_keys=True
        ).lower()
        if "hilog" in source_text:
            failures.append(
                f"J02 measurement {method_id}: generic hilog source forbidden"
            )

    display = methods.get("DISPLAY_RGBA_CAPTURE", {}).get("source", {})
    if "snapshot_display" not in display.get("device_command_argv", []):
        failures.append("J02 pixel capture must use snapshot_display")
    if (
        display.get("required_format") != "PNG"
        or display.get("decoded_pixel_format") != "RGBA8"
        or display.get("color_space") != "sRGB"
    ):
        failures.append("J02 pixel capture format must be PNG/RGBA8/sRGB")

    window = methods.get("APP_WINDOW_RECT", {}).get("source", {})
    window_argv = window.get("command_argv", [])
    if not {"hidumper", "WindowManagerService", "-w"}.issubset(
        set(window_argv)
    ):
        failures.append("J02 window crop must use WMS hidumper -w")

    color = methods.get("SRGB_COLOR_MATCH", {}).get("algorithm", {})
    if (
        color.get("per_channel_absolute_tolerance_8bit") != 8
        or color.get("minimum_matching_pixel_fraction") != 0.98
        or color.get("interior_inset_fraction_each_edge") != 0.05
    ):
        failures.append("J02 sRGB tolerance/inset/fraction drifted")

    ocr = methods.get("CASE_SENSITIVE_OCR", {})
    matching = ocr.get("matching", {})
    ocr_source = ocr.get("source", {})
    if (
        ocr_source.get("engine") != "tesseract"
        or ocr_source.get("engine_version_and_model_sha256_required") is not True
        or matching.get("unicode_normalization") != "NFC"
        or matching.get("case_sensitive") is not True
        or matching.get("expected_string_rule")
        != "exact_line_or_exact_button_token"
    ):
        failures.append("J02 OCR engine/case/exact-match contract drifted")

    process = methods.get("PROCESS_GENERATION", {}).get("source", {})
    if (
        process.get("starttime_source")
        != "/proc/${process_id}/stat field 22"
    ):
        failures.append("J02 process generation lacks proc stat field 22")

    surface = methods.get("SURFACE_GENERATION", {}).get("source", {})
    accessors = set(surface.get("exact_oh_accessors", []))
    if accessors != {"RSSurfaceNode::GetId()", "Surface::GetUniqueId()"}:
        failures.append("J02 Surface generation OH accessors drifted")
    for locator in surface.get("source_locators", []):
        if not (root / locator).is_file():
            failures.append(
                f"J02 Surface generation source locator missing: {locator}"
            )
    surface_tuple = set(surface.get("generation_tuple", []))
    if not {
        "process_id",
        "proc_stat_starttime_ticks",
        "persistent_window_id",
        "rs_node_id",
        "surface_unique_id",
    }.issubset(surface_tuple):
        failures.append("J02 Surface generation tuple is incomplete")

    present = methods.get("OH_PRESENT_TIMESTAMP", {})
    present_source = present.get("source", {})
    if (
        "Surface::GetPresentTimestamp("
        not in present_source.get("exact_oh_call", "")
        or present_source.get("accepted_return") != "GSERROR_OK"
        or present.get("acceptance", {}).get(
            "exact_surface_generation_join_required"
        )
        is not True
        or present.get("acceptance", {}).get(
            "unsupported_timestamp_is_evidence_gap"
        )
        is not True
    ):
        failures.append("J02 OH present typed-source contract drifted")
    for locator in present_source.get("source_locators", []):
        if not (root / locator).is_file():
            failures.append(f"J02 OH present source locator missing: {locator}")

    subjects = _mapping(journey.get("subjects"), "subjects", failures)
    if set(subjects) != set(J02_ANCHORS):
        failures.append("J02 subject set drifted")
    anchors_by_id: dict[str, dict] = {}
    for subject, expected_anchor_ids in J02_ANCHORS.items():
        subject_value = _mapping(
            subjects.get(subject), f"subject {subject}", failures
        )
        anchors = _list(
            subject_value.get("apk_owned_visual_anchors"),
            f"subject {subject}.apk_owned_visual_anchors",
            failures,
        )
        actual_ids = {
            anchor.get("id")
            for anchor in anchors
            if isinstance(anchor, dict)
        }
        if actual_ids != expected_anchor_ids:
            failures.append(f"J02 {subject}: anchor set drifted")
        for anchor in anchors:
            if not isinstance(anchor, dict):
                failures.append(f"J02 {subject}: anchor must be a mapping")
                continue
            anchor_id = anchor.get("id")
            anchors_by_id[anchor_id] = anchor
            _validate_method_references(
                anchor.get("measurement_methods"),
                f"anchor {anchor_id}.measurement_methods",
                failures,
            )
            if set(anchor.get("measurement_methods", [])) != (
                J02_ANCHOR_METHODS.get(anchor_id, set())
            ):
                failures.append(
                    f"J02 anchor {anchor_id}: measurement methods drifted"
                )
            source_anchor = anchor.get("source_anchor")
            expected_source_anchor = J02_SOURCE_ANCHORS.get(anchor_id)
            if expected_source_anchor:
                if source_anchor != expected_source_anchor:
                    failures.append(
                        f"J02 anchor {anchor_id}: source anchor drifted"
                    )
                elif not (root / source_anchor).is_file():
                    failures.append(
                        f"J02 anchor {anchor_id}: source anchor missing"
                    )

    u00 = anchors_by_id.get("U00-COLOR", {})
    u01_background = anchors_by_id.get("U01-BACKGROUND", {})
    u01_text = anchors_by_id.get("U01-TEXT", {})
    if (
        u00.get("expected_srgb_hex") != "#13375A"
        or u01_background.get("expected_srgb_hex") != "#13375A"
    ):
        failures.append("J02 G6 exact sRGB anchors drifted")
    if (
        u01_text.get("exact_text") != "HELLO UNITY\nATOM U01"
        or u01_text.get("text_match", {}).get("method")
        != "CASE_SENSITIVE_OCR"
        or u01_text.get("text_match", {}).get("case_sensitive") is not True
        or u01_text.get("text_match", {}).get("expected_normalized_lines")
        != ["HELLO UNITY", "ATOM U01"]
    ):
        failures.append("J02 U01 exact case-sensitive text anchor drifted")

    menu = anchors_by_id.get("G7-MAIN-MENU", {})
    if tuple(menu.get("required_text", [])) != J02_MENU_TEXT:
        failures.append(
            "J02 G7 menu text drifted; screenshot_1 excludes Exit"
        )
    if "Exit" in menu.get("required_text", []):
        failures.append("J02 screenshot_1 must not anchor Exit")
    if (
        menu.get("text_match", {}).get("method") != "CASE_SENSITIVE_OCR"
        or menu.get("text_match", {}).get("case_sensitive") is not True
    ):
        failures.append("J02 G7 menu text must be case-sensitive OCR")
    _validate_source_reference(
        root, "G7-MAIN-MENU", menu.get("source_reference"), failures
    )
    menu_ref = menu.get("source_reference", {})
    if (
        menu_ref.get("anchor_scope") != "layout_and_listed_text_only"
        or menu_ref.get("evidence_role")
        != "SOURCE_REFERENCE_NON_RUNTIME_EVIDENCE"
    ):
        failures.append("J02 screenshot_1 scope/evidence role drifted")

    board = anchors_by_id.get("G7-NUMBER-BOARD", {})
    _validate_source_reference(
        root, "G7-NUMBER-BOARD", board.get("source_reference"), failures
    )
    board_ref = board.get("source_reference", {})
    if (
        board_ref.get("anchor_scope") != "layout_only"
        or board_ref.get("known_grid_size") != "3x3"
        or board_ref.get("evidence_role")
        != "NON_EVIDENCE_FOR_RUNTIME_2X2_STRUCTURE"
        or board_ref.get("may_prove_runtime_2x2") is not False
    ):
        failures.append(
            "J02 screenshot_3 must remain 3x3 layout-only non-evidence"
        )
    if board.get("required_structure") != [
        "a 2x2 board containing labels 1, 2, and 3 exactly once",
        "exactly one empty board cell",
        "a visible Time value in mm:ss form",
        "visible Reset and Back controls",
    ]:
        failures.append("J02 runtime 2x2 structure anchor drifted")

    grid = methods.get("G7_GRID_STATE", {}).get("algorithm", {})
    if (
        grid.get("selected_grid") != "2x2"
        or grid.get("expected_numeric_labels") != ["1", "2", "3"]
        or grid.get("expected_empty_cells") != 1
        or grid.get("state_encoding")
        != "row-major list of three labels and one EMPTY token"
    ):
        failures.append("J02 G7 grid-state algorithm drifted")
    causality = methods.get("INPUT_CAUSALITY", {}).get("algorithm", {})
    if (
        causality.get("before_after_join")
        != "same process and Surface generation"
        or causality.get("chosen_tile_rule")
        != "smallest numeric label orthogonally adjacent to EMPTY"
        or causality.get("accepted_delta")
        != "chosen label and EMPTY exchange cells; every other cell is unchanged"
    ):
        failures.append("J02 G7 input-causality algorithm drifted")

    exit_control = subjects.get("G7", {}).get("exit_control", {})
    if (
        exit_control.get("exact_text") != "Exit"
        or exit_control.get("text_match_method") != "CASE_SENSITIVE_OCR"
        or exit_control.get("case_sensitive") is not True
        or exit_control.get("validation_scope") != "exit_relaunch_only"
    ):
        failures.append("J02 Exit must be validated only in exit_relaunch")
    if (
        subjects.get("G7", {}).get("pause_timer_oracle") != "none"
        or subjects.get("G7", {}).get("surface_rebuild_timer_oracle") != "none"
        or subjects.get("G7", {}).get(
            "process_generation_must_remain_same"
        )
        is not True
    ):
        failures.append(
            "J02 pause/rebuild must use process gate without timer speculation"
        )
    timer = subjects.get("G7", {}).get("continuous_gameplay", {})
    timer_measurement = timer.get("timer_measurement", {})
    if (
        timer.get("observation_window_seconds") != 10
        or timer.get("minimum_distinct_visible_timer_values") != 3
        or timer_measurement.get("method") != "CASE_SENSITIVE_OCR"
        or timer_measurement.get("value_regex") != r"^[0-9]{2}:[0-9]{2}$"
        or timer_measurement.get("label_case_rule")
        != "not_used_numeric_value_only"
        or timer_measurement.get("comparison_scope")
        != "active_foreground_window_only"
    ):
        failures.append("J02 active-game timer measurement drifted")

    cases = _mapping(journey.get("cases"), "cases", failures)
    if set(cases) != set(J02_CASES):
        failures.append("J02 P/N/F category set drifted")
    coverage = {
        category: {subject: 0 for subject in J02_SUBJECT_TO_ARTIFACT}
        for category in J02_CASES
    }
    expected_verdicts = {
        "positive": "PASS",
        "negative": "REJECT",
        "failure": "NOT_PROVEN",
    }
    for category, expected_cases in J02_CASES.items():
        entries = _list(cases.get(category), f"cases.{category}", failures)
        by_id = {
            entry.get("id"): entry
            for entry in entries
            if isinstance(entry, dict)
        }
        if set(by_id) != set(expected_cases):
            failures.append(f"J02 cases.{category}: case set drifted")
        for case_id, expected_subjects in expected_cases.items():
            case = _mapping(
                by_id.get(case_id), f"case {case_id}", failures
            )
            if "subject" in case:
                failures.append(
                    f"J02 case {case_id}: use applies_to, not singular subject"
                )
            applies_to = _list(
                case.get("applies_to"),
                f"case {case_id}.applies_to",
                failures,
            )
            if set(applies_to) != expected_subjects:
                failures.append(
                    f"J02 case {case_id}: applies_to drifted"
                )
            if case.get("expected_verdict") != expected_verdicts[category]:
                failures.append(
                    f"J02 case {case_id}: expected_verdict drifted"
                )
            _validate_method_references(
                case.get("measurement_methods"),
                f"case {case_id}.measurement_methods",
                failures,
            )
            case_methods = set(case.get("measurement_methods", []))
            if case_methods != J02_CASE_METHODS[case_id]:
                failures.append(
                    f"J02 case {case_id}: measurement methods drifted"
                )
            for subject in set(applies_to) & set(J02_SUBJECT_TO_ARTIFACT):
                resolved_methods = {
                    method_id
                    for method_id in case_methods
                    if subject
                    in J02_METHOD_APPLICABILITY.get(method_id, set())
                }
                if not resolved_methods:
                    failures.append(
                        f"J02 case {case_id}: no methods resolve for {subject}"
                    )
                coverage[category][subject] += 1
    for category, subject_counts in coverage.items():
        for subject, count in subject_counts.items():
            if count == 0:
                failures.append(
                    f"J02 {subject}: no applicable {category} case"
                )

    policy = _mapping(
        journey.get("verdict_policy"), "verdict_policy", failures
    )
    if (
        policy.get("all_applicable_cases_required") is not True
        or policy.get("applicability_field") != "cases.*.applies_to"
        or not str(policy.get("case_method_resolution", "")).startswith(
            "For each subject in a case's applies_to list"
        )
        or policy.get("unavailable_measurement_case") != "F-EVIDENCE-GAP"
        or policy.get("generic_hilog_can_satisfy_measurement") is not False
    ):
        failures.append("J02 fail-closed applicability policy drifted")

    continuity = _mapping(
        journey.get("continuous_frame_contract"),
        "continuous_frame_contract",
        failures,
    )
    _validate_method_references(
        continuity.get("measurement_methods"),
        "continuous_frame_contract.measurement_methods",
        failures,
    )
    if not {"OH_PRESENT_TIMESTAMP", "SURFACE_GENERATION"}.issubset(
        set(continuity.get("measurement_methods", []))
    ):
        failures.append("J02 continuity lacks typed present/Surface methods")
    return failures


def main() -> int:
    failures: list[str] = []
    project = load_yaml(ROOT / "docs/spec/project.yaml")
    baseline = project.get("semantic_baseline", {})
    for name, expected in EXPECTED_ROOTS.items():
        actual = baseline.get(name, {}).get("source_root")
        if actual != expected:
            failures.append(f"source root {name}: {actual!r} != {expected!r}")
        elif not Path(expected).is_dir():
            failures.append(f"source root {name}: directory missing")

    excluded = baseline.get("excluded_current_source_roots", [])
    alex = next(
        (
            item
            for item in excluded
            if item.get("source_root") == "/opt/Bridge/src/AlexBridge"
        ),
        None,
    )
    if not alex or alex.get("build_input") is not False or alex.get(
        "journey_input"
    ) is not False:
        failures.append("src/AlexBridge is not fail-closed as a legacy-only root")

    journey = load_yaml(
        ROOT / "docs/spec/journeys/J01-first-frame-visible/journey.yaml"
    )
    hello_path, hello_sha = EXPECTED_INPUTS["HelloWorld"]
    subject = journey.get("subject", {})
    if subject.get("apk_path") != hello_path:
        failures.append("J01 HelloWorld path is not the frozen canonical input")
    if subject.get("apk_sha256") != hello_sha:
        failures.append("J01 HelloWorld SHA-256 drifted")

    unity = load_yaml(ROOT / "docs/spec/unity-goal-ladder.yaml")
    j02 = load_yaml(ROOT / J02_PATH)
    failures.extend(validate_j02(ROOT, j02, unity))
    unity_root = Path(unity["import_policy"]["canonical_root"])
    artifacts = {
        artifact["id"]: artifact
        for goal in unity.get("goals", [])
        for artifact in goal.get("artifacts", [])
    }
    for artifact_id in ("G6.U00", "G6.U01", "G7.APK"):
        expected_path, expected_sha = EXPECTED_INPUTS[artifact_id]
        artifact = artifacts.get(artifact_id, {})
        actual_path = unity_root / str(artifact.get("path", ""))
        if actual_path != ROOT / expected_path:
            failures.append(f"{artifact_id}: manifest path drifted")
        if artifact.get("sha256") != expected_sha:
            failures.append(f"{artifact_id}: manifest SHA-256 drifted")

    for artifact_id, (relative, expected_sha) in EXPECTED_INPUTS.items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            failures.append(f"{artifact_id}: missing regular input {relative}")
            continue
        actual_sha = sha256(path)
        if actual_sha != expected_sha:
            failures.append(
                f"{artifact_id}: payload SHA-256 {actual_sha} != {expected_sha}"
            )

    current_reference_roots = (
        ROOT / "src/adapter/build",
        ROOT / "docs/spec/journeys/J01-first-frame-visible",
        ROOT / "src/tools/experiments/d600/static_metadata_authority_gate.py",
        ROOT / "src/tools/experiments/fn05_input_receipt_ledger_test.cpp",
        ROOT / "src/tools/fn07_service_metadata_probe",
    )
    for reference_root in current_reference_roots:
        paths = (
            reference_root.rglob("*")
            if reference_root.is_dir()
            else (reference_root,)
        )
        for path in paths:
            if not path.is_file() or path.is_symlink():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if LEGACY_MARKER in text:
                failures.append(
                    f"current build/J01 reference still uses {LEGACY_MARKER}: "
                    f"{path.relative_to(ROOT)}"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        "PASS canonical source/demo inputs: "
        + " ".join(
            f"{name}={identity}" for name, (_, identity) in EXPECTED_INPUTS.items()
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
