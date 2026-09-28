#!/usr/bin/env python3
"""Audit per-atom strategy HTML and Gemini multi-route software-stack visuals."""

from __future__ import annotations

import argparse
import colorsys
import json
from pathlib import Path
import re

from PIL import Image
import yaml


ROOT = Path("/opt/21.Game/02.unity.cardwords/adapter/research/atoms")
COLORS = ("#159947", "#F28C28", "#7C3AED", "#9AA0A6")
PROBABILITY_COLORS = {
    "high": "#39D353",
    "low": "#8B1E1E",
    "almost_impossible": "#FF2B2B",
    "undetermined": "#9AA0A6",
}


def frontmatter(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    return yaml.safe_load(match.group(1)) or {} if match else {}


def route_count(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    ids = set()
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and re.fullmatch(r"R\d+[A-Za-z]?", cells[0]):
                ids.add(cells[0])
    if not ids:
        ids.update(re.findall(r"^##+\s+(R\d+[A-Za-z]?)\s*[·.：:-]", text, re.M))
    return len(ids)


def route_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    ids = set(re.findall(r"^\|\s*(R\d+[A-Za-z]?)\s*\|", text, re.M))
    if not ids:
        ids.update(re.findall(r"^##+\s+(R\d+[A-Za-z]?)\s*[·.：:-]", text, re.M))
    return ids


def image_path(atom: Path) -> Path | None:
    candidates = [atom / "strategy-route-3d.jpg", atom / "strategy-route-3d.png"]
    candidates += sorted(atom.glob("*route*stack*3d*.jpg"))
    candidates += sorted(atom.glob("assets/*route*3d*.jpg"))
    return next((path for path in candidates if path.exists()), None)


def html_path(atom: Path) -> Path | None:
    for name in ("strategy-review.html", "strategy_review.html"):
        path = atom / name
        if path.exists():
            return path
    return None


def color_percent(path: Path) -> dict[str, float]:
    image = Image.open(path).convert("RGB")
    image.thumbnail((900, 900))
    counts = {"green": 0, "orange": 0, "purple": 0, "neutral": 0, "other": 0}
    for red, green, blue in image.getdata():
        hue, saturation, _ = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        degrees = hue * 360
        if saturation < 0.18:
            key = "neutral"
        elif 75 <= degrees <= 175:
            key = "green"
        elif 15 <= degrees <= 55:
            key = "orange"
        elif 245 <= degrees <= 315:
            key = "purple"
        else:
            key = "other"
        counts[key] += 1
    total = sum(counts.values())
    return {key: round(value * 100 / total, 3) for key, value in counts.items()}


def visible_canonical(text: str) -> int:
    protected = re.sub(r'<(?:script|style|pre|code)\b[^>]*>.*?</(?:script|style|pre|code)>', '', text, flags=re.I | re.S)
    visible = re.sub(r'<[^>]+>', '', protected)
    return len(re.findall(r"\bcanonical\b", visible, re.I))


def audit(atom: Path) -> dict:
    atom_id = f"{atom.parent.name}.{atom.name}"
    strategy = atom / "strategy.md"
    route_id_set = route_ids(atom / "routemap.md")
    routes = len(route_id_set)
    page = html_path(atom)
    image = image_path(atom)
    meta = frontmatter(strategy)
    decision = str(meta.get("verdict_status", "")) + " " + str(meta.get("review_status", ""))
    confirmed = any(token in decision for token in ("用户已确认", "已审视", "已确认"))
    html = page.read_text(encoding="utf-8") if page else ""
    receipt_path = atom / "strategy-route-3d.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
    colors = color_percent(image) if image else {}
    stack_terms = ("Android App", "AOSP V14 Framework/API", "WestLake Adapter Boundary", "OpenHarmony 6.1 System Services", "OH 6.1 Kernel / Storage / Device")
    stack_context = all(term in html for term in stack_terms) and bool(receipt.get("single_diagram_multi_route") or "data-single-diagram=\"true\"" in html)
    target = receipt.get("target_baseline") or {}
    target_baseline = target.get("android") == "AOSP V14" and target.get("openharmony") == "6.1" and "目标版本证据门" in html
    color_ok = bool(colors) and colors["green"] >= 0.5 and colors["orange"] >= 0.5 and colors["neutral"] >= 40 and colors["other"] < 5
    if routes >= 3:
        color_ok = color_ok and colors["purple"] >= 0.5
    exact_css = all(color.lower() in html.lower() for color in COLORS[:2]) and (routes < 3 or COLORS[2].lower() in html.lower()) and COLORS[3].lower() in html.lower()
    decision_ok = not confirmed or any(token in html for token in ("既有人工裁决（受保护）", str(meta.get("verdict_status", "")), str(meta.get("selected_route", ""))))
    probability_contract = receipt.get("probability_contract") or {}
    feasibility = receipt.get("route_feasibility") or {}
    primary = str(receipt.get("recommended", ""))
    probability_ok = (
        all((probability_contract.get(key) or {}).get("color", "").upper() == color for key, color in PROBABILITY_COLORS.items())
        and set(feasibility) == route_id_set
        and primary in route_id_set
        and (feasibility.get(primary) or {}).get("class") == "selected"
        and all(
            (feasibility.get(route_id) or {}).get("class") in PROBABILITY_COLORS
            for route_id in route_id_set - {primary}
        )
        and all(color.lower() in html.lower() for color in PROBABILITY_COLORS.values())
        and "可行概率" in html
        and "almost impossible" in html
        and "缺证据只能保持灰色未定" in html
    )
    human_decision = "用户已确认" in str(meta.get("verdict_status", "")) and str(meta.get("selected_route", "")) in route_id_set
    checks = {
        "strategy": strategy.exists(),
        "routes": 2 <= routes <= 5,
        "html": page is not None,
        "image": image is not None,
        "receipt": bool(receipt),
        "single_stack": stack_context,
        "target_baseline": target_baseline,
        "colors": color_ok,
        "probability": probability_ok,
        "exact_css": exact_css,
        "fanben_term": visible_canonical(html) == 0 and "权威验收口径" not in html and "范本" in html,
        "decision_protected": decision_ok,
        "human_decision": human_decision,
    }
    return {
        "atom": atom_id,
        "route_count": routes,
        "html": str(page) if page else "",
        "image": str(image) if image else "",
        "confirmed": confirmed,
        "visible_canonical": visible_canonical(html),
        "colors": colors,
        "checks": checks,
        "pass": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--floor-from", type=int, default=1)
    parser.add_argument("--floor-to", type=int, default=14)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    atoms = [path for path in sorted(ROOT.glob("L*/A*")) if path.is_dir() and args.floor_from <= int(path.parent.name[1:]) <= args.floor_to]
    rows = [audit(atom) for atom in atoms]
    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    passed = sum(row["pass"] for row in rows)
    print(f"atoms={len(rows)} pass={passed} fail={len(rows) - passed}")
    for row in rows:
        if not row["pass"]:
            failed = ",".join(key for key, value in row["checks"].items() if not value)
            print(f"FAIL {row['atom']} {failed}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
