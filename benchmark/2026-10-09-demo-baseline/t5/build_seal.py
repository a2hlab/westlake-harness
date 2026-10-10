import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
SERIAL = "61b0657200000000000000000324012c"
SHA = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*\Z")
PATH = re.compile(r"/[A-Za-z0-9_./:+@-]+\Z")
PATTERN = re.compile(r"/[A-Za-z0-9_./:+@*?-]+\Z")


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def board_path(value, pattern=False):
    require(isinstance(value, str) and bool((PATTERN if pattern else PATH).fullmatch(value)) and
            ".." not in value.split("/"), "unsafe board path: " + str(value))
    return value


def file_map(value):
    require(isinstance(value, dict), "file map required")
    for path, sha in value.items():
        board_path(path)
        require(isinstance(sha, str) and bool(SHA.fullmatch(sha)), "invalid SHA: " + path)
    return dict(sorted(value.items()))


def fingerprint(lines, expected):
    require(isinstance(lines, list) and bool(lines), "raw fingerprint lines required")
    found = {}
    normalized = []
    for line in lines:
        require(isinstance(line, str), "invalid fingerprint line")
        match = re.fullmatch(r"([0-9a-f]{64})\s+(/\S+)", line.strip())
        require(match is not None, "invalid fingerprint line")
        sha, path = match.groups()
        require(path not in found, "duplicate fingerprint path")
        found[path] = sha
        normalized.append(line.strip())
    require(found == expected, "fingerprint membership/SHA differs from effective file group")
    return hash_bytes("\n".join(sorted(normalized)).encode())[:12]


def overlay_check(document):
    require(document.get("schema") == "demo-overlays/v1", "overlay schema required")
    stage = document.get("seal_stage")
    require(stage in {"v1", "v2"}, "explicit v1/v2 seal_stage required")
    rows = document.get("items")
    require(isinstance(rows, list) and {row.get("id") for row in rows} == {"toutiao-route-b", "boatattack"}
            and len(rows) == 2, "exactly two named overlay slots required")
    active = {}
    packages = []
    for row in rows:
        if row["id"] == "boatattack":
            require(row.get("state") == ("absent" if stage == "v1" else "active"),
                    "BoatAttack must be absent in v1 and an admitted overlay in v2")
        require(row.get("state") in {"active", "absent"}, "unresolved overlay slot: " + row["id"])
        if row["id"] == "toutiao-route-b":
            require(row["state"] == "active", "v1/v2 require an active Toutiao Route B overlay")
        if row["state"] == "absent":
            require(not row.get("files") and bool(row.get("reason")), "absent overlay needs reason and no files")
            continue
        require(NAME.fullmatch(str(row.get("package", ""))) is not None, "active overlay package required")
        require(SHA.fullmatch(str(row.get("apk_sha256", ""))) is not None and
                type(row.get("version_code")) in {str, int} and str(row["version_code"]).isdigit() and
                isinstance(row.get("version_name"), str) and bool(row["version_name"]), "active overlay APK/version identity required")
        for field in ("source", "rollback"):
            pin = row.get(field, {})
            require(bool(pin.get("path")) and SHA.fullmatch(str(pin.get("sha256", ""))) is not None,
                    "active overlay requires pinned " + field)
        members = row.get("files")
        require(isinstance(members, list) and bool(members), "active overlay files required")
        roles = [member.get("role") for member in members]
        if row["id"] == "boatattack":
            admission = row.get("admission", {})
            require(bool(admission.get("path")) and SHA.fullmatch(str(admission.get("sha256", ""))) is not None,
                    "v2 BoatAttack requires a pinned admission defining the accepted overlay")
            require(all(isinstance(role, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", role) for role in roles),
                    "v2 BoatAttack member roles must be explicit")
        else:
            require(row.get("route") == "B" and all(role == "ttbundle" for role in roles),
                    "Toutiao requires explicit Route B ttbundle members")
            require(row.get("launch_kind") == "embedded-in-hap" and row.get("host_package") == "org.westlake.imehost",
                    "Route B is embedded in the imehost HAP, not an Android BMS launch")
            payload = board_path(row.get("payload_path"))
            require(any(member["target"] == payload and member.get("sha256") == row["apk_sha256"] for member in members),
                    "Route B embedded APK must be a hashed ttbundle member")
        for member in members:
            path = board_path(member["target"])
            sha = member.get("sha256")
            require(SHA.fullmatch(str(sha)) is not None, "overlay member SHA required")
            require(path not in active, "duplicate overlay target")
            active[path] = sha
        packages.append(row["host_package"] if row["id"] == "toutiao-route-b" else row["package"])
    return dict(sorted(active.items())), packages


def build(snapshot, overlays, manifest):
    require(snapshot.get("schema") == "demo-seal-snapshot/v1", "snapshot schema required")
    require(snapshot.get("serial") == SERIAL, "wrong demo serial")
    require(snapshot.get("mode") == "live-readonly", "only explicitly live-readonly snapshot can be sealed")
    require(snapshot.get("remote_write_operations") == 0 and snapshot.get("lock_operations") == 0,
            "snapshot must be read-only with zero lock operations")
    require(snapshot.get("errors") == [], "snapshot read errors or missing errors field")
    require(snapshot.get("file_inventory_complete") is True, "effective file inventory must be complete")
    boot = snapshot.get("boot_before")
    require(bool(boot) and boot == snapshot.get("boot_after"), "snapshot crosses boot or lacks boot ID")
    stamp = datetime.fromisoformat(snapshot["captured_at"])
    require(stamp.tzinfo is not None, "capture time must include timezone")
    groups = snapshot.get("files")
    require(isinstance(groups, dict) and set(groups) == {"runtime", "boot", "overlays", "installation"},
            "four complete file groups required")
    files = {group: file_map(members) for group, members in groups.items()}
    require(all(files[group] for group in ("runtime", "boot", "installation")), "nonempty baseline groups required")
    all_files = {}
    for members in files.values():
        for path, sha in members.items():
            require(path not in all_files or all_files[path] == sha, "conflicting effective SHA: " + path)
            all_files[path] = sha
    overlay_files, overlay_packages = overlay_check(overlays)
    require(files["overlays"] == overlay_files, "overlay declaration differs from observed effective bytes")
    fingerprints = {group: fingerprint(snapshot.get("fingerprint_lines", {}).get(group), files[group])
                    for group in ("runtime", "boot")}
    if "expected_fingerprints" in snapshot:
        require(snapshot["expected_fingerprints"] == fingerprints, "short fingerprint assertion differs")
    system = snapshot.get("system_params")
    require(isinstance(system, dict) and bool(system.get("const.ohos.fullname")), "system version required")
    require(all(NAME.fullmatch(str(key)) and isinstance(value, str) and bool(value) for key, value in system.items()),
            "invalid system parameters")
    packages, seen, apk_paths = [], set(), set()
    for row in snapshot.get("packages", []):
        name = row.get("package")
        require(NAME.fullmatch(str(name)) is not None and name not in seen, "invalid or duplicate installed package")
        seen.add(name)
        code = row.get("version_code")
        require(type(code) in {str, int} and str(code).isdigit(), "invalid installed version code")
        require(isinstance(row.get("version_name"), str) and bool(row["version_name"]), "installed version name required")
        path = board_path(row.get("apk_path"))
        require(path not in apk_paths, "shared installed APK path")
        apk_paths.add(path)
        require(SHA.fullmatch(str(row.get("apk_sha256", ""))) is not None, "installed APK SHA required")
        require(snapshot.get("apk_hashes", {}).get(path) == row["apk_sha256"], "observed installed APK SHA differs")
        packages.append({field: row[field] for field in ("package", "version_code", "version_name", "apk_path", "apk_sha256")})
    require(bool(packages), "installed package list required")
    indexed = {row["package"]: row for row in packages}
    for app in manifest["apps"]:
        if not app.get("install", True):
            continue
        actual = indexed.get(app["package"])
        require(actual is not None and actual["apk_sha256"] == app["apk_sha256"] and
                str(actual["version_code"]) == str(app["version_code"]) and actual["version_name"] == app["version"],
                "manifest package identity not installed: " + app["key"])
    require(all(name in indexed for name in overlay_packages), "active overlay app is not installed")
    for overlay in overlays["items"]:
        if overlay["state"] == "active" and overlay["id"] != "toutiao-route-b":
            actual = indexed[overlay["package"]]
            require(actual["apk_sha256"] == overlay["apk_sha256"] and
                    str(actual["version_code"]) == str(overlay["version_code"]) and actual["version_name"] == overlay["version_name"],
                    "active overlay APK/version differs from installed package")
    require(snapshot.get("package_inventory_complete") is True, "installed package inventory must be complete")
    inventories = snapshot.get("inventories", [])
    require(isinstance(inventories, list), "inventories must be a list")
    for inventory in inventories:
        patterns, paths = inventory.get("patterns"), inventory.get("paths")
        require(isinstance(patterns, list) and bool(patterns) and isinstance(paths, list) and bool(paths), "invalid inventory")
        require(len(paths) == len(set(paths)), "duplicate inventory member")
        for pattern in patterns:
            board_path(pattern, True)
        require(all(board_path(path) in all_files for path in paths), "inventory path not sealed")
    return {"schema": "demo-seal/v1", "seal_stage": overlays["seal_stage"], "serial": SERIAL, "files": files,
            "system_params": dict(sorted(system.items())), "packages": sorted(packages, key=lambda row: row["package"]),
            "inventories": inventories, "fingerprints": fingerprints, "overlay_deployments": overlays["items"],
            "provenance": {"captured_at": snapshot["captured_at"], "capture_boot_id": boot,
                           "package_inventory_complete": True, "live_verification": "pending-demo_selfcheck",
                           "remote_write_operations": 0, "lock_operations": 0}}


def main():
    parser = argparse.ArgumentParser(description="Offline snapshot-to-demo_selfcheck seal compiler; never contacts a board")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--overlays", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        require(not args.out.exists(), "fresh output required")
        seal = build(read_json(args.snapshot), read_json(args.overlays), read_json(args.manifest))
        seal["provenance"]["input_sha256"] = {name: hash_bytes(path.read_bytes())
                                             for name, path in (("snapshot", args.snapshot), ("overlays", args.overlays), ("manifest", args.manifest))}
        args.out.write_text(json.dumps(seal, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        print(json.dumps({"status": "SEAL_COMPILED_OFFLINE", "sha256": hash_bytes(args.out.read_bytes()),
                          "fingerprints": seal["fingerprints"], "packages": len(seal["packages"])}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print("REJECT " + str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
