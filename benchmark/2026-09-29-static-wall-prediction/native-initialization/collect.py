#!/usr/bin/env python3
"""Capture existing native source snapshots and bounded framework DEX evidence offline."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def collect(workspaces, output):
    from loguru import logger
    logger.remove()
    from androguard.core.dex import DEX

    deploy = workspaces / "westlake-harness-bms-deploy/benchmark"
    origins = {
        "n2-host.c": ("2026-09-30-n2-native/src/westlake_stock_host_main.c", 1),
        "n3b-host.c": ("2026-09-30-n3-native/src/westlake_stock_host_main.c", 1),
        "n4-runtime.cpp": ("2026-09-30-n4-native/src/AndroidRuntime.cpp", 1),
        "n4-order-runtime.cpp": ("2026-10-01-j6-n4-sweep/n4-registration-order/AndroidRuntime.cpp", 1),
        "egl.cpp": ("2026-09-30-n4-native/src/oh_egl_impl.cpp", 1),
        "gl-register.cpp": ("2026-09-30-n2-native/src/com_google_android_gles_jni_GLImpl.cpp", 9036),
        "gl-wrapper.cpp": ("2026-09-30-n2-native/src/glimpl_register.cpp", 1),
    }
    output.mkdir(parents=True, exist_ok=True)
    source_dir = output / "evidence/sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    sources = {}
    for name, (origin, first_line) in origins.items():
        path = deploy / origin
        raw = path.read_bytes()
        selected = b"".join(raw.splitlines(keepends=True)[first_line - 1:])
        target = source_dir / name
        target.write_bytes(selected)
        sources[name] = dict(path=str(target.relative_to(output)), sha256=sha(selected),
                             origin=str(path.relative_to(workspaces)), source_sha256=sha(raw), first_line=first_line)
    for folder, name in [("2026-09-30-n3-native", "n3b-host.c"), ("2026-09-30-n4-native", "n4-runtime.cpp"), ("2026-09-30-n4-native", "egl.cpp")]:
        pins = json.loads((deploy / folder / "source-sha256.json").read_text())
        original = origins[name][0].split("/", 1)[1]
        if sources[name]["source_sha256"] != pins[original]:
            raise ValueError("snapshot/build source mismatch: " + name)
    order = json.loads((deploy / "2026-10-01-j6-n4-sweep/n4-registration-order/build-inputs.json").read_text())
    if order["source_sha256"] != sources["n4-order-runtime.cpp"]["source_sha256"] or order["original_sha256"] != sources["n4-runtime.cpp"]["source_sha256"]:
        raise ValueError("N4-order build receipt mismatch")
    jar = workspaces / "westlake-generation-n2-51a78bde/payload/android/framework/framework.jar"
    raw = jar.read_bytes()
    if sha(raw) != "3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af":
        raise ValueError("framework identity mismatch")
    classes, dex_inputs = {}, []
    with zipfile.ZipFile(jar) as archive:
        for entry in archive.namelist():
            if not entry.endswith(".dex"):
                continue
            dex_raw = archive.read(entry)
            dex_inputs.append(dict(entry=entry, sha256=sha(dex_raw)))
            for cls in DEX(dex_raw).get_classes():
                owner = cls.get_name()[1:-1]
                if not (owner.startswith("com/google/android/gles_jni/") or owner in {"java/lang/Object", "javax/microedition/khronos/egl/EGLContext"}):
                    continue
                methods = []
                for method in cls.get_methods():
                    if method.get_name() not in {"<init>", "<clinit>", "_nativeClassInit"}:
                        continue
                    instructions, offset = [], 0
                    for instruction in method.get_instructions():
                        instructions.append(dict(offset=offset, opcode=instruction.get_name(), output=instruction.get_output()))
                        offset += instruction.get_length()
                    methods.append(dict(name=method.get_name(), descriptor=method.get_descriptor().replace(" ", ""),
                                        native=bool(method.get_access_flags() & 0x100), instructions=instructions))
                parent = cls.get_superclassname()
                classes[owner] = dict(super=parent[1:-1] if parent else None, methods=methods, dex_entry=entry)
    dex_path = output / "evidence/framework-initializers.json"
    dex_path.write_text(json.dumps(dict(origin=str(jar.relative_to(workspaces)), jar_sha256=sha(raw), dex_inputs=dex_inputs, classes=classes), indent=2) + "\n")
    profiles = []
    for name, package, rule, source in [
        ("N2", "westlake-generation-n2-51a78bde", "namespace", "n2-host.c"),
        ("N3b", "westlake-generation-n3b-53bb18d1", "namespace", "n3b-host.c"),
        ("N4", "westlake-generation-n4-1617080a", "jni-order", "n4-runtime.cpp"),
        ("N4-order", "westlake-generation-n4-order-216b68fb", "jni-order", "n4-order-runtime.cpp"),
    ]:
        package_raw = (workspaces / package / "package.json").read_bytes()
        package_data = json.loads(package_raw)
        suffix = "/appspawn-x" if rule == "namespace" else "/liboh_android_runtime.so"
        candidates = [path for path in package_data["files"] if path.endswith(suffix)]
        if len(candidates) != 1:
            raise ValueError("ambiguous generation artifact: " + package)
        binary = candidates[0]
        binary_raw = (workspaces / package / binary).read_bytes()
        if sha(binary_raw) != package_data["files"][binary]:
            raise ValueError("generation binary mismatch: " + package)
        identity = dict(package=package, manifest_sha256=sha(package_raw), artifact=binary, artifact_sha256=sha(binary_raw))
        profile = dict(name=name, rule=rule, source=source, identity=identity)
        if rule == "jni-order":
            profile.update(sources=[source, "egl.cpp", "gl-register.cpp", "gl-wrapper.cpp"], entry_source=source, entry_function="startReg")
        profiles.append(profile)
    manifest = dict(schema_version=1, sources=sources, profiles=profiles,
                    dex=dict(path=str(dex_path.relative_to(output)), sha256=sha(dex_path.read_bytes())))
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspaces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    collect(args.workspaces, args.output)
