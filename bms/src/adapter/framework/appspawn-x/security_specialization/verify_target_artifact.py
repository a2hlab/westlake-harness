#!/usr/bin/env python3
"""Fail-closed ELF/source gate for the non-activated OH security adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess


EXPECTED_EXPORTS = {
    "WLSS_ParentPrepare",
    "WLSS_ParentPreFork",
    "WLSS_ChildExecute",
    "WLSS_GetTlvSpan",
    "WLSS_ReasonString",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def under(path: pathlib.Path, root: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"path escapes project root: {resolved}") from error
    return resolved


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def tool(executable: pathlib.Path, *arguments: str) -> str:
    completed = subprocess.run(
        [str(executable), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


def dynamic_exports(symbols: str) -> set[str]:
    exports: set[str] = set()
    in_dynamic = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynamic = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynamic = False
        if not in_dynamic or " GLOBAL " not in line or " DEFAULT " not in line:
            continue
        match = re.search(r"\b(WLSS_[A-Za-z0-9_]+)(?:@@[^ ]+)?$", line)
        if match:
            exports.add(match.group(1))
    return exports


def dynamic_undefined(symbols: str) -> list[str]:
    undefined: list[str] = []
    in_dynamic = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynamic = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynamic = False
        if in_dynamic and " UND " in line and not line.rstrip().endswith(" UND"):
            undefined.append(line.strip())
    return undefined


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--second-library", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.project_root).resolve(strict=True)
    library = under(pathlib.Path(args.library), root)
    second = under(pathlib.Path(args.second_library), root)
    readelf = under(pathlib.Path(args.readelf), root)
    objdump = under(pathlib.Path(args.objdump), root)
    report = pathlib.Path(args.report).resolve()
    try:
        report.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"report escapes project root: {report}") from error

    module = under(
        root / "adapter/framework/appspawn-x/security_specialization", root
    )
    source_paths = [
        under(module / "include/westlake_oh_security_specialization.h", root),
        under(module / "src/security_specialization.c", root),
    ]
    source = "\n".join(path.read_text(encoding="utf-8")
                       for path in source_paths)

    forbidden_source = {
        "constructor": r"__attribute__\s*\(\(\s*constructor\b",
        "thread_local": r"\b(?:_Thread_local|__thread|thread_local)\b",
        "dynamic_loader": r"\b(?:dlopen|dlsym|dlvsym)\s*\(",
        "environment_activation": r"\b(?:getenv|secure_getenv)\s*\(",
        "direct_security_primitive": (
            r"\b(?:mount|umount|umount2|unshare|chroot|pivot_root|setcon|"
            r"setexeccon|setfscreatecon|setfsuid|setresuid|setresgid|"
            r"setgroups|syscall)\s*\("
        ),
        "direct_procattr": r"/(?:proc|sys)/[^\n\"]*attr|procattr\.c",
        "stock_opaque_struct_fabrication": (
            r"\b(?:TagAppSpawnMgr|TagAppSpawningCtx|AppSpawnMsgNode)\s+[A-Za-z_]"
        ),
    }
    source_hits = {
        name: bool(re.search(pattern, source, flags=re.IGNORECASE))
        for name, pattern in forbidden_source.items()
    }
    require(not any(source_hits.values()),
            f"forbidden source primitive: {source_hits}")
    require(digest(library) == digest(second),
            "target builds are not byte-identical")

    headers = tool(readelf, "-W", "-h", str(library))
    programs = tool(readelf, "-W", "-l", str(library))
    dynamic = tool(readelf, "-W", "-d", str(library))
    sections = tool(readelf, "-W", "-S", str(library))
    symbols = tool(readelf, "-W", "-s", str(library))
    relocations = tool(readelf, "-W", "-r", str(library))
    notes = tool(readelf, "-W", "-n", str(library))
    disassembly = tool(objdump, "-d", str(library))

    require("Machine:                           AArch64" in headers,
            "artifact is not AArch64")
    require("Type:                              DYN" in headers,
            "artifact is not a DSO")
    require(not re.search(r"^\s*TLS\s", programs, re.MULTILINE),
            "PT_TLS is forbidden")
    require(not re.search(r"\.tdata|\.tbss", sections),
            "TLS sections are forbidden")
    require(not re.search(r"\.preinit_array|\.init_array", sections),
            "constructor sections are forbidden")
    require(not re.search(r"\((?:PREINIT_ARRAY|INIT_ARRAY|INIT)\)", dynamic),
            "constructor dynamic tags are forbidden")
    require("(NEEDED)" not in dynamic,
            "control-plane artifact must not link stock/runtime DSOs")
    require("(RPATH)" not in dynamic and "(RUNPATH)" not in dynamic,
            "runtime search paths are forbidden")
    require("(TEXTREL)" not in dynamic, "text relocations are forbidden")
    require(
        "Library soname: [libwestlake_oh_security_specialization.so]" in dynamic,
        "SONAME mismatch",
    )
    require("Build ID:" in notes, "build ID missing")
    require(dynamic_exports(symbols) == EXPECTED_EXPORTS,
            f"export set mismatch: {dynamic_exports(symbols)}")
    require(not dynamic_undefined(symbols),
            f"undefined dynamic symbols: {dynamic_undefined(symbols)}")
    require("svc" not in disassembly.lower(), "direct syscall instruction forbidden")
    require(not re.search(r"TLS|TLSDESC|TPREL|DTPREL", relocations,
                          flags=re.IGNORECASE),
            "TLS relocation forbidden")
    require(not re.search(
        r"\b(?:mount|umount|unshare|chroot|pivot_root|setcon|setexeccon|"
        r"setfscreatecon|dlopen|dlsym|TagAppSpawnMgr|TagAppSpawningCtx|"
        r"SetAppSandboxProperty|AppSpawnHookExecute)\b",
        symbols,
    ), "forbidden implementation symbol present")

    result = {
        "status": "PASS",
        "classification": "control_plane_adapter_not_stock_binding",
        "product_activation": False,
        "device_verified": False,
        "deterministic_builds": 2,
        "sha256": digest(library),
        "exports": sorted(EXPECTED_EXPORTS),
        "needed": [],
        "pt_tls": False,
        "constructors": False,
        "direct_security_primitives": False,
        "opaque_stock_struct_fabrication": False,
        "source_gate": source_hits,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
