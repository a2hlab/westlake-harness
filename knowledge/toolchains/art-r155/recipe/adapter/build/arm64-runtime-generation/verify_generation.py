#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(tool, *args):
    return subprocess.check_output([str(tool), *map(str, args)], text=True,
                                   errors="replace")


def inspect(readelf, path):
    header = run(readelf, "--file-header", "--wide", path)
    dynamic = run(readelf, "--dynamic", "--wide", path)
    notes = run(readelf, "--notes", "--wide", path)
    if "ELF64" not in header or "AArch64" not in header:
        raise SystemExit(f"not ELF64/AArch64: {path}")
    if re.search(r"\((?:RPATH|RUNPATH|TEXTREL)\)", dynamic):
        raise SystemExit(f"unsafe dynamic tag: {path}")
    sonames = re.findall(r"\(SONAME\).*?\[([^]]+)\]", dynamic)
    needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic)
    build_ids = re.findall(r"Build ID:\s*([0-9a-fA-F]+)", notes)
    if len(sonames) != 1 or len(build_ids) != 1:
        raise SystemExit(f"missing/ambiguous SONAME or Build-ID: {path}")
    segments = run(readelf, "--program-headers", "--wide", path)
    return {"sha256": sha(path), "soname": sonames[0],
            "build_id": build_ids[0].lower(), "needed": needed,
            "pt_tls": bool(re.search(r"^\s*TLS\s", segments, re.M))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--frozen", required=True, type=pathlib.Path)
    parser.add_argument("--build-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    frozen = args.frozen.resolve()
    root = args.build_root.resolve()
    readelf = frozen / "toolchain/bin/llvm-readelf"
    roots = {
        "adapter_bridge": ("payload/adapter/liboh_adapter_bridge.so",
                           "/system/lib64/liboh_adapter_bridge.so",
                           "liboh_adapter_bridge.so"),
        "android_runtime": ("payload/adapter/liboh_android_runtime.so",
                            "/system/android/lib64/liboh_android_runtime.so",
                            "liboh_android_runtime.so"),
        "app_native_loader": ("payload/adapter/libapp_native_loader.so",
                              "/system/android/lib64/libapp_native_loader.so",
                              "libapp_native_loader.so"),
        "native_loader": ("payload/aosp/libnativeloader.so",
                          "/system/android/lib64/libnativeloader.so",
                          "libnativeloader.so"),
    }
    artifacts = {}
    for role, (relative, deploy, expected_soname) in roots.items():
        first = root / "pass1" / relative
        second = root / "pass2" / relative
        if first.read_bytes() != second.read_bytes():
            raise SystemExit(f"non-deterministic artifact: {role}")
        info = inspect(readelf, first)
        if info["soname"] != expected_soname:
            raise SystemExit(f"wrong SONAME for {role}: {info['soname']}")
        info.update(path=relative, deploy_path=deploy)
        artifacts[role] = info

    required_edges = {
        "android_runtime": {"liboh_adapter_bridge.so", "libnativeloader.so"},
        "native_loader": {"libapp_native_loader.so"},
    }
    for role, edges in required_edges.items():
        missing = sorted(edges - set(artifacts[role]["needed"]))
        if missing:
            raise SystemExit(f"missing required edges {role}: {missing}")
    if "libhwui.so" in artifacts["adapter_bridge"]["needed"]:
        raise SystemExit("bridge retained the removed ambient hwui dependency")

    graphics = (frozen / "adapter/framework/android-runtime/src/"
                "android_graphics_compat_shim.cpp").read_text(errors="replace")
    denied = ["UNITY_FORCE_OFFSCREEN", 'dlopen("/system/lib64/libEGL.so"',
              'dlopen("/system/lib/liboh_adapter_bridge.so"',
              'dlopen("liboh_adapter_bridge.so", RTLD_NOW);']
    present = [token for token in denied if token in graphics]
    if present:
        raise SystemExit(f"forbidden graphics fallback remains: {present}")

    command_text = "\n".join(
        path.read_text(errors="replace") for path in (root / "logs").glob("*")
        if path.is_file())
    forbidden_paths = ["/opt/10.", "16.12-HanBing", "/02c.", "/data/source"]
    leaks = [value for value in forbidden_paths if value in command_text]
    if leaks:
        raise SystemExit(f"external build path leaked into command logs: {leaks}")

    # Resolve every direct edge recursively against the exact payload, certified
    # AOSP base, target image tree, and target sysroot. Search order is explicit.
    search_dirs = [root / "pass1/payload/adapter", root / "pass1/payload/aosp",
                   root / "pass1/aosp"]
    image = frozen / "oh/out/wukong100/packages/phone/system/lib64"
    for rel in ["", "platformsdk", "chipset-sdk-sp", "chipset-sdk", "ndk",
                "module", "module/arkts"]:
        search_dirs.append(image / rel)
    search_dirs.append(frozen / "sysroot/lib/aarch64-linux-ohos")
    remaining = [root / "pass1" / spec[0] for spec in roots.values()]
    seen, unresolved, edges = {}, [], []
    while remaining:
        current = remaining.pop(0).resolve()
        if str(current) in seen:
            continue
        info = inspect(readelf, current)
        seen[str(current)] = info
        for soname in info["needed"]:
            candidates = [directory / soname for directory in search_dirs
                          if (directory / soname).is_file()]
            if not candidates:
                unresolved.append({"consumer": str(current), "soname": soname})
                continue
            provider = candidates[0].resolve()
            edges.append({"consumer": str(current), "soname": soname,
                          "provider": str(provider), "provider_sha256": sha(provider)})
            remaining.append(provider)
    if unresolved:
        raise SystemExit(f"recursive provider closure unresolved: {unresolved[:8]}")

    meta = root / "meta"
    meta.mkdir(exist_ok=True)
    closure = {"schema": "westlake.provider_closure.v1", "status": "PASS",
               "roots": 4, "objects": len(seen), "edges": edges,
               "unresolved": [], "ambiguous": []}
    (meta / "provider-closure.json").write_text(
        json.dumps(closure, indent=2, sort_keys=True) + "\n")
    receipt = {
        "schema": "westlake.arm64_runtime_generation.v1",
        "generation_id": args.generation_id,
        "status": "build_pass",
        "architecture": "ELF64/AArch64",
        "target": "aarch64-linux-ohos",
        "deterministic_builds": 2,
        "strict_link": True,
        "product_activation": False,
        "device_verified": False,
        "first_frame_stub_call_closure_proven": False,
        "artifacts": artifacts,
        "provider_closure_sha256": sha(meta / "provider-closure.json"),
        "frozen_input_manifest_sha256": sha(frozen.parent / "frozen.sha256"),
    }
    (meta / "generation.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    manifest_files = sorted([meta / "generation.json", meta / "provider-closure.json"] +
                            [root / "pass1" / spec[0] for spec in roots.values()])
    with (meta / "MANIFEST.sha256").open("w") as stream:
        for path in manifest_files:
            stream.write(f"{sha(path)}  {path.relative_to(root)}\n")
    print(f"ARM64_RUNTIME_RECEIPT_PASS generation={args.generation_id} objects={len(seen)}")


if __name__ == "__main__":
    main()
