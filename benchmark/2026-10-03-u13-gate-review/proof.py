import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = REPO.parent
MASTER = WS / "westlake-harness"
sys.path.insert(0, str(REPO / "benchmark/2026-10-03-u13-compat-ctype"))
from common import portable, sha
sys.path.insert(0, str(MASTER / "scripts/lab"))
import open_site_scan as scanner
from rebind import draft_native_rows, draft_static_policy, digest


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2) + "\n")


def capture(name, command):
    result = subprocess.run([str(value) for value in command], text=True, capture_output=True)
    if result.returncode:
        raise ValueError(name + ": " + result.stderr)
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(result.stdout + result.stderr)
    target = HERE / "evidence" / raw.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(portable(raw.read_text()))
    return result.stdout


def literal(elf, address):
    for virtual, offset, size in elf.loads:
        if virtual <= address < virtual + size:
            start = offset + address - virtual
            end = elf.data.find(b"\0", start, min(offset + size, start + 512))
            if end < 0:
                return None
            raw = elf.data[start:end]
            if raw and all(32 <= value < 127 or value in {9, 10} for value in raw):
                return raw.decode("ascii")
    return None


def normalize(path, label):
    text = capture("dlext-" + label, ["llvm-objdump", "-d", "--no-show-raw-insn", "--disassemble-symbols=android_dlopen_ext", path])
    relocations = capture("relocations-" + label, ["llvm-readelf", "-r", "--wide", path])
    imports = {}
    for line in relocations.splitlines():
        match = re.match(r"^([0-9a-f]+)\s+\S+\s+R_AARCH64_GLOB_DAT\s+\S+\s+(\S+)\s+\+", line)
        if match:
            imports[int(match.group(1), 16)] = match.group(2)
    instructions = scanner.parse_disassembly(text)["android_dlopen_ext"]
    elf = scanner.Elf(path)
    start, end = instructions[0][0], instructions[-1][0] + 4
    pages, resolved = {}, []
    for index, (pc, mnemonic, raw) in enumerate(instructions):
        operands = scanner.split_ops(raw.split("//", 1)[0])
        normalized = list(operands)
        if mnemonic == "adrp":
            register, page = operands[0], int(operands[1], 16)
            pages[register] = page
            role = None
            for _, following, following_raw in instructions[index + 1:]:
                parts = scanner.split_ops(following_raw.split("//", 1)[0])
                if following == "adrp" and parts[0] == register:
                    break
                if following == "ldr" and len(parts) == 2:
                    match = re.fullmatch(r"\[" + re.escape(register) + r", #(0x[0-9a-f]+)\]", parts[1])
                    if match and page + int(match.group(1), 16) in imports:
                        role = "GOT:" + imports[page + int(match.group(1), 16)]
                        break
                if following == "add" and parts[:2] == [register, register]:
                    address = page + int(parts[2][1:], 16)
                    value = literal(elf, address)
                    if value is not None:
                        role = "STRING:" + value
                        break
            if role is None:
                raise ValueError("Unresolved page reference, do not wildcard: " + raw)
            normalized[1] = role
            resolved.append(dict(pc=hex(pc), kind="page", role=role))
        elif mnemonic == "ldr" and len(operands) == 2:
            match = re.fullmatch(r"\[(x\d+), #(0x[0-9a-f]+)\]", operands[1])
            if match and match.group(1) in pages:
                address = pages[match.group(1)] + int(match.group(2), 16)
                if address not in imports:
                    raise ValueError("Unexpected GOT target")
                normalized[1] = "[" + match.group(1) + ",GOT:" + imports[address] + "]"
                resolved.append(dict(pc=hex(pc), kind="GOT", address=hex(address), symbol=imports[address]))
        elif mnemonic == "add" and len(operands) == 3 and operands[1] in pages:
            address = pages[operands[1]] + int(operands[2][1:], 16)
            value = literal(elf, address)
            if value is None:
                raise ValueError("Unexpected string address")
            normalized[2] = "STRING:" + value
            resolved.append(dict(pc=hex(pc), kind="cstring", address=hex(address), value=value))
        elif mnemonic == "adr":
            value = literal(elf, int(operands[1], 16))
            if value is None:
                raise ValueError("Unexpected ADR target")
            normalized[1] = "STRING:" + value
            resolved.append(dict(pc=hex(pc), kind="cstring", address=operands[1], value=value))
        elif mnemonic in {"b", "bl", "cbz", "cbnz"} or mnemonic.startswith("b."):
            destination = int(operands[-1], 16)
            if start <= destination < end:
                normalized[-1] = "function+" + hex(destination - start)
            else:
                match = re.search(r"<([^<>]+)@plt>", raw)
                if not match:
                    raise ValueError("Unknown external branch")
                normalized[-1] = "PLT:" + match.group(1)
        resolved_row = dict(offset=hex(pc - start), mnemonic=mnemonic, operands=normalized)
        resolved_row["raw_pc"] = hex(pc)
        resolved_row["raw"] = raw
        resolved.append(dict(kind="instruction", **resolved_row))
    body = [{key: row[key] for key in ["offset", "mnemonic", "operands"]} for row in resolved if row["kind"] == "instruction"]
    graph = scanner.successors(instructions)
    backend = next(index for index, row in enumerate(instructions) if row[1] == "bl" and "__loader_android_dlopen_ext@plt" in row[2])
    fallback = next(index for index, row in enumerate(instructions) if row[1] == "b" and "dlopen@plt" in row[2])
    if scanner.reachable(graph, backend, fallback):
        raise ValueError("Backend call can reach ordinary fallback, new review required")
    return dict(sha256=sha(path), start=hex(start), instruction_count=len(instructions), normalized=body, references=resolved,
         backend_pc=hex(instructions[backend][0]), fallback_pc=hex(instructions[fallback][0]), backend_can_reach_fallback=False,
         explanation="Backend branch returns; cbz skips it to ordinary fallback. Linear resolver crosses an unreachable clobber; raw diagnostic is retained, scanner not patched.")


def main():
    ctype = REPO / "benchmark/2026-10-03-u13-compat-ctype"
    prior = REPO / "benchmark/2026-10-02-u13-assembly-draft"
    package = ctype / ".artifacts/bundle-v2"
    deployed = WS / "westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle/native/payload/android/lib64/libbionic_compat.so"
    bodies = {label: normalize(path, label) for label, path in [("old", deployed),
        ("vlc", ctype / ".artifacts/baseline1.so"), ("new", ctype / ".artifacts/candidate1.so")]}
    if bodies["old"]["normalized"] != bodies["vlc"]["normalized"] or bodies["old"]["normalized"] != bodies["new"]["normalized"]:
        raise ValueError("Full function semantics do not match")
    overlay = REPO / "benchmark/2026-10-02-u12-vlc-bionic-residue/inputs/overlay/android_dlopen_ext.c"
    target = HERE / "sources/android_dlopen_ext.c"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(overlay, target)
    save("semantics.json", dict(bodies=bodies, all_equal=True, source_sha256=sha(overlay), source=target,
         source_statement_lines=[20, 28], historical_pc_delta=0x300, final_pc_delta=0x440,
         artifact_only_addresses_normalized=True, immediate_register_branch_semantics_preserved=True))
    lineage = json.loads((prior / "new-n1-lineage.json").read_text())
    old_source = Path(lineage["baseline_source"].replace("$WORKSPACES", str(WS)))
    new_source = prior / "sources/u13-m1-compat-shim.cpp"
    if sha(old_source) != lineage["baseline_source_sha256"] or sha(new_source) != lineage["candidate_source_sha256"]:
        raise ValueError("NOLOAD source lineage changed")
    shutil.copyfile(old_source, HERE / "sources/gfx-old.cpp")
    shutil.copyfile(new_source, HERE / "sources/gfx-new.cpp")
    contexts = []
    for label, source, ranges in [("old", old_source, [(398, 435), (1309, 1341)]),
                                  ("new", new_source, [(398, 435), (1390, 1420)])]:
        lines = source.read_text().splitlines()
        for first, last in ranges:
            contexts.append(dict(label=label, sha256=sha(source), first_line=first,
                 lines=[dict(line=number, text=lines[number - 1]) for number in range(first, last + 1)]))
    save("evidence/source-lines.json", contexts)
    scans = {}
    runtime_old_sha = "ac59dec0"
    for row in (prior / "scans").glob("*.json"):
        report = json.loads(row.read_text())
        binary = report["binaries"][0]
        if row.stem.startswith(runtime_old_sha) or row.stem.startswith("18763dd4"):
            source = Path(binary["path"].replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO)))
            if sha(source) != row.stem:
                raise ValueError("Historical runtime scan path/hash mismatch")
            scans[row.stem] = binary
    sites = []
    runtime_provenance = []
    for artifact_sha, binary in scans.items():
        source = Path(binary["path"].replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO)))
        runtime_provenance.append(dict(path=source, artifact_sha256=artifact_sha))
        for site in binary["sites"]:
            if "resolve_oh_wm_funcs" in site["function"] and site["path"] == ["liboh_adapter_bridge.so"] or site["function"] == "eglCreateWindowSurface" and site["path"] == ["libEGL.so"]:
                if site["flags"] != ["0x6=NOW|NOLOAD"]:
                    raise ValueError("NOLOAD flag drift")
                sites.append(dict(artifact_sha256=artifact_sha, **site))
                pc = int(site["pc"], 16) if isinstance(site["pc"], str) else site["pc"]
                capture("runtime-" + artifact_sha[:8] + "-" + hex(pc), ["llvm-objdump", "-d", "--no-show-raw-insn",
                    "--start-address=" + hex(pc - 24), "--stop-address=" + hex(pc + 24), source])
    if len(sites) != 4:
        raise ValueError("Expected both resident sites in both ELF scans")
    old_scan = json.loads((prior / "evidence/native-u12.json").read_text())
    old_profiles = [row["profile"] for row in old_scan["gates"]["N1"]["details"]["scanner"]["profiles"]]
    save("lineage.json", dict(**lineage, runtime_sites=sites, old_profiles=old_profiles,
         runtime_provenance=runtime_provenance,
         new_full_gfx_profile="u13-m1-compat-shim.cpp", old_full_gfx_absent="u13-m1-compat-shim.cpp" not in old_profiles,
         miss_behavior=dict(bridge="log and return, no fresh fallback", egl="return EGL_NO_SURFACE; s_resolved alreadytrue, no retry on subsequent call"),
         resident_availability_proven=False, new_mapping_from_these_sites=False))
    libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    ranges = [("noload-mode", "0x85d9c", "0x85de0"), ("noload-map-guard", "0x8712c", "0x871b0")]
    for label, first, last in ranges:
        capture(label, ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=" + first, "--stop-address=" + last, libc])
    save("evidence/noload-flags.json", dict(factory_libc_sha256=sha(libc), same_source_provenance=False,
         interpretation="Actual fd3c binary: mode bit4 at85dc4 saved to15e514;87130 loads it and87134 branches to8717c, bypassing header mapper8f16c at87140. Read-only lookup can miss; no assertion of zero bookkeeping/relocation side effects.",
         files=["evidence/noload-mode.txt", "evidence/noload-map-guard.txt"], sites=sites))
    report = json.loads((ctype / "evidence/native-v2.json").read_text())
    save("evidence/native-final.json", report)
    manifest_bytes = (package / "native/package.json").read_bytes()
    inputs_bytes = (package / "native/native-checks/native-gates.json").read_bytes()
    evidence = "benchmark/2026-10-03-u13-gate-review/evidence/native-final.json"
    rows = draft_native_rows(report, manifest_bytes, inputs_bytes, evidence)
    save("native-predeploy-exceptions.draft.json", rows)
    delta = json.loads((ctype / "open-delta.json").read_text())["vs_deployed"]
    composition = json.loads((ctype / "composition.json").read_text())
    review = dict(review_required=[dict(target=target, candidate_sha256=composition["compat_after"],
        deployed_sha256=bodies["old"]["sha256"], delta_sha256=digest_value) for target in composition["changed_targets"] for digest_value in [digest(delta)]])
    save("static-review.json", review)
    save("static-policy.draft.json", draft_static_policy(review, sha(package / "native/package.json")))
    for name, path in [("native-manifest.json", package / "native/package.json"), ("native-inputs.json", package / "native/native-checks/native-gates.json")]:
        destination = HERE / "manifests" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    save("results.json", dict(package_manifest_sha256=sha(package / "native/package.json"), inputs_sha256=sha(package / "native/native-checks/native-gates.json"),
         bundle_sha256=composition["bundle_sha256"], compat_sha256=composition["compat_after"], review_cases=3, n1_rows=2,
         static_alias_rows=2, same_source_statement=True, semantic_instruction_count=bodies["new"]["instruction_count"],
         native_gate_status="REJECT", exception_rebinding_pending=157, new_n1_pending=2,
         additional_ctype_string_review="benchmark/2026-10-03-u13-compat-ctype/strings-review.json",
         applied=False, execution_enabled=False, registry_writes=0, candidate_rebuilds=0))
    print("REVIEW_ONLY:3758->3a58->3b98 normalized equal; 2 old/new NOLOAD pairs; 2 N1+2 static alias rows, null approvals")


if __name__ == "__main__":
    main()
