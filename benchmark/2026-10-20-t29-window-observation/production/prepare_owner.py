#!/usr/bin/env python3
"""Derive only the five exact owner bindings after the new bridge is linked."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

FUNCTIONS = {
    "oh_anw_get_oh": 0x125dc0,
    "oh_anw_try_acquire": 0x125dfc,
    "oh_anw_try_release": 0x125e4c,
}
SLOTS = {
    "OH_NativeWindow_NativeObjectReference": 0x1740a0,
    "OH_NativeWindow_NativeObjectUnreference": 0x173fc8,
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mappings(data):
    if len(data) < 64 or data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("not ELF64 little-endian")
    kind, machine = struct.unpack_from("<HH", data, 16)
    off = struct.unpack_from("<Q", data, 32)[0]
    size, count = struct.unpack_from("<HH", data, 54)
    if kind != 3 or machine != 183 or size != 56 or not 0 < count <= 64:
        raise ValueError("not bounded AArch64 ET_DYN")
    if off < 64 or off + count * size > min(len(data), 4096):
        raise ValueError("program headers outside runtime gate range")
    loads = []
    for n in range(count):
        typ, flags, fileoff, va, _, filesz, memsz, _ = struct.unpack_from(
            "<IIQQQQQQ", data, off + n * size)
        if typ == 1:
            if filesz > memsz or fileoff + filesz > len(data):
                raise ValueError("invalid PT_LOAD")
            loads.append((va, filesz, memsz, flags))
    return loads


def extract(text, data):
    loads = mappings(data)
    result = {}
    for name in FUNCTIONS:
        rows = re.findall(
            r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)\s+FUNC\s+GLOBAL"
            r"\s+DEFAULT\s+(\d+)\s+" + re.escape(name) + r"\s*$",
            text, re.M)
        if len(rows) != 1:
            raise ValueError("function missing/ambiguous: " + name)
        addr, length = int(rows[0][0], 16), int(rows[0][1])
        if not length or not any(flags & 1 and va <= addr and
                                 addr + length <= va + fs
                                 for va, fs, _, flags in loads):
            raise ValueError("function outside executable file range: " + name)
        result[name] = addr
    for name in SLOTS:
        rows = re.findall(
            r"^([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+"
            r"R_AARCH64_(JUMP_SLOT|GLOB_DAT)\s+0+\s+" +
            re.escape(name) + r"\s+\+\s+0\s*$", text, re.M)
        if len(rows) != 1:
            raise ValueError("reference GOT missing/ambiguous: " + name)
        addr = int(rows[0][0], 16)
        if addr % 8 or not any(flags & 4 and va <= addr and addr + 8 <= va + ms
                               for va, _, ms, flags in loads):
            raise ValueError("GOT outside readable PT_LOAD: " + name)
        result[name] = addr
    if len(set(result.values())) != 5:
        raise ValueError("overlapping binding locations")
    return result


def derive(source, bindings):
    """Preserve every other source byte and all same-provider predicates."""
    replacements = {hex(old): hex(bindings[name])
                    for name, old in (FUNCTIONS | SLOTS).items()}
    pattern = re.compile(r"\b(?:" + "|".join(map(re.escape, replacements)) + r")\b")
    for old in replacements:
        if not re.search(r"\b" + re.escape(old) + r"\b", source):
            raise ValueError("template no longer contains expected binding: " + old)
    return pattern.sub(lambda m: replacements[m[0]], source)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bridge", type=Path, required=True)
    p.add_argument("--bridge-sha256", required=True)
    p.add_argument("--readelf", type=Path, required=True)
    p.add_argument("--readelf-sha256", required=True)
    p.add_argument("--template-dir", type=Path, required=True)
    p.add_argument("--template-pins", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if sha(a.bridge) != a.bridge_sha256 or sha(a.readelf) != a.readelf_sha256:
        raise ValueError("bridge/tool SHA mismatch")
    pins = json.loads(a.template_pins.read_text())
    originals = {}
    for name in ("geometry.c", "pair.c"):
        f = a.template_dir / name
        if sha(f) != pins[name]:
            raise ValueError("template SHA mismatch: " + name)
        originals[name] = f.read_bytes()
    a.out.mkdir(parents=True, exist_ok=False)
    # Keep argv[0] llvm-readelf, even when it is a symlink to llvm-readobj.
    argv = [str(a.readelf), "--elf-output-style=GNU", "--dyn-syms",
            "--relocs", "--wide", str(a.bridge)]
    (a.out / "readelf.argv.json").write_text(json.dumps(argv) + "\n")
    with (a.out / "readelf.stdout").open("wb") as o, (a.out / "readelf.stderr").open("wb") as e:
        rc = subprocess.run(argv, stdout=o, stderr=e).returncode
    (a.out / "readelf.rc").write_text(str(rc) + "\n")
    if rc:
        raise SystemExit(rc)
    bindings = extract((a.out / "readelf.stdout").read_text(), a.bridge.read_bytes())
    if sha(a.bridge) != a.bridge_sha256 or sha(a.readelf) != a.readelf_sha256:
        raise ValueError("bridge/tool drift during extraction")
    produced = {}
    for name, old in originals.items():
        if sha(a.template_dir / name) != pins[name]:
            raise ValueError("template drift during extraction")
        new = derive(old.decode(), bindings).encode()
        (a.out / name).write_bytes(new)
        produced[name] = {"before": pins[name], "after": sha(a.out / name)}
    receipt = {
        "status": "EXACT_ELF_BINDINGS_ONLY_NOT_RUNTIME_ADMISSION",
        "bridge_sha256": a.bridge_sha256,
        "readelf_sha256": a.readelf_sha256,
        "offsets": {name: hex(value) for name, value in bindings.items()},
        "sources": produced,
        "same_provider_predicates": "unchanged; only five exact location literals replaced",
        "production_requirement": "compile these derived files, never the old templates",
        "device_calls": 0,
    }
    (a.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
