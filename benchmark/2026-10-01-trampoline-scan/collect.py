"""Read exact frozen APKs locally and retain manifest/smali-style evidence."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

import rules


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / "benchmark/2026-10-01-u7-prospective/v1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def physical(root, key, mount):
    path = root / key
    if path.is_symlink():
        target = Path(os.readlink(path))
        return mount / str(target).lstrip("/") if target.is_absolute() else (path.parent / target).resolve()
    return path


def collect_app(entry, args):
    directory = physical(args.input_root, entry["key"], args.vm_mount)
    apk = directory / entry["selected_apk"]
    payload = apk.read_bytes()
    if sha(payload) != entry["apk_sha256"]:
        raise ValueError("frozen APK drift: " + entry["key"])
    manifest_text = subprocess.run([str(args.aapt2), "dump", "xmltree", str(apk), "--file", "AndroidManifest.xml"], check=True, capture_output=True, text=True).stdout
    manifest = rules.manifest(manifest_text)
    if manifest["package"] != entry["package"]:
        raise ValueError("package mismatch")
    classes, methods, inventory = {}, {}, []
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix="trampoline-dex-") as temporary:
        for name in sorted(archive.namelist()):
            if not re.fullmatch(r"classes(?:[2-9]|[1-9][0-9]+)?\.dex", name):
                continue
            data = archive.read(name)
            digest = sha(data)
            path = Path(temporary) / name
            path.write_bytes(data)
            with tempfile.TemporaryFile() as errors:
                process = subprocess.Popen([str(args.dexdump), "-d", str(path)], stdout=subprocess.PIPE, stderr=errors, text=True, errors="replace")
                try:
                    defined, code = rules.parse_dex(process.stdout, name, digest)
                finally:
                    process.stdout.close()
                    process.wait()
                if process.returncode:
                    raise ValueError("dexdump failed: " + entry["key"] + "/" + name)
            if set(classes) & set(defined):
                raise ValueError("duplicate class across DEX")
            classes.update(defined)
            methods.update(code)
            inventory.append(dict(name=name, sha256=digest, bytes=len(data)))
    launches = [dict(launcher=launcher, analysis=rules.inspect_activity(launcher["target"], classes, methods)) for launcher in manifest["launchers"] if launcher["enabled"]]
    runner = entry.get("launch_activity")
    override = rules.inspect_activity(runner, classes, methods) if runner and runner not in {row["launcher"]["target"] for row in launches} else None
    visited = {identifier for row in launches for identifier in row["analysis"]["methods"]}
    if override:
        visited.update(override["methods"])
    global_starts = [dict(method=method["id"], dex=method["dex"], call=call) for method in methods.values() for call in method["calls"] if call["name"] in rules.STARTS]
    unvisited = [row for row in global_starts if row["method"] not in visited]
    retained_ids = set(visited)
    for identifier in visited:
        for call in methods[identifier]["calls"]:
            target = rules.resolve(call["owner"], call["name"], call["descriptor"], classes, methods)
            if target:
                retained_ids.add(target)
    retained = {identifier: methods[identifier] for identifier in sorted(retained_ids)}
    owners = {owner for row in launches for owner in row["analysis"].get("hierarchy", [])}
    if override:
        owners.update(override.get("hierarchy", []))
    for method in retained.values():
        for call in method["calls"]:
            owners.update(rules.hierarchy(call["owner"], classes))
    return dict(key=entry["key"], package=entry["package"], apk=entry["selected_apk"], apk_sha256=entry["apk_sha256"],
                manifest_sha256=sha(manifest_text.encode()), manifest_text=manifest_text, manifest=manifest,
                dex=inventory, class_count=len(classes), method_count=len(methods),
                launchers=launches, runner_activity=runner, runner_override=override,
                retained_methods=retained, class_hierarchy={owner: classes[owner] for owner in sorted(owners) if owner in classes},
                unrelated_or_callback_start_sites=len(unvisited), unrelated_or_callback_examples=unvisited[:8],
                metadata_sha256=sha((directory / "app-input.json").read_bytes()), input_scope="APK pinned to U7; native payload/quarantine changes do not alter launcher bytecode")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--vm-mount", type=Path, required=True)
    parser.add_argument("--aapt2", type=Path, default=Path.home() / "Library/Android/sdk/build-tools/37.0.0/aapt2")
    parser.add_argument("--dexdump", type=Path, default=Path.home() / "Library/Android/sdk/build-tools/37.0.0/dexdump")
    parser.add_argument("--keys", nargs="*")
    args = parser.parse_args()
    entries = json.loads((FROZEN / "inputs.json").read_text())["apps"]
    if args.keys:
        entries = [entry for entry in entries if entry["key"] in args.keys]
    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = list(executor.map(lambda entry: collect_app(entry, args), entries))
    print(json.dumps(dict(schema_version=1, rule_scope="static conditional prediction, not board execution", frozen_inputs_sha256=sha((FROZEN / "inputs.json").read_bytes()),
                          tool_sha256=dict(aapt2=sha(args.aapt2.read_bytes()), dexdump=sha(args.dexdump.read_bytes())), rows=rows), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
