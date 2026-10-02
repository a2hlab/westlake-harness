import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
LAB = MASTER / "scripts/lab"
KIT = WS / "oh61-bms-kit-b79"
VALIDATION = WS / "westlake-harness-bms-deploy/benchmark/2026-09-29-install-wall-validation"
SOURCE = "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/installd/installd_operator.cpp"
OLD = "2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0"
NEW = "51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5"
BINARIES = {"old": KIT / "board-baseline/libinstalls.z.so",
            "new": KIT / "out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so"}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable(value):
    text = str(value)
    for root, variable in [(REPO, "$REPO"), (WS, "$WORKSPACES")]:
        if text == str(root):
            return variable
        text = text.replace(str(root) + "/", variable + "/")
    return text


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(label, command):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    raw = HERE / ".artifacts" / (label + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(text)
    target = HERE / "evidence" / (label + ".txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(portable(text))
    return dict(label=label, command=[portable(value) for value in command], exit_code=result.returncode,
                raw_path=portable(raw), raw_sha256=sha(raw), evidence="evidence/" + target.name,
                published_sha256=sha(target), text=text)


def elf_reader():
    path = REPO / "benchmark/2026-10-02-n11h-host-owner/elf_readonly.py"
    spec = importlib.util.spec_from_file_location("readonly", path)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    return reader


def compiled_table():
    reader = elf_reader()
    data = BINARIES["new"].read_bytes()
    sections = reader.sections(data)
    table = next(row for row in sections if row["addr"] <= 0x131ad0 < row["addr"] + row["size"])
    rows = []
    for offset in range(0, 128, 32):
        pointers = struct.unpack_from("<4Q", data, table["offset"] + 0x131ad0 - table["addr"] + offset)
        values = []
        for address in pointers:
            source = next(row for row in sections if row["name"] == ".rodata" and row["addr"] <= address < row["addr"] + row["size"])
            start = source["offset"] + address - source["addr"]
            values.append(data[start:].split(b"\0", 1)[0].decode())
        rows.append(dict(zip(["bundle", "abi", "filename", "sha256"], values), address=hex(0x131ad0 + offset),
                         pointers=[hex(value) for value in pointers]))
    approved = json.loads((VALIDATION / "native-data-exceptions.json").read_text())
    expected = [{field: row[field] for field in ["bundle", "abi", "filename", "sha256"]} for row in approved]
    if [{field: row[field] for field in expected[0]} for row in rows] != expected:
        raise ValueError("compiled four-tuple table drift")
    return rows


def main():
    for name, digest in [("old", OLD), ("new", NEW)]:
        if sha(BINARIES[name]) != digest:
            raise ValueError("deployed byte identity mismatch: " + name)
    objdump = shutil.which("llvm-objdump")
    nm = shutil.which("llvm-nm")
    if not objdump or not nm:
        raise ValueError("LLVM native analysis tools required")
    records = [run("whois", ["python3", LAB / "deployed_whois.py", "libinstalls.z.so"]),
               run("strings", ["python3", LAB / "deployed_strings_diff.py", BINARIES["new"], "--deployed", BINARIES["old"]]),
               run("abi", ["python3", LAB / "abi_diff.py", "--old", BINARIES["old"], "--new", BINARIES["new"],
                           "--calls", "--json", HERE / ".artifacts/abi.json"])]
    abi = json.loads((HERE / ".artifacts/abi.json").read_text())
    save("evidence/abi.json", json.loads(portable(json.dumps(abi))))
    bodies = {"old": (0x117ba0, 0xc7a14, 0xc8ce0), "new": (0x118eac, 0xc8a14, 0xc9d04)}
    for name, (entry, start, end) in bodies.items():
        records.append(run("entry-" + name, [objdump, "-d", "--no-show-raw-insn", "--start-address=" + hex(entry),
                                            "--stop-address=" + hex(entry + 4), BINARIES[name]]))
        records.append(run("extractor-" + name, [objdump, "-d", "--no-show-raw-insn", "--start-address=" + hex(start),
                                                "--stop-address=" + hex(end), BINARIES[name]]))
        records.append(run("open-" + name, ["python3", LAB / "open_site_scan.py", BINARIES[name],
                                           "--json", HERE / ".artifacts" / ("open-" + name + ".json")]))
        save("evidence/open-" + name + ".json", json.loads(portable((HERE / ".artifacts" / ("open-" + name + ".json")).read_text())))
    unstripped = KIT / "out/wukong100/lib.unstripped/bundlemanager/bundle_framework/libinstalls.z.so"
    reader = elf_reader()
    section_hashes = {}
    for path in [BINARIES["new"], unstripped]:
        data = path.read_bytes()
        section_hashes[portable(path)] = {row["name"]: hashlib.sha256(reader.payload(data, row)).hexdigest()
                                         for row in reader.sections(data) if row["name"] in {".text", ".rodata", ".data.rel.ro"}}
    if len(set(json.dumps(row, sort_keys=True) for row in section_hashes.values())) != 1:
        raise ValueError("supplemental symbol owner is not same deployed body/data")
    records.append(run("symbol-lineage", [nm, "-a", "-S", "--demangle", unstripped]))
    symbol_text = records[-1]["text"]
    symbol_lines = [line for line in symbol_text.splitlines() if "ExtractApkNativeFiles" in line]
    (HERE / "evidence/symbol-witnesses.txt").write_text("\n".join(symbol_lines) + "\n")
    records[-1]["evidence"] = "evidence/symbol-witnesses.txt"
    records[-1]["published_sha256"] = sha(HERE / "evidence/symbol-witnesses.txt")
    records[-1]["transformation"] = "Public excerpt selects ExtractApkNativeFiles symbol lines; full nm stdout retained in raw archive"
    records.append(run("validator-new", [objdump, "-d", "--no-show-raw-insn", "--start-address=0xcacac",
                                         "--stop-address=0xcb450", BINARIES["new"]]))
    originals = {variant: KIT / (variant + "-source") / SOURCE for variant in ["baseline", "candidate"]}
    ledger = json.loads((VALIDATION / "source-toolchain.json").read_text())
    for variant, path in originals.items():
        if sha(path) != ledger[variant + "-source/" + SOURCE]:
            raise ValueError("frozen source snapshot drift")
    difference = "".join(difflib.unified_diff(originals["baseline"].read_text().splitlines(True),
                                              originals["candidate"].read_text().splitlines(True),
                                              fromfile="baseline-source/" + SOURCE, tofile="candidate-source/" + SOURCE))
    (HERE / "evidence/source.diff").write_text(difference)
    archive = WS / "oh61-bms-kit-b79-r3-final.tar.gz"
    archive_sha = sha(archive)
    if archive_sha != "61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6":
        raise ValueError("durable final archive drift")
    strings = {name: reader.rodata_strings(path) for name, path in BINARIES.items()}
    clean = {"dropped": sorted(strings["old"] - strings["new"]), "added": sorted(strings["new"] - strings["old"])}
    save("evidence/rodata-delta.json", clean)
    scans = {name: json.loads((HERE / "evidence" / ("open-" + name + ".json")).read_text()) for name in ["old", "new"]}
    semantic_sites = {name: [{field: row[field] for field in ["callee", "path", "namespace", "flags"]}
                            for row in report["binaries"][0]["sites"]] for name, report in scans.items()}
    save("evidence/open-delta.json", dict(old=semantic_sites["old"], new=semantic_sites["new"],
         semantic_equal=semantic_sites["old"] == semantic_sites["new"], old_edges=scans["old"]["binaries"][0]["namespace_edges"],
         new_edges=scans["new"]["binaries"][0]["namespace_edges"], raw_default_ns_retained=True))
    source_lines = originals["candidate"].read_text().splitlines()
    witnesses = [dict(path=portable(originals["candidate"]), line=number, text=line.strip())
                 for number, line in enumerate(source_lines, 1) if any(needle in line for needle in
                 ["dataPayloadExceptions[]", "Sha256File(path) ==", "entry.crc && checkPayload", "S_ISREG(fileStat",
                  "st_uid != 0", "accepted reviewed", "CRC/payload/owner", "table is generated"])]
    save("artifacts.json", dict(schema_version=1, device_access=False, binaries=[dict(role=name, path=portable(path), sha256=sha(path)) for name, path in BINARIES.items()],
         source_snapshots=[dict(path=portable(path), sha256=sha(path)) for path in originals.values()], section_identity=section_hashes,
         table=compiled_table(), table_address="0x131ad0", source_witnesses=witnesses,
         source_patch_commit="22de5ddb52212f3640a7214194472e30991e0c65", approval_refresh_commit="e89d1af4fe7a29c4d095d5cebcb6367c3c87474f",
         archive=dict(path=portable(archive), sha256=archive_sha, remote_path=os.environ.get("HW_HOME", "$HW_HOME") + "/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz"),
         baseline_provenance="Recorded original board backup; adjacent baseline-source snapshot, not a claimed byte-reproduced old build",
         new_provenance="b79 source build, frozen OH clang b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913; archived final kit",
         whois_scope="Default tool covers native runtime bundle/app maps, not system installation services; none/never mapped is NOT service absence",
         commands=[{key: value for key, value in row.items() if key != "text"} for row in records]))
    print("identities: old2c9a5294 / new51e1b525 full SHA verified; source artifact, not live61b copy")
    print("compiled table: 0x131ad0, four exact bundle/ABI/name/payload-SHA rows; no whole-APK-SHA predicate")
    print("CFI entries: old117ba0->c7a14; new118eac->c8a14; deployed text matches supplemental symbols")
    print("raw strings rc=" + str(records[1]["exit_code"]) + "; ABI rc=" + str(records[2]["exit_code"]) + "; no allowance or deployment")


if __name__ == "__main__":
    main()
