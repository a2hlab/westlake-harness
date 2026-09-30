"""Read actual U7 inputs and candidate bytes; emit evidence without mutating sources."""

import argparse
import concurrent.futures
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
U6 = ROOT / "benchmark/2026-10-01-u6-prospective"
sys.path.insert(0, str(ROOT / "benchmark/2026-09-29-static-wall-prediction"))
from scan_u5_feedback import collect_app, file_digest
from rules_u5_feedback import app_requirements, input_findings

FRESH = {"burgerking", "firefox", "mcdonalds", "subwaysurfers", "x", "fd-seal", "toutiao"}
STUBS_SHA = "d8b2406eb89d2947a8cb313a471d4858ff6be86018ece3bb5c2068a11b42ca2c"


def read(path):
    return json.loads(path.read_text())


def inventory(path):
    result = {}
    for line in path.read_text().splitlines():
        digest, name = line.split()
        if name in result or len(digest) != 64:
            raise ValueError("bad inventory")
        result[name] = digest
    return result


def physical_directory(root, key, mount):
    directory = root / key
    if directory.is_symlink():
        target = Path(os.readlink(directory))
        if not target.is_absolute():
            return (directory.parent / target).resolve(), str(target)
        if not mount:
            return target, str(target)
        return mount / str(target).lstrip("/"), str(target)
    return directory, None


def collect_input(entry, args, batch, old, profile):
    key = entry["key"]
    directory, link = physical_directory(args.input_root, key, args.vm_mount)
    metadata = read(directory / "app-input.json")
    pinned = {name: entry[name] for name in ["key", "package", "apk_sha256", "launch_activity"] if name in entry}
    resolved = batch.resolve_input(directory.parent, pinned)
    badging = None
    if key in FRESH - {"fd-seal", "toutiao"}:
        badging = subprocess.run([str(args.aapt2), "dump", "badging", resolved["apk"]],
                                 check=True, capture_output=True, text=True).stdout
        if "split='" in badging.splitlines()[0] or re.search(r"package: name='([^']+)'", badging)[1] != pinned["package"]:
            raise ValueError("selected merged APK is split or wrong package: " + key)
    if key in FRESH:
        facts = collect_app(pinned, directory.parent, args.dexdump)
        mode = "fresh-all-dex-and-native"
    else:
        facts = copy.deepcopy(old[key])
        for item in facts["apks"] + facts["sidecars"]:
            if file_digest(directory / item["path"]) != item["sha256"]:
                raise ValueError("prior static bytes changed: " + key + "/" + item["path"])
        if file_digest(directory / "app-input.json") != facts["metadata_sha256"]:
            raise ValueError("prior metadata changed: " + key)
        mode = "all-input-bytes-rehashed-static-facts-reused"
    facts["entry"] = pinned
    facts["declared_sidecars"] = sorted(metadata.get("native_libraries", {}))
    facts["metadata_inventory_matches"] = set(facts["declared_sidecars"]) == {item["path"] for item in facts["sidecars"]}
    facts["input_findings"] = input_findings(facts)
    facts["native_and_dex_requirements"] = app_requirements(facts, profile)
    if facts["scan_errors"] or facts["input_findings"]:
        raise ValueError("input/static scan rejected: " + key + " " + str(facts["scan_errors"] + facts["input_findings"]))
    sidecars = {"lib/" + item["abi"] + "/" + item["name"]: item["sha256"] for item in resolved["native_sidecars"]}
    if sidecars != {item["path"]: item["sha256"] for item in facts["sidecars"]}:
        raise ValueError("resolver/static inventory disagreement: " + key)
    receipt = dict(key=key, package=resolved["package"], apk_sha256=resolved["apk_sha256"],
                   metadata_sha256=resolved["input_sha256"], launch_activity=resolved["launch_activity"],
                   sidecars=sidecars, split_hint=resolved["split_hint"], resolved=True,
                   selected_apk=Path(resolved["apk"]).name, source_symlink=link,
                   source_directory="VM_INPUT_ROOT/" + key, scan_mode=mode,
                   merged_manifest_badging=[line for line in (badging or "").splitlines()
                                            if line.startswith(("package:", "launchable-activity:", "native-code:", "uses-split:"))],
                   merged_manifest_badging_sha256=hashlib.sha256(badging.encode()).hexdigest() if badging else None,
                   split_hint_note="Historical metadata hint only; selected APK badging has no split and physical directory has one APK" if resolved["split_hint"] and badging else None)
    print("resolved " + key + " sidecars=" + str(len(sidecars)), file=sys.stderr, flush=True)
    return receipt, facts


def collect(args):
    spec = importlib.util.spec_from_file_location("u7_batch_resolver", args.batch_script)
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    prior = read(U6 / "input-facts.json")
    old = {item["entry"]["key"]: item for item in prior["apps"]}
    expected = read(U6 / "expected-run.json")
    profile = read(U6 / "candidate.json")["native_generation"]
    entries = read(U6 / "apps-u6.json")["apps"]
    with contextlib.redirect_stdout(sys.stderr), concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda entry: collect_input(entry, args, batch, old, profile), entries))
    actual = dict(expected["boot_files"])
    files = [args.boot_stage / "adapter-mainline-stubs.jar", *sorted((args.boot_stage / "arm64").glob("*"))]
    files = [path for path in files if path.suffix in {".jar", ".art", ".oat", ".vdex"}]
    if len(files) != 28 or file_digest(files[0]) != STUBS_SHA:
        raise ValueError("not the accepted full-tagsoup T7d package")
    replacements = {"/system/android/framework/" + str(path.relative_to(args.boot_stage)): file_digest(path) for path in files}
    actual.update(replacements)
    component = inventory(args.component_boot)
    if actual != component:
        raise ValueError("T7d stage differs from the component-tested boot inventory")
    runtime = dict(expected["runtime_files"])
    if file_digest(args.runtime_jar) != runtime["/system/android/framework/oh-adapter-runtime.jar"]:
        raise ValueError("J7b jar changed")
    candidate = dict(version="u7-t7d-j7b-n4order-v1", composition="U6 + T7d; native U5 N4-order; no N6/N7/N8",
                     stubs_sha256=STUBS_SHA, runtime_files=runtime, boot_files=actual, replacements=replacements,
                     native_generation=profile, j7b_sha256=file_digest(args.runtime_jar),
                     component_boot_sha256=file_digest(args.component_boot),
                     source_paths=dict(boot_stage="WORKSPACES/_hw248-t7d", runtime_jar="WORKSPACES/_u6-stage/oh-adapter-runtime.jar"))
    return dict(candidate=candidate, input_facts=dict(apps=[item[1] for item in results]),
                inputs=dict(recorded_at=datetime.now(timezone.utc).isoformat(),
                            input_root="VM:$HOME/a2hlab/app-inputs-u6", access="read-only mounted VM view; absolute per-key symlinks translated through --vm-mount",
                            batch_script_sha256=file_digest(args.batch_script), dexdump_sha256=file_digest(args.dexdump),
                            u6_input_facts_sha256=file_digest(U6 / "input-facts.json"),
                            apps=[item[0] for item in results]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--vm-mount", type=Path)
    parser.add_argument("--batch-script", type=Path, required=True)
    parser.add_argument("--boot-stage", type=Path, required=True)
    parser.add_argument("--component-boot", type=Path, required=True)
    parser.add_argument("--runtime-jar", type=Path, required=True)
    parser.add_argument("--dexdump", type=Path, default=Path.home() / "Library/Android/sdk/build-tools/37.0.0/dexdump")
    parser.add_argument("--aapt2", type=Path, default=Path.home() / "Library/Android/sdk/build-tools/37.0.0/aapt2")
    args = parser.parse_args()
    if (HERE / "FREEZE.json").exists():
        raise ValueError("already frozen; use a new version")
    print(json.dumps(collect(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
