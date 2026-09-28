#!/usr/bin/env python3
"""Generate one evidence-labelled 3D route-comparison illustration with Gemini.

The image carries no prose because image-model text is not a trustworthy source.
Exact route names and evidence remain HTML/SVG overlays in strategy-review.html.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import ssl
import tempfile
import time
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFont


MODEL = "gemini-3-pro-image-preview"
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
PROBABILITY_COLORS = {
    "high": "#39D353",
    "low": "#8B1E1E",
    "almost_impossible": "#FF2B2B",
    "undetermined": "#9AA0A6",
}
PROBABILITY_LABELS = {
    "high": "高概率",
    "low": "低概率",
    "almost_impossible": "almost impossible / 几乎不可能",
    "undetermined": "证据不足 / 未定",
}
OVERLAY_SCHEMA_VERSION = 2
OVERLAY_FONT = Path("/System/Library/Fonts/STHeiti Medium.ttc")


def api_key() -> str:
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    key_path = Path.home() / ".gemini_key"
    match = re.search(r"AIza[0-9A-Za-z_-]+", key_path.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError(f"no Gemini API key found in {key_path}")
    return match.group(0)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    result: dict[str, str] = {}
    if not match:
        return result
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip("'\"")
    return result


def route_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not re.fullmatch(r"R\d+[A-Za-z]?", cells[0]):
            continue
        rows.append((cells[0], re.sub(r"[`*_]", "", cells[1])))
    if rows:
        return rows
    for match in re.finditer(r"^##+\s+(R\d+[A-Za-z]?)\s*[·.：:-]+\s*(.+)$", text, re.M):
        rows.append((match.group(1), match.group(2).strip()))
    return rows


def valid_route_ref(value: object, valid: set[str], fallback: str) -> str:
    """Pick the first referenced route that actually exists in the current routemap."""
    return next((route_id for route_id in re.findall(r"\bR\d+[A-Za-z]?\b", str(value or "")) if route_id in valid), fallback)


def route_context(route_id: str, routemap: str, strategy: str) -> str:
    """Collect only route-local prose used by the auditable feasibility classifier."""
    lines: list[str] = []
    for text in (routemap, strategy):
        source = text.splitlines()
        for index, line in enumerate(source):
            if re.match(rf"^\|\s*{re.escape(route_id)}\s*\|", line):
                lines.append(line)
            elif re.match(rf"^##+\s+.*\b{re.escape(route_id)}\b", line):
                lines.append(line)
                lines.extend(source[index + 1 : index + 5])
    return "\n".join(lines)


def feasibility(route_id: str, primary: str, routemap: str, strategy: str) -> tuple[str, str]:
    if route_id == primary:
        return "selected", "主选路线不使用备选可行概率徽标"
    strategy_context = route_context(route_id, "", strategy)
    routemap_context = route_context(route_id, routemap, "")
    # Strategy is the later route evaluation. Use its route-local evidence for
    # high/low/unknown when available; fall back to the non-decisional routemap.
    context = strategy_context or routemap_context
    combined_context = "\n".join(part for part in (routemap_context, strategy_context) if part)
    # An "almost impossible" label is a strong claim. Only route table rows and
    # route headings may authorize it; explanatory prose often says that some
    # *other* route is rejected or that a failure result must be explicit.
    decision_context = "\n".join(
        line for line in combined_context.splitlines() if line.startswith("|") or re.match(r"^##+", line)
    )
    decision_context = re.sub(
        r"不等于已拒绝|不是已拒绝|并非已拒绝|未被拒绝|不是已失败|并非已失败",
        "",
        decision_context,
    )
    impossible = re.compile(
        r"almost impossible|几乎不可能|已证伪|明确反例|反例路线|拒绝反例|已拒绝|明确拒绝|"
        r"\*\*出局\*\*|已出局|明确淘汰|明确不可行|判定不可行|"
        r"硬原则.{0,20}(?:明确不通过|违反)|违反.{0,20}(?:硬原则|范本|验收)|"
        r"(?:范本|acceptance|验收).{0,20}(?:明确不满足|明确违反)|不能承接.{0,20}验收",
        re.I | re.S,
    )
    insufficient = re.compile(
        r"缺少|缺乏|未证|未评估|证据(?:薄|弱|不足)|待证明|待证|未核验|未闭合|尚未|证据缺口",
        re.I,
    )
    low = re.compile(
        r"低概率|仅当|条件性|有条件|暂不|风险(?:大|高)|高成本|不推荐|前置条件|可维护性差",
        re.I,
    )
    high = re.compile(r"高概率|强先例|直接先例|成熟|(?<!不)可行|存活|有效备选|高置信", re.I)
    if impossible.search(decision_context):
        return "almost_impossible", "路线表状态或路线标题明确标为硬原则/范本失败、反例、拒绝或已证伪"
    if insufficient.search(context):
        return "undetermined", "路线局部文本仅表明证据缺口；按纪律保持证据不足/未定"
    if low.search(context):
        return "low", "路线局部文本含条件、高风险、高成本或不推荐信号"
    if high.search(context):
        return "high", "路线局部文本含明确可行、存活、成熟或强先例信号"
    return "undetermined", "路线局部文本没有足以判定高/低/几乎不可能的证据"


def build_prompt(
    atom_id: str,
    title: str,
    routes: list[tuple[str, str]],
    primary: str,
    backup: str,
    route_feasibility: dict[str, dict[str, str]],
) -> str:
    ordered: list[tuple[str, str]] = []
    route_map = dict(routes)
    if primary in route_map:
        ordered.append((primary, route_map[primary]))
    if backup in route_map and backup != primary:
        ordered.append((backup, route_map[backup]))
    for route_id, mechanism in routes:
        if route_id not in {primary, backup}:
            ordered.append((route_id, mechanism))

    route_text = "\n".join(
        f"- {route_id}: "
        + re.sub(
            r"权威验收口径",
            "范本",
            re.sub(r"canonical\s+acceptance", "范本", re.sub(r"\bcanonical\b", "范本", mechanism, flags=re.I), flags=re.I),
        )
        for route_id, mechanism in ordered
    )
    return f"""
Create a clean isometric 3D technical route-comparison illustration for a systems architecture textbook.
Atom identity for visual semantics only: {atom_id} {title}.

Routes:
{route_text}

STRICT visual grammar:
- Compose ONE diagram containing every listed route. Do not produce separate panels or isolated route icons.
- The diagram must visibly include the surrounding target software stack as neutral-grey isometric layers, not merely abstract input/output endpoints. Use these exact short layer labels, ordered from caller to host foundation: "Android App", "AOSP V14 Framework/API", "WestLake Adapter Boundary", "OpenHarmony 6.1 System Services", "OH 6.1 Kernel / Storage / Device". If a layer is not traversed by a route it still remains visible in grey as context.
- One shared neutral-grey input enters from the relevant source/caller layer and one shared neutral-grey observable result returns to the relevant consumer/evidence layer. Place each mechanism only at the stack layer implied by its supplied mechanism text. Governance or baseline routes may be var/evidence/provenance overlays spanning source, build artifact and device layers; do not turn them into runtime calls.
- Overlay every listed route as a separate, spatially separated 3D lane through this same stack. The lanes must visibly differ in crossed layers, ownership and topology, not merely in color. Shared stack boxes, shared endpoints and shared path segments stay grey until the routes diverge.
- Color the first listed route saturated green, the second saturated orange, and the third saturated purple. Use route IDs only as visible lane labels.
- Preserve those route-identity colors from end to end. Feasibility is encoded later in a separate native-text strip and must never recolor a route lane or connector.
- Do not draw feasibility badges or probability words inside the 3D canvas; an exact native-text probability strip is appended after generation. This keeps model-generated text from becoming evidence.
- Any fourth/fifth route lane, non-route connector, process/ABI/security boundary, platform, stack layer, scaffold, shadow edge, grid, or decorative structure is neutral grey only. No blue, red, yellow, cyan, pink, brown, or multicolor gradient.
- Neutral light background. Thin precise grey connector lines. Strong separation among the three assigned lane colors.
- Use only mechanism objects directly stated or unambiguously implied by the supplied route text. For example, a source-patch baseline may show a source tree/patch set; a build-artifact baseline may show artifacts/manifest; a device-receipt baseline may show a device and signed receipt. Do not invent BMS, package ledgers, RPC, sidecars, resolvers, storage, network tunnels, security modules, or runtime projection unless those words or their direct equivalent appear in that route's mechanism text.
- Every colored route must preserve its supplied route identity end to end. Do not swap a route's mechanism, endpoint, process topology, or stack ownership merely to make the picture more dramatic.
- No people, no real-world scene, no logos, no code, no title, no fake UI, and no border. Text is restricted to the five exact stack labels above and short route IDs; keep all labels horizontal and readable. Show mechanisms as objects/topology, not prose. The HTML supplies the authoritative wording.
- Never write or draw color names, route-order labels, color values, prompt-instruction vocabulary, the English word "canonical", or the obsolete Chinese phrase "权威验收口径" in the image. If that acceptance-contract concept is needed, use the Chinese word "范本" only.
- The target versions are fixed: AOSP V14 and OpenHarmony 6.1. Never label the target stack AOSP V15, OpenHarmony V7, or any newer version.
- Professional IEEE/software-architecture textbook aesthetic, crisp isometric 3D, 16:9 composition, generous spacing, readable at page width.
""".strip()


def request_image(prompt: str, retries: int = 4) -> tuple[bytes, str]:
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
                "imageConfig": {"aspectRatio": "16:9", "imageSize": "1K"},
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        API.format(model=MODEL, key=api_key()),
        data=body,
        headers={"Content-Type": "application/json"},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                result = json.load(response)
            for part in (result.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
                inline = part.get("inlineData")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"]), inline.get("mimeType", "image/png")
            raise RuntimeError("Gemini returned no image part")
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt + 1 == retries:
                raise
            time.sleep(5 * (attempt + 1))
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError, http.client.IncompleteRead):
            if attempt + 1 == retries:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def add_probability_overlay(
    image_bytes: bytes,
    routes: list[tuple[str, str]],
    primary: str,
    route_feasibility: dict[str, dict[str, str]],
) -> tuple[bytes, dict[str, object]]:
    """Append an exact native-text probability strip without touching route pixels."""
    source = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    alternatives = [route_id for route_id, _ in routes if route_id != primary]
    columns = 2
    rows = max(1, (len(alternatives) + columns - 1) // columns)
    heading_height = 76
    row_height = 54
    strip_height = heading_height + rows * row_height + 12
    canvas = Image.new("RGB", (source.width, source.height + strip_height), "#FFFFFF")
    canvas.paste(source, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(OVERLAY_FONT), 24)
    small_font = ImageFont.truetype(str(OVERLAY_FONT), 20)
    draw.text(
        (22, source.height + 8),
        "备选可行概率（徽标色独立于路线线色）",
        fill="#20242B",
        font=font,
    )
    draw.text(
        (22, source.height + 39),
        "Android App → AOSP V14 Framework/API → WestLake Adapter Boundary → OpenHarmony 6.1 System Services → OH 6.1 Kernel / Storage / Device",
        fill="#454A50",
        font=ImageFont.truetype(str(OVERLAY_FONT), 15),
    )
    cell_width = source.width // columns
    labels: list[dict[str, str]] = []
    for index, route_id in enumerate(alternatives):
        feasibility_record = route_feasibility[route_id]
        probability_class = feasibility_record["class"]
        label = PROBABILITY_LABELS[probability_class]
        color = PROBABILITY_COLORS[probability_class]
        column = index % columns
        row = index // columns
        left = column * cell_width + 22
        top = source.height + heading_height + row * row_height
        right = (column + 1) * cell_width - 22
        bottom = top + 42
        draw.rounded_rectangle((left, top, right, bottom), radius=18, fill=color, outline="#454A50", width=2)
        text_color = "#FFFFFF" if probability_class == "low" else "#111111"
        exact_text = f"{route_id}  可行概率：{label}"
        draw.text((left + 14, top + 7), exact_text, fill=text_color, font=small_font)
        labels.append(
            {
                "route_id": route_id,
                "class": probability_class,
                "label": label,
                "color": color,
                "text": exact_text,
            }
        )
    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=95, subsampling=0)
    return output.getvalue(), {
        "schema_version": OVERLAY_SCHEMA_VERSION,
        "placement": "native-text stack/probability strip appended below Gemini diagram; original route pixels unchanged",
        "source_image_height": source.height,
        "strip_height": strip_height,
        "exact_stack_context": "Android App → AOSP V14 Framework/API → WestLake Adapter Boundary → OpenHarmony 6.1 System Services → OH 6.1 Kernel / Storage / Device",
        "labels": labels,
    }


def remove_existing_overlay(
    image_bytes: bytes,
    old_overlay: dict[str, object],
    routes: list[tuple[str, str]],
    primary: str,
) -> bytes:
    """Recover the Gemini base pixels before replacing an older native strip."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    source_height = old_overlay.get("source_image_height")
    if not isinstance(source_height, int) or not 0 < source_height < image.height:
        alternatives = [route_id for route_id, _ in routes if route_id != primary]
        rows = max(1, (len(alternatives) + 1) // 2)
        old_heading = 42 if old_overlay.get("schema_version") == 1 else 76
        source_height = image.height - (old_heading + rows * 54 + 12)
    if not 0 < source_height <= image.height:
        raise RuntimeError("invalid prior probability-overlay height")
    base = image.crop((0, 0, image.width, source_height))
    output = io.BytesIO()
    base.save(output, format="JPEG", quality=95, subsampling=0)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("atom_dir", type=Path)
    parser.add_argument("--output", default="strategy-route-3d.jpg")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    atom_dir = args.atom_dir.resolve()
    strategy_path = atom_dir / "strategy.md"
    routemap_path = atom_dir / "routemap.md"
    atom_path = atom_dir / "atom.yaml"
    strategy = strategy_path.read_text(encoding="utf-8")
    routemap = routemap_path.read_text(encoding="utf-8")
    atom = atom_path.read_text(encoding="utf-8") if atom_path.exists() else ""
    meta = parse_frontmatter(strategy)
    atom_meta = parse_frontmatter(atom)
    atom_id = meta.get("atom_id") or atom_meta.get("atom_id") or atom_dir.parent.name + "." + atom_dir.name
    title_match = re.search(r"^title:\s*(.+)$", atom, re.M)
    title = title_match.group(1).strip() if title_match else meta.get("atom_name", atom_id)
    routes = route_rows(routemap)
    if len(routes) < 2:
        raise RuntimeError(f"{atom_id}: expected at least two routemap routes, found {len(routes)}")
    valid_routes = {route_id for route_id, _ in routes}
    primary = valid_route_ref(meta.get("recommended"), valid_routes, routes[0][0])
    backup = valid_route_ref(meta.get("backup"), valid_routes, routes[1][0])
    if backup == primary:
        backup = next((route_id for route_id, _ in routes if route_id != primary), routes[1][0])
    route_feasibility: dict[str, dict[str, str]] = {}
    for route_id, _ in routes:
        probability_class, basis = feasibility(route_id, primary, routemap, strategy)
        route_feasibility[route_id] = {"class": probability_class, "basis": basis}
    prompt = build_prompt(atom_id, title, routes, primary, backup, route_feasibility)

    output = atom_dir / args.output
    receipt = atom_dir / "strategy-route-3d.json"
    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if output.exists() and receipt.exists() and not args.force:
        old = json.loads(receipt.read_text(encoding="utf-8"))
        if (
            old.get("prompt_sha256") == prompt_sha
            and old.get("model") == MODEL
            and (old.get("probability_overlay") or {}).get("schema_version") == OVERLAY_SCHEMA_VERSION
        ):
            print(f"SKIP {atom_id} {output}")
            return 0

    # A prior receipt with the same route/stack/color contract proves that the
    # base picture was already generated by Gemini under the requested visual
    # grammar.  If it only lacks the deterministic native-text probability
    # strip, preserve those Gemini pixels and add the strip instead of paying
    # for a semantically identical regeneration.
    reused_gemini_base = False
    old_base_sha = ""
    old: dict[str, object] = {}
    if output.exists() and receipt.exists():
        try:
            old = json.loads(receipt.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            old = {}
    expected_stack = [
        "Android App",
        "AOSP V14 Framework/API",
        "WestLake Adapter Boundary",
        "OpenHarmony 6.1 System Services",
        "OH 6.1 Kernel / Storage / Device",
    ]
    may_reuse = (
        not args.force
        and old.get("model") == MODEL
        and old.get("route_order") == [route_id for route_id, _ in routes]
        and old.get("recommended") == primary
        and old.get("single_diagram_multi_route") is True
        and old.get("stack_context") == expected_stack
        and bool(old.get("probability_contract"))
    )
    if may_reuse:
        image = output.read_bytes()
        old_overlay = old.get("probability_overlay")
        if isinstance(old_overlay, dict) and old_overlay:
            image = remove_existing_overlay(image, old_overlay, routes, primary)
        mime = str(old.get("mime_type") or "image/jpeg")
        reused_gemini_base = True
        old_base_sha = hashlib.sha256(image).hexdigest()
    else:
        image, mime = request_image(prompt)
    image, probability_overlay = add_probability_overlay(image, routes, primary, route_feasibility)
    mime = "image/jpeg"
    with tempfile.NamedTemporaryFile(dir=atom_dir, prefix=".route-3d-", delete=False) as handle:
        handle.write(image)
        temp_path = Path(handle.name)
    os.replace(temp_path, output)
    record = {
        "schema_version": 1,
        "atom_id": atom_id,
        "model": MODEL,
        "mime_type": mime,
        "prompt_sha256": prompt_sha,
        "image_sha256": hashlib.sha256(image).hexdigest(),
        "gemini_base_reused": reused_gemini_base,
        "gemini_base_image_sha256": old_base_sha or None,
        "route_order": [route_id for route_id, _ in routes],
        "recommended": primary,
        "backup": backup,
        "color_contract": {
            "primary": "#159947",
            "backup": "#F28C28",
            "third": "#7C3AED",
            "structure": "#9AA0A6",
        },
        "probability_contract": {
            "scope": "non-primary route badge/halo only; never recolor route lanes or connectors",
            "high": {"label": "高概率", "color": PROBABILITY_COLORS["high"]},
            "low": {"label": "低概率", "color": PROBABILITY_COLORS["low"]},
            "almost_impossible": {
                "label": "almost impossible / 几乎不可能",
                "color": PROBABILITY_COLORS["almost_impossible"],
            },
            "undetermined": {"label": "证据不足 / 未定", "color": PROBABILITY_COLORS["undetermined"]},
            "policy": "almost_impossible only for explicit hard-principle/范本 failure or proven counterexample; missing evidence must remain undetermined",
        },
        "route_feasibility": route_feasibility,
        "probability_overlay": probability_overlay,
        "stack_context": expected_stack,
        "single_diagram_multi_route": True,
        "target_baseline": {"android": "AOSP V14", "openharmony": "6.1"},
    }
    receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {atom_id} {output} {record['image_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
