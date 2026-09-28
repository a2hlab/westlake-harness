#!/usr/bin/env python3
"""Fail-closed identity/owner verifier for two strict provider builds."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from libart_tuple_receipt import verify as verify_libart_tuple_receipt


LEGACY_V11_EXPECTED_FILES = {
    "libapp_native_loader.so",
    "libart.so",
    "libart_runtime_stubs.so",
    "libartbase.so",
    "libartpalette-system.so",
    "libartpalette.so",
    "libbase.so",
    "libbionic_compat.so",
    "libcutils.so",
    "libdexfile.so",
    "libelffile.so",
    "liblog.so",
    "liblz4.so",
    "liblzma.so",
    "libnativebridge.so",
    "libnativehelper.so",
    "libnativeloader.so",
    "libprofile.so",
    "libsigchain.so",
    "libtinyxml2.so",
    "libunwindstack.so",
    "libutils.so",
    "libvixl.so",
    "libziparchive.so",
}

NO_BROAD_ART_STUB_EXPECTED_FILES = (
    LEGACY_V11_EXPECTED_FILES - {"libart_runtime_stubs.so"}
)

POLICIES = {
    "legacy-v11": {
        "expected_files": LEGACY_V11_EXPECTED_FILES,
        "broad_art_stub_absent": False,
        "real_palette_scheduler": False,
    },
    "no-broad-art-stub-v1": {
        "expected_files": NO_BROAD_ART_STUB_EXPECTED_FILES,
        "broad_art_stub_absent": True,
        "real_palette_scheduler": False,
    },
    "no-broad-art-stub-real-palette-v2": {
        "expected_files": NO_BROAD_ART_STUB_EXPECTED_FILES,
        "broad_art_stub_absent": True,
        "real_palette_scheduler": True,
        "atomic_libart_tuple": False,
    },
    "libart-zero-array-tuple-v3": {
        "expected_files": NO_BROAD_ART_STUB_EXPECTED_FILES | {"libart-compiler.so"},
        "broad_art_stub_absent": True,
        "real_palette_scheduler": False,
        "atomic_libart_tuple": True,
    },
}

BASE_PROVIDERS = {
    "libc.so",
    "libc++.so",
    "libdl.so",
    "libm.so",
    "libpthread.so",
    "librt.so",
    "libbegetutil.z.so",
    "libhilog.so",
    "libshared_libz.z.so",
}

FORBIDDEN_COMPAT_DEFINITIONS = {
    "ErrorCodeString",
    "_Z15ErrorCodeStringi",
    "pthread_create",
    "pthread_key_create",
    "pthread_getspecific",
    "pthread_setspecific",
    "sigaction",
    "signal",
}

NO_BROAD_STUB_REAL_OWNERS = {
    # AOSP deliberately has a client and its dlopen'd system implementation.
    # libprofile links to the client; the duplicate typed API is not a stub or
    # an accidental provider ambiguity.
    "PaletteTraceBegin": ("libartpalette-system.so", "libartpalette.so"),
    "PaletteTraceEnd": ("libartpalette-system.so", "libartpalette.so"),
    "_ZNK9unix_file6FdFile2FdEv": ("libartbase.so",),
    "_ZN9unix_file6FdFile12ClearContentEv": ("libartbase.so",),
    "_ZN11unwindstack20DemangleNameIfNeededERKNSt3__h12basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEE": ("libunwindstack.so",),
    "_ZN7art_api3dex14LoadLibdexfileEv": ("libunwindstack.so",),
    "_ZN7art_api3dex17TryLoadLibdexfileEPNSt3__h12basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEE": ("libunwindstack.so",),
    "_ZN7art_api3dex17g_ADexFile_createE": ("libunwindstack.so",),
    "_ZN7art_api3dex18g_ADexFile_destroyE": ("libunwindstack.so",),
    "_ZN7art_api3dex29g_ADexFile_findMethodAtOffsetE": ("libunwindstack.so",),
    "_ZN7art_api3dex31g_ADexFile_Method_getCodeOffsetE": ("libunwindstack.so",),
    "_ZN7art_api3dex34g_ADexFile_Method_getQualifiedNameE": ("libunwindstack.so",),
    "ADexFile_create": ("libdexfile.so",),
    "ADexFile_destroy": ("libdexfile.so",),
    "ADexFile_findMethodAtOffset": ("libdexfile.so",),
    "ADexFile_Method_getCodeOffset": ("libdexfile.so",),
    "ADexFile_Method_getQualifiedName": ("libdexfile.so",),
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tool_output(tool: Path, *arguments: str) -> str:
    result = subprocess.run(
        [str(tool), *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        fail(f"tool failed rc={result.returncode}: {tool.name} {' '.join(arguments)}: {result.stderr}")
    return result.stdout


def defined_symbols(readelf: Path, elf: Path) -> dict[str, int]:
    output = tool_output(readelf, "--dyn-syms", "--wide", str(elf))
    definitions: dict[str, int] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(":"):
            continue
        if fields[4] not in {"GLOBAL", "WEAK"} or fields[6] == "UND":
            continue
        name = fields[7].split("@", 1)[0]
        definitions[name] = definitions.get(name, 0) + 1
    return definitions


def undefined_symbols(readelf: Path, elf: Path) -> set[str]:
    output = tool_output(readelf, "--dyn-syms", "--wide", str(elf))
    undefined: set[str] = set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(":") or fields[6] != "UND":
            continue
        undefined.add(fields[7].split("@", 1)[0])
    return undefined


def inspect(
    readelf: Path,
    root: Path,
    expected_files: set[str],
) -> dict[str, dict[str, object]]:
    providers = root / "providers"
    actual = {path.name for path in providers.glob("*.so") if path.is_file() and not path.is_symlink()}
    if actual != expected_files:
        fail(
            "provider file set mismatch "
            f"missing={sorted(expected_files-actual)} extra={sorted(actual-expected_files)}"
        )
    if any(path.is_symlink() for path in providers.iterdir()):
        fail("provider output contains a symlink")

    records: dict[str, dict[str, object]] = {}
    soname_owners: dict[str, list[str]] = {}
    for name in sorted(actual):
        elf = providers / name
        header = tool_output(readelf, "--file-header", str(elf))
        if "Class:                             ELF64" not in header:
            fail(f"{name}: not ELF64")
        if "Machine:                           AArch64" not in header:
            fail(f"{name}: not AArch64")
        if not re.search(r"Type:\s+DYN ", header):
            fail(f"{name}: not ET_DYN")

        dynamic = tool_output(readelf, "--dynamic-table", str(elf))
        sonames = re.findall(r"Library soname: \[([^]]+)\]", dynamic)
        if sonames != [name]:
            fail(f"{name}: expected one exact SONAME, got {sonames}")
        if re.search(r"\b(RPATH|RUNPATH|TEXTREL)\b", dynamic):
            fail(f"{name}: forbidden RPATH/RUNPATH/TEXTREL")
        needed = re.findall(r"Shared library: \[([^]]+)\]", dynamic)
        soname_owners.setdefault(sonames[0], []).append(name)

        notes = tool_output(readelf, "--notes", str(elf))
        build_ids = re.findall(r"Build ID:\s*([0-9a-fA-F]+)", notes)
        if len(build_ids) != 1 or not re.fullmatch(r"[0-9a-fA-F]{40}", build_ids[0]):
            fail(f"{name}: expected one SHA1 Build-ID, got {build_ids}")

        records[name] = {
            "sha256": sha256(elf),
            "build_id": build_ids[0].lower(),
            "soname": sonames[0],
            "needed": needed,
            "defined": defined_symbols(readelf, elf),
        }

    duplicates = {name: owners for name, owners in soname_owners.items() if len(owners) != 1}
    if duplicates:
        fail(f"duplicate SONAME owners: {duplicates}")

    admitted = set(soname_owners) | BASE_PROVIDERS
    unresolved: list[tuple[str, str]] = []
    for consumer, record in records.items():
        for needed in record["needed"]:  # type: ignore[index]
            if needed not in admitted:
                unresolved.append((consumer, str(needed)))
    if unresolved:
        fail(f"unadmitted DT_NEEDED edges: {unresolved}")

    return records


def require_direct(records: dict[str, dict[str, object]], consumer: str, provider: str) -> None:
    needed = records[consumer]["needed"]
    if list(needed).count(provider) != 1:  # type: ignore[arg-type]
        fail(f"direct edge {consumer}->{provider} count={list(needed).count(provider)}")


def require_exact_owners(
    records: dict[str, dict[str, object]], symbol: str, expected_owners: tuple[str, ...]
) -> None:
    owners = {
        name: int(record["defined"].get(symbol, 0))  # type: ignore[union-attr]
        for name, record in records.items()
        if int(record["defined"].get(symbol, 0)) != 0  # type: ignore[union-attr]
    }
    expected = {owner: 1 for owner in expected_owners}
    if owners != expected:
        fail(f"real owner mismatch for {symbol}: {owners}")


def verify_runtime_start_zero_array_transport(
    readelf: Path, objdump: Path, libart: Path
) -> str:
    symbols = tool_output(readelf, "--dyn-syms", "--wide", str(libart))
    symbol = re.search(
        r"^\s*\d+:\s*([0-9a-fA-F]+)\s+(\d+)\s+FUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+_ZN3art7Runtime5StartEv\s*$",
        symbols,
        re.MULTILINE,
    )
    if symbol is None:
        fail("Runtime::Start dynamic symbol is absent")
    start = int(symbol.group(1), 16)
    stop = start + int(symbol.group(2))
    disassembly = tool_output(
        objdump,
        "-d",
        "--demangle",
        f"--start-address={start:#x}",
        f"--stop-address={stop:#x}",
        str(libart),
    )
    lines = disassembly.splitlines()
    invoke_windows = []
    for index, line in enumerate(lines):
        if "<art::ArtMethod::Invoke(" in line and re.search(r"\bbl\b", line):
            invoke_windows.append("\n".join(lines[max(0, index - 12):index + 1]))
    if len(invoke_windows) != 1:
        fail(f"Runtime::Start ArtMethod::Invoke count={len(invoke_windows)}")
    window = invoke_windows[0]
    if (re.search(r"\bmov\s+x2,\s*xzr\b", window) and
            re.search(r"\bmov\s+w3,\s*#(?:0x)?4\b", window)):
        fail("Runtime::Start retains rejected args=nullptr,args_size=4 transport")
    if not re.search(r"\b(?:add\s+x2,\s*sp|mov\s+x2,\s*sp)\b", window):
        fail("Runtime::Start zero-array pointer is not stack-owned")
    if re.search(r"\bmov\s+w3,\s*wzr\b", window):
        return "stack-address/0"
    if re.search(r"\bmov\s+w3,\s*#(?:0x)?4\b", window):
        return "stack-address/4"
    fail("Runtime::Start zero-array byte count is neither 0 nor 4")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readelf", required=True, type=Path)
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--repro", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--objdump", type=Path)
    parser.add_argument(
        "--policy",
        choices=sorted(POLICIES),
        default="legacy-v11",
        help="Explicit generation contract; legacy-v11 remains the default so its immutable evidence can be replayed.",
    )
    args = parser.parse_args()

    policy = POLICIES[args.policy]
    expected_files = set(policy["expected_files"])
    broad_art_stub_absent = bool(policy["broad_art_stub_absent"])
    real_palette_scheduler = bool(policy["real_palette_scheduler"])
    atomic_libart_tuple = bool(policy.get("atomic_libart_tuple", False))

    primary = inspect(args.readelf, args.primary, expected_files)
    repro = inspect(args.readelf, args.repro, expected_files)

    primary_identity = {
        name: (record["sha256"], record["build_id"], record["soname"])
        for name, record in primary.items()
    }
    repro_identity = {
        name: (record["sha256"], record["build_id"], record["soname"])
        for name, record in repro.items()
    }
    if primary_identity != repro_identity:
        differences = {
            name: {"primary": primary_identity[name], "repro": repro_identity[name]}
            for name in sorted(primary_identity)
            if primary_identity[name] != repro_identity[name]
        }
        fail(f"provider build is not byte deterministic: {differences}")

    tuple_receipt = None
    runtime_start_zero_array_transport = None
    if atomic_libart_tuple:
        if args.inputs is None or args.objdump is None:
            fail("atomic libart tuple policy requires --inputs and --objdump")
        primary_tuple = verify_libart_tuple_receipt(
            args.primary / "BRIDGE_LIBART_TUPLE_RECEIPT.json",
            args.inputs,
            args.primary,
            args.readelf,
        )
        repro_tuple = verify_libart_tuple_receipt(
            args.repro / "BRIDGE_LIBART_TUPLE_RECEIPT.json",
            args.inputs,
            args.repro,
            args.readelf,
        )
        if primary_tuple != repro_tuple:
            fail("primary/repro BRIDGE_LIBART_TUPLE_RECEIPT mismatch")
        tuple_receipt = primary_tuple
        runtime_start_zero_array_transport = verify_runtime_start_zero_array_transport(
            args.readelf, args.objdump, args.primary / "providers/libart.so"
        )

    error_symbol = "_Z15ErrorCodeStringi"
    owners = {
        name: int(record["defined"].get(error_symbol, 0))  # type: ignore[union-attr]
        for name, record in primary.items()
        if int(record["defined"].get(error_symbol, 0)) != 0  # type: ignore[union-attr]
    }
    if owners != {"libziparchive.so": 1}:
        fail(f"ErrorCodeString owner mismatch: {owners}")

    compat_definitions = primary["libbionic_compat.so"]["defined"]
    forbidden_present = sorted(
        symbol for symbol in FORBIDDEN_COMPAT_DEFINITIONS
        if int(compat_definitions.get(symbol, 0)) != 0  # type: ignore[union-attr]
    )
    if forbidden_present:
        fail(f"compat owns forbidden global ABI: {forbidden_present}")

    require_direct(primary, "libartbase.so", "libziparchive.so")
    require_direct(primary, "libart.so", "libnativeloader.so")
    require_direct(primary, "libnativeloader.so", "libapp_native_loader.so")

    broad_art_stub_consumers = sorted(
        name
        for name, record in primary.items()
        if "libart_runtime_stubs.so" in record["needed"]
    )
    if broad_art_stub_absent:
        if "libart_runtime_stubs.so" in primary:
            fail("no-broad-art-stub policy admitted libart_runtime_stubs.so")
        if broad_art_stub_consumers:
            fail(
                "no-broad-art-stub policy found direct consumers: "
                f"{broad_art_stub_consumers}"
            )
        require_direct(primary, "libprofile.so", "libartbase.so")
        require_direct(primary, "libprofile.so", "libartpalette.so")
        require_direct(primary, "libunwindstack.so", "libdexfile.so")
        for symbol, owners in NO_BROAD_STUB_REAL_OWNERS.items():
            require_exact_owners(primary, symbol, owners)
        forbidden_global_interposers = {
            symbol: sorted(
                name
                for name, record in primary.items()
                if int(record["defined"].get(symbol, 0)) != 0  # type: ignore[union-attr]
            )
            for symbol in ("abort", "raise")
        }
        forbidden_global_interposers = {
            symbol: owners
            for symbol, owners in forbidden_global_interposers.items()
            if owners
        }
        if forbidden_global_interposers:
            fail(
                "provider generation owns libc process-control interposers: "
                f"{forbidden_global_interposers}"
            )

    if real_palette_scheduler:
        palette = primary["libartpalette-system.so"]
        if palette["needed"] != ["libc.so", "liblog.so"]:
            fail(
                "real OH Palette provider must need exactly libc/liblog, got "
                f"{palette['needed']}"
            )
        palette_undefined = undefined_symbols(
            args.readelf,
            args.primary / "providers" / "libartpalette-system.so",
        )
        missing_scheduler_imports = {
            "setpriority", "getpriority"
        } - palette_undefined
        if missing_scheduler_imports:
            fail(
                "Palette target lacks real scheduler imports: "
                f"{sorted(missing_scheduler_imports)}"
            )

    compat_program_headers = tool_output(
        args.readelf,
        "--program-headers",
        str(args.primary / "providers" / "libbionic_compat.so"),
    )
    if re.search(r"^\s*TLS\s", compat_program_headers, re.MULTILINE):
        fail("libbionic_compat.so unexpectedly owns PT_TLS")

    report = {
        "schema": "westlake.provider-generation-verification.v2",
        "status": "ARTIFACT_VERIFIED_NOT_PRODUCT_ACTIVATED",
        "policy": args.policy,
        "provider_count": len(primary),
        "byte_deterministic_runs": 2,
        "unique_soname_count": len(primary),
        "build_id_complete": True,
        "rpath_runpath_textrel_absent": True,
        "error_code_string_owner": "libziparchive.so",
        "direct_edges": [
            "libartbase.so->libziparchive.so",
            "libart.so->libnativeloader.so",
            "libnativeloader.so->libapp_native_loader.so",
        ],
        "compat_forbidden_owners_absent": sorted(FORBIDDEN_COMPAT_DEFINITIONS),
        "compat_pt_tls_absent": True,
        "broad_art_runtime_stub_absent": broad_art_stub_absent,
        "broad_art_runtime_stub_consumers": broad_art_stub_consumers,
        "real_palette_scheduler": real_palette_scheduler,
        "atomic_libart_tuple": atomic_libart_tuple,
        "bridge_libart_tuple_receipt": tuple_receipt,
        "runtime_start_zero_array_transport": runtime_start_zero_array_transport,
        "no_broad_stub_real_owners": (
            {
                symbol: list(owners)
                for symbol, owners in sorted(NO_BROAD_STUB_REAL_OWNERS.items())
            }
            if broad_art_stub_absent else {}
        ),
        "product_activation": False,
        "device_verified": False,
        "not_proven": [
            "stock appspawn host/plugin final integration",
            "main and every Android-owned thread guard publication",
            "full initial TP/prepare certificate",
            "first-frame stub call closure",
            "production init or Unity first frame",
        ],
        "providers": {
            name: {
                "sha256": record["sha256"],
                "build_id": record["build_id"],
                "soname": record["soname"],
                "needed": record["needed"],
            }
            for name, record in primary.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS provider_generation "
        f"providers={len(primary)} deterministic=2 unique_soname={len(primary)} "
        "build_id=complete product_activation=false"
    )


if __name__ == "__main__":
    main()
