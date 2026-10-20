#!/usr/bin/env python3
"""Offline exact T33 intake / T32 HAP verifier. Never issues device commands.

SHA parsing and bundle/runtime assertions follow T33 static/window_ops.py;
that module is deliberately not imported because its top level operates devices.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

REFERENCE = "benchmark/2026-10-20-t33-demo61b-host/static/reference.json"
REFERENCE_SHA = "c2ebf2f413132fc433b5bfed93b2c47fcc125a7dcec2a683c78366f5fb46913d"
HAP = "/data/app/el1/bundle/public/org.westlake.imehost/entry.hap"
PAGE = "ets/pages/Index.abc"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hashes(text):
    """Strict complete sha256sum records, as used by the original consumer."""
    result = {}
    for line in text.splitlines():
        fields = line.split()
        need(len(fields) == 2 and re.fullmatch("[0-9a-f]{64}", fields[0]),
             "malformed SHA record")
        need(fields[1] not in result, "duplicate SHA path")
        result[fields[1]] = fields[0]
    return result


def members(path):
    result = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = info.filename
            parts = PurePosixPath(name)
            need(not parts.is_absolute() and ".." not in parts.parts
                 and "\\" not in name and str(parts) == name,
                 "unsafe HAP member path")
            need(not info.is_dir() and name not in result, "duplicate/directory HAP member")
            need(info.file_size <= 16 * 1024 * 1024, "oversized HAP member")
            result[name] = digest(archive.read(info))
    return result


def verify(intake, release, reference):
    pins = {}

    def read(root, relative, label):
        path = root / relative
        need(path.is_file() and not path.is_symlink(), "missing/linked input: " + label)
        need(path.resolve().is_relative_to(root.resolve()), "input escapes root: " + label)
        data = path.read_bytes()
        pins[label] = {"sha256": digest(data), "bytes": len(data)}
        return data

    ref_bytes = reference.read_bytes()
    need(digest(ref_bytes) == REFERENCE_SHA, "unknown baseline reference")
    ref = json.loads(ref_bytes)
    pins["reference"] = {"sha256": digest(ref_bytes), "bytes": len(ref_bytes)}

    def receipt(name):
        label = "intake/" + name + "/"
        rc = read(intake, name + "/rc", label + "rc").decode().strip()
        need(rc == "0", "nonzero recorded rc: " + name)
        argv = json.loads(read(intake, name + "/argv.json", label + "argv.json"))
        need(isinstance(argv, list) and len(argv) >= 5
             and argv[1:4] == ["-t", ref["serial"], "shell"],
             "wrong recorded serial/transport: " + name)
        need(not read(intake, name + "/stderr", label + "stderr").strip(),
             "recorded stderr: " + name)
        return read(intake, name + "/stdout", label + "stdout").decode()

    bundle = json.loads(read(intake, "bundle.json", "intake/bundle.json"))
    need(isinstance(bundle, dict) and bundle.get("name") == "org.westlake.imehost",
         "unknown bundle")
    for key, expected in ref["bundle"].items():
        need(key in bundle and bundle[key] == expected, "bundle field missing/drift: " + key)
    application = bundle.get("applicationInfo")
    need(isinstance(application, dict), "bundle applicationInfo missing")
    token = application.get("accessTokenId")
    need(token == ref["accessTokenId"], "bundle accessTokenId missing/drift")
    raw_bundle = receipt("bundle")
    need(json.loads(raw_bundle[raw_bundle.index("{"):]) == bundle, "bundle/raw receipt mismatch")
    runtime = receipt("runtime-correct")
    need(runtime.splitlines().count("COMPAT_ABSENT") == 1, "compat absence missing/ambiguous")
    runtime_hashes = hashes("\n".join(x for x in runtime.splitlines() if x != "COMPAT_ABSENT"))
    need(runtime_hashes == ref["runtime"], "runtime baseline/path drift")
    controls = hashes(receipt("control-shas"))
    need(controls == ref["controls"], "guardian baseline/path drift")
    hap_raw = receipt("hap-sha")
    need(hashes(hap_raw.splitlines()[0]) == {HAP: ref["old_hap_sha256"]},
         "installed HAP path/hash drift")
    power = re.findall(r"ScreenOffTime:\s+Timeout=(\d+)ms\s+OverrideTimeout=(\d+)ms", hap_raw)
    need(len(power) == 1, "power fields missing/ambiguous")
    power = dict(zip(("timeout", "override"), map(int, power[0])))
    need(power == ref["power"], "power baseline drift")
    old = read(intake, "installed-entry.hap", "intake/installed-entry.hap")
    rollback = read(release, "rollback-exact.hap", "release/rollback-exact.hap")
    candidate = read(release, "candidate-signed.hap", "release/candidate-signed.hap")
    need(digest(old) == ref["old_hap_sha256"] and rollback == old, "wrong baseline/rollback HAP")
    old_members = members(intake / "installed-entry.hap")
    new_members = members(release / "candidate-signed.hap")
    need(old_members == ref["members"], "baseline HAP members drift")
    need(old_members.keys() == new_members.keys(), "extra/missing HAP member")
    changed = [name for name in old_members if old_members[name] != new_members[name]]
    need(changed == [PAGE], "HAP changes outside Index.abc")
    need(digest(candidate) == ref["candidate_hap_sha256"], "unknown exact T32 candidate")
    release_receipt = json.loads(read(release, "receipt.json", "release/receipt.json"))
    need(isinstance(release_receipt, dict)
         and release_receipt.get("old") == digest(old)
         and release_receipt.get("new") == digest(candidate), "release receipt drift")
    return {
        "status": "OFFLINE_EXACT_INPUTS_VERIFIED",
        "fresh_authorization": False, "deployment_verified": False, "device_calls": 0,
        "serial": ref["serial"], "bundle": {"name": bundle["name"], **ref["bundle"],
                                           "accessTokenId": token},
        "power": power, "runtime": runtime_hashes, "guardian": controls,
        "compat": "RECORDED_ABSENT_NOT_LIVE",
        "hap": {"baseline_sha256": digest(old), "candidate_sha256": digest(candidate),
                "changed_members": changed, "baseline_members": old_members,
                "candidate_members": new_members},
        "input_pins": pins,
        "limits": ["Local recorded evidence only; no present identity/holder/freshness claim",
                   "Exact signed bytes pinned; no independent signature cryptography performed"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", required=True, type=Path)
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--reference", type=Path,
                        default=Path(__file__).resolve().parents[2] / REFERENCE)
    args = parser.parse_args()
    try:
        result = verify(args.intake, args.release, args.reference)
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        # OSError paths may contain private roots; do not print them publicly.
        message = "input I/O failure" if isinstance(exc, OSError) else str(exc)
        print(json.dumps({"status": "REJECTED", "fresh_authorization": False}))
        print("host_hap_preflight: " + message, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
