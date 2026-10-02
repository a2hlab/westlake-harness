#!/usr/bin/env python3

import hashlib
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "policy" / "native_bridge_policy.v1.json"
HEADER = ROOT / "include" / "nativeloader" / "native_bridge_policy.h"


def header_array(text: str, name: str) -> list[str]:
    match = re.search(
        rf"{re.escape(name)}\s*=\s*\{{(?P<body>.*?)\}};", text, re.DOTALL
    )
    if match is None:
        raise ValueError(f"missing header array {name}")
    return re.findall(r'"([^"]+)"', match.group("body"))


def fail(message: str) -> None:
    print(f"bridge policy gate: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def canonical_absolute_path(value: object, *, trailing_slash: bool) -> bool:
    if not isinstance(value, str) or not value.startswith("/"):
        return False
    if value.endswith("/") != trailing_slash:
        return False
    body = value[1:-1] if trailing_slash else value[1:]
    if not body:
        return False
    return all(component not in {"", ".", ".."} for component in body.split("/"))


manifest_bytes = MANIFEST.read_bytes()
manifest = json.loads(manifest_bytes)
header = HEADER.read_text(encoding="utf-8")

if manifest.get("schema_version") != 1:
    fail("schema_version must be 1")
if manifest.get("architecture") != "arm64":
    fail("architecture must be arm64")
bootstrap = manifest.get("bridge_bootstrap_soname")
if bootstrap != "libwestlake_bionic_pthread_bridge.so" or \
        bootstrap not in header:
    fail("bridge bootstrap SONAME differs from checked-in header")

fields = {
    "bridge_search_paths": "kBridgeSearchPaths",
    "bridge_permitted_paths": "kBridgePermittedPaths",
    "system_caller_roots": "kSystemCallerRoots",
    "shared_sonames": "kBridgeSharedSonames",
}
for json_name, header_name in fields.items():
    values = manifest.get(json_name)
    if not isinstance(values, list) or not values:
        fail(f"{json_name} must be a non-empty list")
    if len(values) != len(set(values)):
        fail(f"{json_name} contains duplicates")
    if header_array(header, header_name) != values:
        fail(f"{json_name} differs from checked-in header {header_name}")

system_libraries = manifest.get("system_libraries")
if not isinstance(system_libraries, list) or not system_libraries:
    fail("system_libraries must be a non-empty list")
manifest_system_flat = []
system_sonames = set()
system_paths = set()
for item in system_libraries:
    if not isinstance(item, dict) or set(item) != {"soname", "path"}:
        fail("system_libraries entries require only soname and path")
    if item["soname"] in system_sonames:
        fail(f"duplicate system SONAME: {item['soname']}")
    if item["path"] in system_paths:
        fail(f"duplicate system provider path: {item['path']}")
    system_sonames.add(item["soname"])
    system_paths.add(item["path"])
    manifest_system_flat.extend([item["soname"], item["path"]])
if header_array(header, "kSystemLibraries") != manifest_system_flat:
    fail("system_libraries differs from checked-in header kSystemLibraries")

for path in manifest["bridge_search_paths"] + manifest["bridge_permitted_paths"]:
    if not canonical_absolute_path(path, trailing_slash=False) or path.startswith("/data/"):
        fail(f"untrusted bridge path: {path}")
for root in manifest["system_caller_roots"]:
    if not canonical_absolute_path(root, trailing_slash=True) or root.startswith("/data/"):
        fail(f"untrusted system caller root: {root}")
for item in system_libraries:
    if "/" in item["soname"] or not item["soname"].endswith(".so"):
        fail(f"invalid system SONAME: {item['soname']}")
    if not canonical_absolute_path(item["path"], trailing_slash=False):
        fail(f"system library path is not canonical: {item['path']}")
    if item["path"] != f"/system/android/lib64/{item['soname']}":
        fail(f"system library path is not exact: {item['path']}")
for soname in manifest["shared_sonames"]:
    if "/" in soname or ".." in soname or not soname.endswith(".so"):
        fail(f"invalid bridge SONAME: {soname}")
    if soname in {"libc.so", "libm.so", "libdl.so"}:
        fail(f"loader reserved-self SONAME must not become a bridge edge: {soname}")

digest = hashlib.sha256(manifest_bytes).hexdigest()
print(f"NativeLoader bridge policy: PASS sha256={digest}")
