import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[2]))
MASTER = WORKSPACES / "westlake-harness"
METADATA = MASTER / "benchmark/2026-10-08-lit-apps-report/apps.json"
GALLERY = WORKSPACES / "westlake-inputs/reports/2026-10-08-lit-apps/report-data.json"
UNLIT = MASTER / "benchmark/2026-10-08-u14-first-fatal-clusters"
FIRST_TAPS = WORKSPACES / "westlake-harness-t4/benchmark/2026-10-09-demo-baseline/first-tap-candidates.md"
UNLIT_GAME_KEYS = {
    "fd-app": ("Unciv", "game"),
    "fd-shatteredpixeldungeon": ("Shattered Pixel Dungeon", "game"),
    "mindustry": ("Mindustry", "game"),
    "ppsspp": ("PPSSPP", "game-tool"),
    "subwaysurfers": ("Subway Surfers", "game"),
    "cv2-com-bytehamster-flowitgame": ("Flowit!", "game"),
    "cv2-com-chessclock-android": ("Chess Clock", "game-tool"),
    "cv2-org-linaro-glmark2": ("glmark2", "graphics-benchmark"),
}


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def expand(value):
    return Path(value.replace("$WORKSPACES/", str(WORKSPACES) + "/")
                .replace("$HOME/", str(Path.home()) + "/"))


def portable(value):
    value = str(value)
    for prefix, token in ((WORKSPACES, "$WORKSPACES"), (Path.home(), "$HOME")):
        if value.startswith(str(prefix) + "/"):
            return token + value[len(str(prefix)):]
    return value


def pin(path):
    return {"path": portable(path), "sha256": digest(path)}


def read_json(path):
    return json.loads(Path(path).read_text())


def portable_tree(value):
    if isinstance(value, str):
        return portable(value)
    if isinstance(value, list):
        return [portable_tree(item) for item in value]
    if isinstance(value, dict):
        return {key: portable_tree(item) for key, item in value.items()}
    return value


def apk_package(path):
    from androguard.core.axml import AXMLPrinter
    from loguru import logger
    logger.disable("androguard")
    with zipfile.ZipFile(path) as archive:
        document = AXMLPrinter(archive.read("AndroidManifest.xml")).get_xml_obj()
    if document is None or not document.get("package"):
        raise ValueError("unreadable AndroidManifest package")
    return document.get("package")


def verify_identity(app, package_reader=apk_package):
    key = app["key"]
    try:
        apk = expand(app["apk_path"])
        actual_sha = digest(apk)
        if actual_sha != app["apk_sha256"]:
            raise ValueError("APK SHA differs from signed metadata")
        package = package_reader(apk)
        if package != app["package"]:
            raise ValueError("APK package differs from signed metadata")
        record_path = expand(app["record_path"])
        if digest(record_path) != app["record_sha256"]:
            raise ValueError("signed source record SHA changed")
        record = read_json(record_path)
        expected = (key, package, actual_sha)
        if (record.get("key"), record.get("package"), record.get("apk_sha256")) != expected:
            raise ValueError("signed source record identity differs")
        return {"key": key, "package": package, "apk": portable(apk),
                "apk_sha256": actual_sha, "apk_bytes": apk.stat().st_size,
                "record": pin(record_path), "identity_verified": True}
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        raise ValueError(f"{key}: {error}") from error


def selection(apps, gallery):
    metadata = {app["key"]: app for app in apps}
    if len(metadata) != len(apps):
        raise ValueError("duplicate metadata key")
    covered = []
    rows = []
    packages = set()
    for partition in ("shown", "minimal", "errors"):
        for shot in gallery[partition]:
            key = shot["key"]
            app = metadata[key]
            if shot["pkg"] != app["package"] or shot["ver"] != app["version"]:
                raise ValueError(f"{key}: gallery package/version differs")
            if app["package"] in packages:
                raise ValueError(f"{key}: unresolved package conflict")
            packages.add(app["package"])
            aliases = [alias["key"] for alias in shot.get("also_keys", [])]
            for alias in aliases:
                if metadata[alias]["package"] != app["package"]:
                    raise ValueError(f"{alias}: alias is not the same package")
            covered.extend([key] + aliases)
            rows.append((app, shot, partition, aliases))
    if len(covered) != len(set(covered)) or set(covered) != set(metadata):
        raise ValueError("gallery coverage duplicates or omits signed keys")
    return rows


def verify_signed_scope(metadata):
    sources = metadata["provenance"]
    for name in ("reference", "signoff"):
        if digest(expand(sources[name]["path"])) != sources[name]["sha256"]:
            raise ValueError(f"{name}: signed source SHA changed")
    reference = read_json(expand(sources["reference"]["path"]))["keys"]
    gains = read_json(expand(sources["signoff"]["path"]))["summary"]["gains"]
    expected = {key for key, value in reference.items() if value["verdict"] == "lit"} | set(gains)
    if {app["key"] for app in metadata["apps"]} != expected:
        raise ValueError("metadata differs from signed reference plus window1 gains")


def first_taps(expected_keys):
    if not FIRST_TAPS.is_file():
        return {}, {"status": "pending-oc-t4", "path": portable(FIRST_TAPS)}
    text = FIRST_TAPS.read_text()
    rows = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.startswith("| ") or line.startswith("| key"):
            continue
        fields = [field.strip() for field in line.split("|")[1:-1]]
        if len(fields) != 5:
            raise ValueError(f"first-tap table malformed at line {line_number}")
        key, entry, why, assessment, target = fields
        if key in rows or key not in expected_keys:
            raise ValueError(f"{key}: duplicate or unexpected first-tap key")
        likely = assessment.startswith(("能", "大概率能"))
        rows[key] = {"status": "offline-proposal-not-board-verified",
                     "assessment": "tap_likely" if likely else "tap_try_or_review",
                     "needs_first_tap": True,
                     "content_prediction": "likely-after-interaction" if likely else "unknown-after-interaction",
                     "source_entry": entry, "empty_screen_hypothesis": why,
                     "expected_content": assessment, "target": target,
                     "suggested_coordinates": [[int(axis) for axis in match]
                                               for match in re.findall(r"\((\d+),(\d+)\)", target)],
                     "coordinate_basis": "1200x1920 UI convention; NOT layout/hit-tested",
                     "coordinate_status": "unverified",
                     "requires_layout_confirmation": True, "interaction_verified": False,
                     "requires_more_than_tap": "输入" in assessment or "画一笔" in assessment,
                     "source_line": line_number}
    if set(rows) != expected_keys:
        raise ValueError("first-tap table omits empty/loading keys")
    source = {"status": "received-all-32-proposals", **pin(FIRST_TAPS),
              "source_commit": "a2030a6f2a", "rowwise_likely": sum(row["assessment"] == "tap_likely" for row in rows.values()),
              "rowwise_try_or_review": sum(row["assessment"] == "tap_try_or_review" for row in rows.values()),
              "warnings": ["Source header 24/5/3 groups overlap; rowwise 26 likely/6 uncertain used instead.",
                           "Source's all-fullscreen summary conflicts with per-row no-window notes; not adopted.",
                           "Proposed coordinates and successful-content hypotheses require actual layout/interaction review."]}
    return rows, source


def unlit_games():
    clusters = read_json(UNLIT / "clusters.json")["rows"]
    priors = read_json(UNLIT / "priors-29.json")["priors"]
    rows = []
    for key, (name, category) in UNLIT_GAME_KEYS.items():
        observation = clusters[key]
        prior = observation if observation.get("u14_observed") else priors.get(key)
        run = expand(prior["run"]) if prior and prior.get("run") else None
        record = read_json(run / "record.json") if run else {}
        fatal = None
        receipt = None
        if run:
            command = [sys.executable, str(MASTER / "scripts/lab/first_fatal.py"), str(run)]
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode:
                raise ValueError(f"{key}: first_fatal replay failed rc={process.returncode}")
            result = json.loads(process.stdout)
            terminal = result.get("terminal")
            root = result.get("root") or {}
            if terminal and terminal["kind"] != "process-disappeared":
                fatal = {"termination": terminal, "root_status": root.get("status"),
                         "root_event": root.get("event"), "frames": root.get("frames", [])[:6],
                         "report_source": (root.get("report") or {}).get("source")}
            receipt = {"terminal": terminal, "status": result["status"],
                       "source": result.get("source"), "limitations": result.get("limitations")}
        rows.append({"key": key, "name": name, "category": category, "install": False,
                     "package": record.get("package"), "apk_sha256": record.get("apk_sha256"),
                     "observation_version": "U14" if observation.get("u14_observed") else (prior or {}).get("version"),
                     "verdict": observation["verdict"], "u14_observed": observation.get("u14_observed", False),
                     "run": portable(run) if run else None,
                     "first_fatal": fatal, "analysis": receipt,
                     "status": "real-run-evidence" if fatal else "unknown-terminal-root",
                     "prior_label": (prior or {}).get("prior_label", (prior or {}).get("label"))})
    return rows


def build(output, identities_output, metadata_path=METADATA, gallery_path=GALLERY,
          package_reader=apk_package, include_unlit=True):
    metadata = read_json(metadata_path)
    gallery = read_json(gallery_path)
    if include_unlit:
        verify_signed_scope(metadata)
    selected = selection(metadata["apps"], gallery)
    taps, tap_source = first_taps({app["key"] for app, shot, partition, aliases in selected if partition == "minimal"}) if include_unlit else ({}, {})
    identities = {app["key"]: verify_identity(app, package_reader) for app in metadata["apps"]}
    rows = []
    for app, shot, partition, aliases in selected:
        key = app["key"]
        evidence_record = Path(shot["shot"]).parent / "record.json"
        record = read_json(evidence_record)
        if (record.get("key"), record.get("package"), record.get("apk_sha256")) != (
                key, app["package"], app["apk_sha256"]):
            raise ValueError(f"{key}: selected screenshot record identity differs")
        if digest(shot["shot"]) != record.get("screenshots", [{}])[-1].get("sha256"):
            screenshot_rows = [item for item in record.get("screenshots", [])
                               if Path(item["path"]).name == Path(shot["shot"]).name]
            if not any(item.get("sha256") == digest(shot["shot"]) for item in screenshot_rows):
                raise ValueError(f"{key}: screenshot SHA differs from run receipt")
        identity = identities[key]
        tap = taps.get(key)
        rows.append({"key": key, "package": app["package"], "version": app["version"],
                     "version_code": app["version_code"], "name_zh": app["display_name_zh"],
                     "category": app["category"], "purpose_zh": app["purpose_zh"],
                     "source": app["source"], "is_game": app["category"] == "游戏",
                     "install": True, "apk": identity["apk"], "apk_sha256": identity["apk_sha256"],
                     "input_root": "$WORKSPACES/westlake-inputs/corpus-v2/app-inputs" if key.startswith("cv2-") else "$HOME/a2hlab/app-inputs",
                     "apk_bytes": identity["apk_bytes"], "signed_keys": [key] + aliases,
                     "alias_selection": "gallery-selected-version; other signed versions not installed" if aliases else None,
                     "historical_content_status": partition, "counts_as_first_content": partition == "shown",
                     "needs_first_tap": tap["needs_first_tap"] if tap else (None if partition == "minimal" else False),
                     "first_tap": tap if tap else ({"status": "pending-oc-t4", "target": None, "expected_content": None}
                         if partition == "minimal" else None),
                     "error_note": shot.get("why") if partition == "errors" else None,
                     "evidence": {"signed_scope": app["signed_scope"], "signoff": app["signoff_path"],
                                  "source_record": identity["record"], "selected_record": pin(evidence_record),
                                  "selected_screenshot": pin(shot["shot"]), "run_tag": shot["src"]},
                     "native_sidecars": [{"name": sidecar["name"], "path": portable(sidecar["path"]),
                                          "sha256": sidecar["sha256"], "bytes": sidecar.get("bytes"),
                                          "abi": sidecar.get("abi")}
                                         for sidecar in record.get("native_sidecars", [])]})
    rows.sort(key=lambda row: (not row["counts_as_first_content"], not row["is_game"], row["category"], row["key"]))
    for order, row in enumerate(rows, 1):
        row["demo_order"] = order
    summary = {"signed_keys": len(identities), "distinct_packages": len(rows),
               "historical_first_content_packages": sum(row["counts_as_first_content"] for row in rows),
               "pending_first_tap_packages": sum(row["historical_content_status"] == "minimal" for row in rows),
               "error_screen_packages": sum(row["historical_content_status"] == "errors" for row in rows),
               "required_signed_games": sum(row["is_game"] for row in rows),
               "selected_apk_bytes": sum(row["apk_bytes"] for row in rows),
               "board_storage_estimate_apk_x3_bytes": 3 * sum(row["apk_bytes"] for row in rows),
               "first_content_target": 100, "target_verified_on_demo_board": False,
               "fresh_local_identity_keys_verified": len(identities)}
    summary.update(first_tap_assessed_packages=len(taps),
                   first_tap_likely_packages=sum(row["assessment"] == "tap_likely" for row in taps.values()),
                   first_tap_try_or_review_packages=sum(row["assessment"] == "tap_try_or_review" for row in taps.values()),
                   first_tap_interaction_verified_packages=0)
    board_evidence = MASTER / "benchmark/2026-10-09-demo-baseline/board-choice.md"
    board_choice = {"status": "selected-by-outer-not-sealed", "board": "61b0657200000000000000000324012c",
                    "evidence": pin(board_evidence), "owner": "cx-t0",
                    "outer_approval": "ACK(91) 2026-10-09T20:52+0800"} if board_evidence.is_file() else {"status": "pending-cx-t0", "board": None}
    toutiao = MASTER / "benchmark/2026-10-09-demo-toutiao/results.json"
    special = {"key": "toutiao", "status": "pending-t2", "owner": "cc-t3", "install": False}
    if toutiao.is_file():
        route = read_json(toutiao)["decision"]
        special.update(status="route-selected-coexistence-validation-pending", package="com.ss.android.article.news",
                       selected_route=route["primary"], acceptance_gates=route["gates_before_accept"], evidence=pin(toutiao))
    manifest = {"schema": "demo-baseline-manifest/v1", "state": "offline-inventory-interaction-unverified",
                "execution_enabled": False, "summary": summary,
                "provenance": {"contract_master_commit": "aa6c584bf2", "metadata": pin(metadata_path),
                               "gallery": pin(gallery_path), "signed_sources": portable_tree(metadata.get("provenance"))},
                "apps": rows, "signed_games": [row["key"] for row in rows if row["is_game"]],
                "unlit_games_and_tools": unlit_games() if include_unlit else [],
                "special_apps": [special,
                                 {"key": "boatattack", "status": "pending-t2b", "owner": "cc-wiki", "install": False}],
                "board_choice": board_choice, "first_tap_evidence": tap_source}
    validate(manifest)
    if taps:
        write_json(HERE / "first-tap-assessments.json", {"source": tap_source, "apps": taps})
        (HERE / "evidence/first-tap-candidates.md").write_bytes(FIRST_TAPS.read_bytes())
    write_json(identities_output, {"schema": "demo-apk-identity/v1", "checks": list(identities.values())})
    write_json(output, manifest)
    return manifest


def validate(manifest):
    rows = manifest["apps"]
    if len({row["package"] for row in rows}) != len(rows) or len(rows) < 100:
        raise ValueError("manifest needs at least 100 conflict-free packages")
    if any(not row["install"] or not row["apk_sha256"] for row in rows):
        raise ValueError("missing installation identity")
    if set(manifest["signed_games"]) != {row["key"] for row in rows if row["is_game"]}:
        raise ValueError("required signed games omitted")
    if any(row["historical_content_status"] != "shown" and row["counts_as_first_content"] for row in rows):
        raise ValueError("empty/error screen falsely counted as content")


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = stream.name
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "demo-manifest.json")
    parser.add_argument("--identities-output", type=Path, default=HERE / "identity-checks.json")
    args = parser.parse_args()
    try:
        result = build(args.output, args.identities_output)
    except (OSError, ValueError, KeyError) as error:
        print("REJECT: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
