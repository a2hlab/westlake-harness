#!/usr/bin/env python3
"""Validate the L11-L14 strategy-route visual rollout without changing artifacts."""

from __future__ import annotations

import argparse
import colorsys
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import subprocess

from PIL import Image


ROOT = Path("/opt/21.Game/02.unity.cardwords/adapter/research/atoms")
EXPECTED_COLORS = {
    "primary": "#159947",
    "backup": "#F28C28",
    "third": "#7C3AED",
    "structure": "#9AA0A6",
}
EXPECTED_STACK = [
    "Android App",
    "AOSP V14 Framework/API",
    "WestLake Adapter Boundary",
    "OpenHarmony 6.1 System Services",
    "OH 6.1 Kernel / Storage / Device",
]
EXPECTED_PROBABILITY = {
    "high": {"label": "高概率", "color": "#39D353"},
    "low": {"label": "低概率", "color": "#8B1E1E"},
    "almost_impossible": {"label": "almost impossible / 几乎不可能", "color": "#FF2B2B"},
    "undetermined": {"label": "证据不足 / 未定", "color": "#9AA0A6"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def visible_text(source: str) -> str:
    source = re.sub(r"<(?:script|style|pre|code)\b[^>]*>.*?</(?:script|style|pre|code)>", " ", source, flags=re.I | re.S)
    return unescape(re.sub(r"<[^>]+>", " ", source))


def color_gate(path: Path, require_purple: bool, probability_classes: set[str]) -> dict:
    image = Image.open(path).convert("RGB")
    counts = {"orange": 0, "green": 0, "purple": 0, "dark_red": 0, "bright_red": 0, "unauthorized": 0, "chromatic": 0}
    for red, green, blue in image.getdata():
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        if saturation <= 0.35 or value <= 0.25:
            continue
        counts["chromatic"] += 1
        degrees = hue * 360
        if degrees <= 5 or degrees >= 345:
            if value >= 0.72:
                counts["bright_red"] += 1
            else:
                counts["dark_red"] += 1
            if not probability_classes.intersection({"low", "almost_impossible"}):
                counts["unauthorized"] += 1
        elif 5 < degrees <= 45:
            counts["orange"] += 1
        elif 110 <= degrees <= 165:
            counts["green"] += 1
        elif 230 <= degrees <= 285:
            counts["purple"] += 1
        else:
            counts["unauthorized"] += 1
    unauthorized_ratio = counts["unauthorized"] / max(1, counts["chromatic"])
    passed = (
        counts["orange"] >= 500
        and counts["green"] >= 500
        and (not require_purple or counts["purple"] >= 500)
        and ("low" not in probability_classes or counts["dark_red"] >= 50)
        and ("almost_impossible" not in probability_classes or counts["bright_red"] >= 50)
        and (counts["unauthorized"] <= 1500 or unauthorized_ratio <= 0.01)
    )
    return {
        "pass": passed,
        "width": image.width,
        "height": image.height,
        "purple_required": require_purple,
        "counts": counts,
        "unauthorized_ratio": round(unauthorized_ratio, 6),
    }


def ocr_gate(path: Path, ocr: Path | None, probability_classes: set[str]) -> dict:
    if not ocr:
        return {"pass": False, "reason": "ocr unavailable", "text": ""}
    result = subprocess.run([str(ocr), str(path)], text=True, capture_output=True)
    text = result.stdout
    compact = normalized(text)
    checks = {
        "android_app": "androidapp" in compact,
        "framework_api": "aospv14" in compact and "framework" in compact and ("api" in compact or "iap" in compact),
        "adapter_boundary": "westlakeadapterboundary" in compact or ("adapter" in compact and "boundary" in compact),
        "oh_services": "openharmony61systemservices" in compact,
        "foundation": "oh61kernel" in compact and "storage" in compact and "device" in compact,
        "no_canonical": "canonical" not in text.lower(),
        "no_obsolete_authoritative_term": "权威验收口径" not in text,
        "no_prompt_meta_words_or_hex": re.search(
            r"PRIMARY\s+GREEN|BACKUP\s+ORANGE|THIRD\s+PURPLE|ADDITIONAL\s+NEUTRAL|"
            r"mechanism\s+concept|alternative\s+feasibility\s+badge|#[0-9A-Fa-f]{6}",
            text,
            re.I,
        )
        is None,
    }
    probability_checks = {
        "probability_heading_hint": not probability_classes
        or "可行概率" in text
        or "almostimpossible" in compact
        or bool(re.search(r"可行.{0,3}[率幸]", text)),
        "probability_labels": all(
            (
                ("高概率" in text)
                if probability_class == "high"
                else ("低概率" in text)
                if probability_class == "low"
                else ("almostimpossible" in compact or "几乎不可能" in text)
                if probability_class == "almost_impossible"
                else ("证据不足" in text or "未定" in text)
            )
            for probability_class in probability_classes
        ),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "probability_ocr_hints_non_blocking": probability_checks,
        "text": text.strip(),
        "rc": result.returncode,
    }


def js_gate(source: str) -> dict:
    scripts = "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", source, flags=re.I | re.S))
    if not scripts.strip():
        return {"pass": False, "reason": "no inline JS"}
    result = subprocess.run(["node", "--check"], input=scripts, text=True, capture_output=True)
    return {"pass": result.returncode == 0, "stderr": result.stderr.strip()}


def validate_atom(atom_dir: Path, ocr: Path | None) -> dict:
    atom_id = f"{atom_dir.parent.name}.{atom_dir.name}"
    required = [atom_dir / name for name in ("strategy.md", "routemap.md")]
    if not all(path.exists() for path in required):
        return {
            "atom_id": atom_id,
            "status": "BLOCKED_INPUT",
            "missing": [path.name for path in required if not path.exists()],
            "semantic_review": "NOT_COMPLETED",
        }
    image = atom_dir / "strategy-route-3d.jpg"
    strategy_text = (atom_dir / "strategy.md").read_text(encoding="utf-8")
    verdict_match = re.search(r"^verdict_status:\s*(.+)$", strategy_text, flags=re.M)
    verdict_status = verdict_match.group(1).strip() if verdict_match else ""
    recommended_match = re.search(r"^recommended:\s*(.+)$", strategy_text, flags=re.M)
    recommended_text = recommended_match.group(1).strip() if recommended_match else ""
    condition_match = re.search(r"^recommendation_condition:\s*(.+)$", strategy_text, flags=re.M)
    conditional_recommendation = bool(condition_match and condition_match.group(1).strip()) or "条件" in recommended_text
    confidence_match = re.search(r"^confidence:\s*(.+)$", strategy_text, flags=re.M)
    confidence = confidence_match.group(1).strip().lower() if confidence_match else ""
    evidence_blocked = "needs-source" in strategy_text.lower() or confidence in {"low", "very-low", "very low"}
    existing_protected = "用户已确认" in verdict_status and "默认选项" not in verdict_status
    receipt_path = atom_dir / "strategy-route-3d.json"
    html_paths = [path for path in (atom_dir / "strategy-review.html", atom_dir / "strategy_review.html") if path.exists()]
    failures: list[str] = []
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
    route_order = receipt.get("route_order") or []
    route_count = len(route_order)
    require_purple = route_count >= 3
    color_contract = receipt.get("color_contract") or {}
    probability_contract = receipt.get("probability_contract") or {}
    route_feasibility = receipt.get("route_feasibility") or {}
    primary_route = receipt.get("recommended")
    non_primary_routes = [route_id for route_id in route_order if route_id != primary_route]
    probability_classes = {
        str((route_feasibility.get(route_id) or {}).get("class", ""))
        for route_id in non_primary_routes
    }
    probability_entries_valid = all(
        (route_feasibility.get(route_id) or {}).get("class") in EXPECTED_PROBABILITY
        and bool((route_feasibility.get(route_id) or {}).get("basis"))
        for route_id in non_primary_routes
    )
    impossible_basis_valid = all(
        (route_feasibility.get(route_id) or {}).get("class") != "almost_impossible"
        or re.search(
            r"硬原则|范本|反例|已证伪|acceptance|验收",
            str((route_feasibility.get(route_id) or {}).get("basis", "")),
            re.I,
        )
        for route_id in non_primary_routes
    )
    probability_overlay = receipt.get("probability_overlay") or {}
    overlay_labels = probability_overlay.get("labels") or []
    overlay_by_route = {entry.get("route_id"): entry for entry in overlay_labels}
    probability_overlay_valid = (
        probability_overlay.get("schema_version") == 2
        and bool(probability_overlay.get("exact_stack_context"))
        and set(overlay_by_route) == set(non_primary_routes)
        and all(
            overlay_by_route[route_id].get("class") == (route_feasibility.get(route_id) or {}).get("class")
            and overlay_by_route[route_id].get("label")
            == EXPECTED_PROBABILITY.get((route_feasibility.get(route_id) or {}).get("class"), {}).get("label")
            and overlay_by_route[route_id].get("color")
            == EXPECTED_PROBABILITY.get((route_feasibility.get(route_id) or {}).get("class"), {}).get("color")
            and overlay_by_route[route_id].get("text", "").startswith(f"{route_id}  可行概率：")
            for route_id in non_primary_routes
        )
    )
    required_color_roles = ("primary", "backup", "structure") + (("third",) if require_purple else ())
    review_log_text = (atom_dir / "REVIEW_LOG.md").read_text(encoding="utf-8") if (atom_dir / "REVIEW_LOG.md").exists() else ""
    six_round_complete = all(f"student-r{index}" in review_log_text for index in (1, 2, 3)) and all(
        f"ieee-r{index}" in review_log_text for index in (1, 2, 3)
    )
    semantic_review = "COMPLETED" if six_round_complete else "NOT_COMPLETED"
    receipt_checks = {
        "exists": receipt_path.exists(),
        "atom_id": receipt.get("atom_id") == atom_id,
        "model": receipt.get("model") == "gemini-3-pro-image-preview",
        "image_hash": image.exists() and receipt.get("image_sha256") == sha256(image),
        "route_count": 2 <= route_count <= 5,
        "route_roles": receipt.get("recommended") in route_order
        and receipt.get("backup") in route_order
        and receipt.get("recommended") != receipt.get("backup"),
        "colors": all(color_contract.get(role) == EXPECTED_COLORS[role] for role in required_color_roles),
        "stack": receipt.get("stack_context") == EXPECTED_STACK,
        "single_diagram": receipt.get("single_diagram_multi_route") is True,
        "target_baseline": receipt.get("target_baseline") == {"android": "AOSP V14", "openharmony": "6.1"},
        "probability_contract": all(
            (probability_contract.get(probability_class) or {}).get("label") == spec["label"]
            and (probability_contract.get(probability_class) or {}).get("color") == spec["color"]
            for probability_class, spec in EXPECTED_PROBABILITY.items()
        ),
        "route_feasibility": probability_entries_valid,
        "almost_impossible_evidence_gate": impossible_basis_valid,
        "missing_evidence_stays_undetermined": "missing evidence must remain undetermined"
        in str(probability_contract.get("policy", "")),
        "probability_overlay": probability_overlay_valid,
    }
    if not all(receipt_checks.values()):
        failures.append("receipt")
    colors = color_gate(image, require_purple, probability_classes) if image.exists() else {"pass": False, "reason": "missing image"}
    if not colors["pass"]:
        failures.append("gamut")
    ocr_result = ocr_gate(image, ocr, probability_classes) if image.exists() else {"pass": False, "reason": "missing image"}
    if not ocr_result["pass"]:
        failures.append("ocr_stack_or_canonical")
    html_results = []
    if not html_paths:
        failures.append("html_missing")
    for html_path in html_paths:
        source = html_path.read_text(encoding="utf-8")
        visible = visible_text(source)
        full_term = "范本（原子唯一验收合同）"
        first_term = visible.find("范本")
        html_check = {
            "path": str(html_path),
            "visual_marker_or_eight_chapters": (
                'id="technical-route-stack-map-v3"' in source
                or all(f"第{chapter}章" in visible for chapter in ("一", "二", "三", "四", "五", "六", "七", "八"))
            ),
            "stack_caption": all(label in source for label in EXPECTED_STACK),
            "image_embedded": "data:image/" in source,
            "visible_canonical_zero": re.search(r"\bcanonical\b", visible, flags=re.I) is None,
            "visible_obsolete_term_zero": "权威验收口径" not in visible,
            "authority_first_full": first_term >= 0 and visible.find(full_term) == first_term,
            "decision_ui": (
                ("既有人工裁决（受保护）" in visible or "既有选择受保护" in visible)
                if existing_protected
                else "用户已确认·默认选项·可重新调整" in visible
            ),
            "no_obsolete_preselection": "默认预选·待复审" not in visible and "不因预选" not in visible,
            "direction_not_implementation_or_acceptance": (
                ("方向确认不等于实现批准" in visible or "不代表路线已实现" in visible)
                and ("不等于验收通过" in visible or "不代表范本已验收通过" in visible or "不代表路线已实现或验收通过" in visible)
            ),
            "conditional_prerequisite_disclosed": (
                not conditional_recommendation or "条件性推荐前置" in visible
            ),
            "evidence_blocker_disclosed": (
                not evidence_blocked or ("证据阻断" in visible or "证据门阻断" in visible)
            ),
            "probability_dual_encoding": (
                "可行概率" in visible
                and ("概率颜色不改变路线身份线色" in visible or "徽标不得改染路线" in visible)
                and all(EXPECTED_PROBABILITY[probability_class]["label"] in visible for probability_class in probability_classes)
            ),
            "probability_per_alternative": visible.count("可行概率：") >= len(non_primary_routes),
            "semantic_review_disclosed": (
                "语义审稿" in visible
                and (
                    (six_round_complete and ("已闭合" in visible or "REVIEW_LOG" in visible))
                    or (not six_round_complete and ("未完成" in visible or "尚未完成" in visible))
                )
            ),
            "js": js_gate(source),
        }
        html_check["pass"] = all(
            value if isinstance(value, bool) else value.get("pass", False)
            for key, value in html_check.items()
            if key not in {"path", "pass"}
        )
        if not html_check["pass"]:
            failures.append(f"html:{html_path.name}")
        html_results.append(html_check)
    return {
        "atom_id": atom_id,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "receipt": receipt_checks,
        "gamut": colors,
        "ocr": ocr_result,
        "html": html_results,
        "semantic_review": semantic_review,
        "version_evidence_gate": "PENDING_VERSION_ALIGNMENT_LANE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--floor-from", type=int, default=11)
    parser.add_argument("--floor-to", type=int, default=14)
    parser.add_argument("--ocr", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = []
    for floor in range(args.floor_from, args.floor_to + 1):
        for atom_dir in sorted((ROOT / f"L{floor:02d}").glob("A*")):
            if atom_dir.is_dir():
                rows.append(validate_atom(atom_dir, args.ocr))
    summary = {
        "total": len(rows),
        "pass": sum(row["status"] == "PASS" for row in rows),
        "fail": sum(row["status"] == "FAIL" for row in rows),
        "blocked_input": sum(row["status"] == "BLOCKED_INPUT" for row in rows),
        "semantic_review_completed": sum(row.get("semantic_review") == "COMPLETED" for row in rows),
        "version_evidence_gate": "PENDING_VERSION_ALIGNMENT_LANE",
    }
    report = json.dumps({"summary": summary, "atoms": rows}, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
