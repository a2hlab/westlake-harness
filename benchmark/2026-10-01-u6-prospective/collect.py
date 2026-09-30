"""Offline U6-T7c/J7b evidence collection. Never edits original inputs."""

import argparse
import concurrent.futures
import copy
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "benchmark/2026-09-29-static-wall-prediction"))
from scan_u5_feedback import collect_app, file_digest, write_json
from rules_u5_feedback import app_requirements, input_findings

MERGED = {"burgerking", "firefox", "mcdonalds", "subwaysurfers", "x"}
REPAIRED = {"fd-seal", "toutiao"}


def collect_merged(key, old, args):
    apk = args.merged_root / (key + "-signed.apk")
    sha = file_digest(apk)
    badging = subprocess.run([str(args.aapt2), "dump", "badging", str(apk)], check=True, capture_output=True, text=True).stdout
    package = re.search(r"package: name='([^']+)'", badging)[1]
    if package != (old["entry"]["package"] or old["metadata_package"]):
        raise ValueError("Merged package mismatch: " + key)
    if "split='" in badging.splitlines()[0]:
        raise ValueError("Selected APK is still a split: " + key)
    with tempfile.TemporaryDirectory(prefix="u6-input-") as temp:
        root = Path(temp)
        directory = root / key
        directory.mkdir()
        (directory / "merged.apk").symlink_to(apk.resolve())
        write_json(directory / "app-input.json", dict(apk_sha256=sha, application=dict(package=package)))
        with zipfile.ZipFile(apk) as archive:
            for name in archive.namelist():
                if re.fullmatch(r"lib/arm64-v8a/[^/]+\.so", name):
                    path = directory / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.read(name))
        facts = collect_app(dict(key=key, package=package, apk_sha256=sha), root, args.dexdump)
    activity = re.search(r"launchable-activity: name='([^']+)'", badging)
    facts["entry"]["launch_activity"] = activity[1] if activity else None
    facts["input_origin"] = "merged-APK-native-members; synthetic metadata for scan only, not deployment readiness"
    facts["source_apk"] = "t4-split-merge/" + apk.name
    facts["old_apk_sha256"] = old["selected_apk"]["sha256"]
    facts["scan_mode"] = "fresh-all-dex-and-embedded-native"
    (HERE / "evidence" / (key + "-badging.txt")).write_text(badging)
    return facts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged-root", type=Path, required=True)
    parser.add_argument("--repaired-input-root", type=Path, required=True)
    parser.add_argument("--original-input-root", type=Path, default=Path.home() / "a2hlab/app-inputs")
    parser.add_argument("--boot-stage", type=Path, required=True)
    parser.add_argument("--j7b", type=Path, required=True)
    parser.add_argument("--j6", type=Path, required=True)
    parser.add_argument("--reuse-merged", action="store_true")
    parser.add_argument("--dexdump", type=Path, default=Path.home() / "Library/Android/sdk/build-tools/37.0.0/dexdump")
    parser.add_argument("--aapt2", type=Path, default=Path.home() / "Library/Android/sdk/build-tools/37.0.0/aapt2")
    args = parser.parse_args()
    if (HERE / "FREEZE.json").exists():
        raise ValueError("U6 version already frozen; collect into a new version, not this directory")
    (HERE / "evidence").mkdir(parents=True, exist_ok=True)
    prior = ROOT / "benchmark/2026-10-01-u5-feedback-v1/static-facts.json"
    document = json.loads(prior.read_text())
    source = {row["entry"]["key"]: row for row in document["apps"]}
    facts = {}
    if args.reuse_merged:
        saved = json.loads((HERE / "input-facts.json").read_text())
        for row in saved["apps"]:
            key = row["entry"]["key"]
            if key in MERGED:
                if file_digest(args.merged_root / (key + "-signed.apk")) != row["selected_apk"]["sha256"]:
                    raise ValueError("Merged APK changed: " + key)
                badging = (HERE / "evidence" / (key + "-badging.txt")).read_text()
                activity = re.search(r"launchable-activity: name='([^']+)'", badging)
                row["entry"]["launch_activity"] = activity[1] if activity else None
                facts[key] = row
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            jobs = {key: executor.submit(collect_merged, key, source[key], args) for key in sorted(MERGED)}
            for key, job in jobs.items():
                facts[key] = job.result()
    for key, old in source.items():
        if key in MERGED:
            continue
        if key in REPAIRED:
            facts[key] = collect_app(old["entry"], args.repaired_input_root, args.dexdump)
            facts[key]["scan_mode"] = "fresh-repaired-sidecars-and-all-dex"
        else:
            directory = args.original_input_root / key
            for row in old["apks"] + old["sidecars"]:
                if file_digest(directory / row["path"]) != row["sha256"]:
                    raise ValueError("Unchanged input drift: " + key + "/" + row["path"])
            if file_digest(directory / "app-input.json") != old["metadata_sha256"]:
                raise ValueError("Metadata drift: " + key)
            facts[key] = copy.deepcopy(old)
            facts[key]["scan_mode"] = "sha-revalidated-unchanged-u5-static-facts"
        input_root = args.repaired_input_root if key in REPAIRED else args.original_input_root
        metadata = json.loads((input_root / key / "app-input.json").read_text())
        facts[key]["entry"]["launch_activity"] = metadata["application"].get("launch_activity")
        facts[key]["declared_sidecars"] = sorted(metadata.get("native_libraries", {}))
        facts[key]["metadata_inventory_matches"] = set(facts[key]["declared_sidecars"]) == {row["path"] for row in facts[key]["sidecars"]}
    for row in facts.values():
        row["entry"]["package"] = row["entry"]["package"] or row["metadata_package"]
        row["entry"]["apk_sha256"] = row["selected_apk"]["sha256"]
        row["input_findings"] = input_findings(row)
        row["native_and_dex_requirements"] = app_requirements(row, document["profile"])
    files = [args.boot_stage / "adapter-mainline-stubs.jar", *sorted((args.boot_stage / "arm64").glob("*"))]
    files = [path for path in files if path.is_file() and path.suffix in {".art", ".oat", ".vdex", ".jar"}]
    if len(files) != 28:
        raise ValueError("Expected exactly 27 image files plus stubs jar")
    candidate = dict(version="u6-t7c-j7b-v1", recorded_at=datetime.now(timezone.utc).isoformat(),
                     boot_variant="T7c", t7d="not-in-this-freeze; any T7d rollout requires a new version",
                     native_generation=document["profile"],
                     j7b_sha256=file_digest(args.j7b), j6_sha256=file_digest(args.j6),
                     boot_files={str(path.relative_to(args.boot_stage)): file_digest(path) for path in files},
                     original_facts_sha256=file_digest(prior),
                     tools=dict(dexdump=file_digest(args.dexdump), aapt2=file_digest(args.aapt2)))
    if candidate["j7b_sha256"] != "381110a675fb543b6ad4102c8fc721fcb5673bc0da8644ececd1bab1ca60bec8":
        raise ValueError("J7b identity mismatch")
    write_json(HERE / "candidate.json", candidate)
    write_json(HERE / "input-facts.json", dict(candidate="u6-t7c-j7b-v1", apps=[facts[key] for key in sorted(facts)]))
    write_json(HERE / "apps-u6.json", dict(schema="bms-batch-apps-v1", input_plan_only=True,
               note="Merged keys require staging the pinned APK and exactly these native members into a new input root; synthetic scan metadata is not an installer receipt",
               apps=[dict(**facts[key]["entry"], **({"native_sidecar_count": len(facts[key]["sidecars"])} if facts[key]["sidecars"] else {})) for key in sorted(facts)]))


if __name__ == "__main__":
    main()
