import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from source import HERE, REPO, R3_SHA, sha


WORKSPACES = Path(os.environ.get("WORKSPACES", REPO.parent)).resolve()
HARNESS = WORKSPACES / "westlake-harness"
BASE = WORKSPACES / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native"
RAW = HERE / ".artifacts/gates"
HOST = HERE / ".artifacts/frozen-r1/candidate/appspawn-x"
BASE_HOST = BASE / "payload/runtime/appspawn-x"
COMMANDS = []


def portable(text):
    return text.replace(str(REPO), "$REPO").replace(str(WORKSPACES), "$WORKSPACES")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(label, command, expected=0):
    completed = subprocess.run([str(value) for value in command], capture_output=True, text=True, cwd=REPO)
    output = RAW / (label + ".txt")
    output.write_text(completed.stdout + completed.stderr)
    record = dict(label=label, command=[portable(str(value)) for value in command],
                  exit_code=completed.returncode, raw_stdout=portable(str(output)), raw_sha256=sha(output))
    COMMANDS.append(record)
    print(label + " exit=" + str(completed.returncode) + " raw_sha256=" + record["raw_sha256"], flush=True)
    accepted = expected if isinstance(expected, tuple) else (expected,)
    if completed.returncode not in accepted:
        raise ValueError("unexpected exit: " + label)
    return completed.stdout


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_package():
    destination = HERE / ".artifacts/audit-package"
    original = json.loads((BASE / "package.json").read_text())
    if sha(BASE_HOST) != R3_SHA:
        raise ValueError("prospective baseline is not accepted r3")
    if sha(BASE / "package.json") != "4db327033870b597248a7188ab7f007e1979dafbb330edc58a4f052b6a086e00":
        raise ValueError("prospective composition drift")
    destination.mkdir(parents=True, exist_ok=True)
    for name, digest in original["files"].items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == "payload/runtime/appspawn-x":
            shutil.copyfile(HOST, path)
        elif not path.is_file():
            shutil.copyfile(BASE / name, path)
        if name != "payload/runtime/appspawn-x" and sha(path) != digest:
            raise ValueError("unrelated candidate package file changed: " + name)
    manifest = dict(original)
    manifest["files"] = dict(original["files"], **{"payload/runtime/appspawn-x": sha(HOST)})
    manifest["rollout_ready"] = False
    save(destination / "package.json", manifest)
    checks = destination / "native-checks"
    if not checks.exists():
        shutil.copytree(BASE / "native-checks", checks)
    scan = json.loads((BASE / "native-checks/scan-manifest.json").read_text())
    for name, source in [("n4-host.c", HERE / "src/candidate-stock-host.c"),
                         ("n11h-owner.h", HERE / "n11h-owner.h")]:
        shutil.copyfile(source, checks / name)
        scan["sources"][name] = dict(path=name, sha256=sha(source), origin=portable(str(source)),
                                     source_sha256=sha(source), first_line=1)
    scan["profiles"].append(dict(name="n11h-resident-owners", rule="namespace", source="n11h-owner.h",
                                  identity=dict(artifact="payload/runtime/appspawn-x")))
    for profile in scan["profiles"]:
        identity = profile["identity"]
        identity.update(package="offline-audit-only", manifest_sha256=sha(destination / "package.json"),
                        artifact_sha256=manifest["files"][identity["artifact"]])
    save(checks / "scan-manifest.json", scan)
    inputs = json.loads((BASE / "native-checks/native-gates.json").read_text())
    inputs["package_manifest_sha256"] = sha(destination / "package.json")
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", inputs)
    return destination


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((HERE / ".artifacts/frozen-r1/build-receipt.json").read_text())
    assert receipt["repeated"][0] == receipt["repeated"][1]
    assert receipt["repeated"][0]["baseline"] == sha(BASE_HOST) == R3_SHA
    assert receipt["repeated"][0]["candidate"] == sha(HOST)
    run("whois", [sys.executable, HARNESS / "scripts/lab/deployed_whois.py", "appspawn-x"])
    for variant, path in [("r3", BASE_HOST), ("candidate", HOST)]:
        run("open-" + variant, [sys.executable, REPO / "scripts/lab/open_site_scan.py", path,
                                "--json", RAW / ("open-" + variant + ".json")])
    run("strings", [sys.executable, HARNESS / "scripts/lab/deployed_strings_diff.py", HOST, "--deployed", BASE_HOST], 1)
    consumers, copies, seen = [], 0, set()
    for path in sorted((BASE / "payload").rglob("*.so")):
        if not path.is_file() or path.is_symlink():
            continue
        copies += 1
        digest = sha(path)
        if digest not in seen:
            seen.add(digest)
            consumers.append(path)
    abi_command = [sys.executable, HARNESS / "scripts/lab/abi_diff.py", "--old", BASE_HOST,
                   "--new", HOST, "--calls", "--json", RAW / "abi.json"]
    for path in consumers:
        abi_command.extend(["--consumer", path])
    run("abi", abi_command)
    abi = json.loads((RAW / "abi.json").read_text())
    assert not (abi["removed"] or abi["added"] or abi["drift"] or abi["consumer_breaks"])
    assert {row["function"] for row in abi["call_diffs"]} == {"StockCreateConfiguredNamespaces", "StockOpenNamespace"}
    readonly = import_file("n11h_readonly", HERE / "elf_readonly.py")
    old_table, new_table = readonly.normalized_relro(BASE_HOST), readonly.normalized_relro(HOST)
    assert old_table == new_table
    tags = []
    for variant, path in [("r3", BASE_HOST), ("candidate", HOST)]:
        text = run("dynamic-" + variant, ["llvm-readelf", "-d", "--wide", path])
        tags.append([line.split(")", 1)[1].strip() for line in text.splitlines()
                     if any("(" + tag + ")" in line for tag in ["NEEDED", "SONAME", "RPATH", "RUNPATH", "FLAGS", "FLAGS_1", "INIT_ARRAYSZ", "FINI_ARRAYSZ"])])
    assert tags[0] == tags[1]
    old_ro, new_ro = readonly.rodata_strings(BASE_HOST), readonly.rodata_strings(HOST)
    old_private = "liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so"
    dropped = old_ro - new_ro
    assert dropped == {old_private,
                       str(REPO / "benchmark/2026-10-01-u10-native-shims/.artifacts/host-r3/candidate-stock-host.c"),
                       str(REPO / "benchmark/2026-10-01-u10-native-shims/host-r3/resident-compat.h")}
    assert old_private + ":liboh_adapter_bridge.so" in new_ro
    save(RAW / "readonly.json", dict(relro_unchanged=True, relro=new_table, dynamic_tags_unchanged=True,
                                     dynamic_tags=tags[1], rodata_added=sorted(new_ro - old_ro), rodata_dropped=sorted(dropped)))
    old_scan = json.loads((RAW / "open-r3.json").read_text())
    new_scan = json.loads((RAW / "open-candidate.json").read_text())
    old_after = [row for row in old_scan["findings"] if row["kind"] == "INHERIT-AFTER-OPEN"]
    assert len(old_after) == 4
    assert not [row for row in new_scan["findings"] if row["kind"] in {"INHERIT-REPEAT", "INHERIT-AFTER-OPEN"}]
    binary = new_scan["binaries"][0]
    fresh = [row for row in binary["sites"] if row["function"] == "StockCreateConfiguredNamespaces" and not any("NOLOAD" in value for value in row["flags"])]
    first_open = min(int(row["pc"], 16) for row in fresh)
    sealed = [row for row in binary["namespace_edges"] if row["callee"] == "dlns_inherit" and row["parent_identity"] == ["name:westlake.sealed.child"]]
    assert len(sealed) == 2 and all(int(row["pc"], 16) < first_open for row in sealed)
    mapping = {"0xcfc8": "0xd464", "0xcffc": "0xd480"}
    comparisons = [dict(row, candidate_inherit_pc=mapping[row["site"].split("@")[-1]],
                        candidate_open_pc="0xd640" if row["open_pc"] == "0xd13c" else "0xd6e4",
                        changed=True, candidate_reachable_after_open=False,
                        reason="app->bridge and optional compat inheritance now precede bootstrap/runtime/audio/ABI loads; no returning CFG path reaches either inherit")
                   for row in old_after]
    package = prepare_package()
    tool = HARNESS / "scripts/lab/native_predeploy.py"
    baseline_output = run("native-r3", [sys.executable, tool, "--package", BASE,
                                       "--inputs", BASE / "native-checks/native-gates.json"], (0, 1))
    output = run("native-candidate", [sys.executable, tool, "--package", package,
                                      "--inputs", package / "native-checks/native-gates.json"], 1)
    native, baseline_native = json.loads(output), json.loads(baseline_output)
    assert native["status"] == "REJECT" and not native["errors"]
    assert native["gates"]["N1"]["excepted"] == 0 and native["gates"]["N1"]["rejected"] > 0
    assert native["gates"]["N2"]["details"] == baseline_native["gates"]["N2"]["details"]
    n2_findings = lambda report: [{key: value for key, value in row.items() if key not in {"issue_id", "disposition", "exception"}}
                                  for row in report["gates"]["N2"]["findings"]]
    assert n2_findings(native) == n2_findings(baseline_native)
    summary = dict(baseline_sha256=R3_SHA, candidate_sha256=sha(HOST), two_identical_builds=True,
                   tool_hashes={portable(str(path)): sha(path) for path in [
                       REPO / "scripts/lab/open_site_scan.py", HARNESS / "scripts/lab/deployed_whois.py",
                       HARNESS / "scripts/lab/deployed_strings_diff.py", HARNESS / "scripts/lab/abi_diff.py",
                       HARNESS / "scripts/lab/native_predeploy.py", HARNESS / "scripts/lab/native_initialization_gate.py",
                       HARNESS / "scripts/lab/native_needed_gate.py", HARNESS / "scripts/lab/native_gate_common.py"]},
                   inherit_repeat=0, inherit_after_open=0, sealed_edges_before_fresh_open=len(sealed),
                   sealed_edges=sealed, first_fresh_open_pc=hex(first_open), r3_after_open_comparison=comparisons,
                   abi_consumer_breaks=0, payload_consumer_copies=copies, distinct_payload_consumers=len(consumers),
                   unrelated_call_diffs=0, call_diffs=abi["call_diffs"], relro_bytes=new_table["size"],
                   relro_pointer_relocations=len(new_table["references"]), policy_sha256=sha(BASE / "payload/android/lib64/libnativeloader.so"),
                   all_other_package_files_unchanged=True, rollout_ready=False, device_io=False,
                   n2_exact_details_and_findings_unchanged=True,
                   new_n1_findings=[row for row in native["gates"]["N1"]["findings"] if row["profile"] == "n11h-resident-owners"],
                   dynamic_single_owner_proven=False,
                   native_predeploy=dict(status=native["status"], exit_code=native["exit_code"],
                                         package_manifest_sha256=native["package_manifest_sha256"], inputs_sha256=native["inputs_sha256"],
                                         gates={name: {key: value[key] for key in ["rejected", "excepted", "stale"]} for name, value in native["gates"].items()}),
                   baseline_native_predeploy={name: {key: value[key] for key in ["rejected", "excepted", "stale"]} for name, value in baseline_native["gates"].items()},
                   audit_package=portable(str(package)), commands=COMMANDS)
    save(HERE / "results.json", summary)
    save(RAW / "commands.json", COMMANDS)
    for name, gate in native["gates"].items():
        print(name + " status=" + ("REJECT" if gate["rejected"] else "PASS") +
              " rejected=" + str(gate["rejected"]) + " excepted=" + str(gate["excepted"]) + " stale=" + str(len(gate["stale"])))
    print("AUDIT COMPLETE: static/ABI/consumer/replay handoff; NO deployment authorization; unapproved N1 findings preserved")


if __name__ == "__main__":
    main()
