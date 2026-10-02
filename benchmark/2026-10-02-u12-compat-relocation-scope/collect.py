import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
BASE = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    text = str(value)
    for root, variable in [(REPO, "$REPO"), (WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
        if text == str(root):
            return variable
        text = text.replace(str(root) + "/", variable + "/")
    return text


def save(name, value):
    (HERE / name).write_text(portable(json.dumps(value, indent=2)) + "\n")


def capture(name, command):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True, errors="replace")
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(result.stdout + result.stderr)
    (HERE / "evidence" / raw.name).write_text(portable(raw.read_text()))
    if result.returncode:
        raise RuntimeError(name + ": " + result.stderr)
    return dict(command=[portable(value) for value in command], exit_code=result.returncode, raw_sha256=sha(raw))


def main():
    for name in ["evidence", "inputs", ".artifacts"]:
        (HERE / name).mkdir(exist_ok=True)
    receipt_path = WS / "westlake-generation-u9-j10g-238ffc14/native/receipts/ROUTE_A_INPUTS.json"
    inputs = {row["path"]: row for row in json.loads(receipt_path.read_text())["files"]}
    source_paths = {
        "app_native_loader.c": WS / "westlake-harness-bms-deploy/bms/src/.work/b67-generation/adapter/framework/app-native-loader/src/app_native_loader.c",
        "native_loader_registry.cpp": WS / "westlake-inputs/generations/u10.1-policy-repro/native-loader-u10.1/src/native_loader_registry.cpp",
        "stock-host.c": REPO / "benchmark/2026-10-02-u11-native-batch/inputs/host-r3/candidate-stock-host.c",
        "resident-compat.h": REPO / "benchmark/2026-10-02-u11-native-batch/inputs/host-r3/resident-compat.h",
    }
    sources = []
    for name, path in source_paths.items():
        source_sha = sha(path)
        receipt_key = next((key for key in inputs if key.endswith("/" + name)), None)
        if name in {"app_native_loader.c", "native_loader_registry.cpp"}:
            if receipt_key is None or inputs[receipt_key]["sha256"] != source_sha:
                raise ValueError("exact deployed source mismatch: " + name)
        (HERE / "inputs" / name).write_bytes(path.read_bytes())
        sources.append(dict(path=portable(path), sha256=source_sha, snapshot="inputs/" + name,
                            receipt_key=receipt_key, receipt_sha256=sha(receipt_path) if receipt_key else None,
                            provenance_limit="receipt-matched pre-override input, not reproduced eebd62f2 full source" if name == "app_native_loader.c" else None))
    binaries = {
        "host": BASE / "payload/runtime/appspawn-x",
        "anl": BASE / "payload/android/lib64/libapp_native_loader.so",
        "loader": BASE / "payload/android/lib64/libnativeloader.so",
        "compat": BASE / "payload/android/lib64/libbionic_compat.so",
    }
    identities = {}
    for name, path in binaries.items():
        identities[name] = dict(path=portable(path), sha256=sha(path))
        capture("whois-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py", path.name,
                                  "--generation", BASE])
        scan_path = HERE / "evidence" / ("open-" + name + ".json")
        capture("open-" + name, ["python3", REPO / "scripts/lab/open_site_scan.py", path, "--json", scan_path])
        scan_path.write_text(portable(scan_path.read_text()))
        capture("strings-" + name, ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", path, "--deployed", path])
        capture("dynamic-" + name, ["llvm-readelf", "-d", "-V", path])
    capture("anl-create", ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=0x31f4", "--stop-address=0x3634", binaries["anl"]])
    capture("anl-open", ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=0x3c6c", "--stop-address=0x4110", binaries["anl"]])
    exports = set(subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", binaries["compat"]], text=True).splitlines())
    if "__gnu_strerror_r" not in exports:
        raise ValueError("actual compat GNU export missing")
    prior = json.loads((REPO / "benchmark/2026-10-02-u12-disappeared/observations.json").read_text())
    rows = []
    for key in ["fd-fennec_fdroid", "firefox"]:
        row = next(row for row in prior["rows"] if row["key"] == key)
        folder = Path(row["run"].replace("$WORKSPACES", str(WS)))
        hilog = folder / "hilog.txt"
        if sha(hilog) != row["hashes"]["hilog.txt"]:
            raise ValueError("raw run changed")
        pid = row["pids"][0]["pid"]
        selected = []
        for number, line in enumerate(hilog.read_text(errors="replace").splitlines(), 1):
            match = re.match(r"\S+\s+\S+\s+(\d+)\s+(\d+)\s+[A-Z]\s+", line)
            app_match = match and int(match[1]) == pid
            if (app_match and any(value in line for value in ["owner_verified", "native namespace created", "__gnu_strerror_r", "libmozglue", "westlake.anl."])) or number == row["pids"][0]["status"]["line"]:
                selected.append(dict(line=number, text=line))
        owner_rows = [event for event in selected if "owner_verified" in event["text"]]
        relocation = [event for event in selected if "reloc" in event["text"] and "__gnu_strerror_r" in event["text"]]
        first_error = min(event["line"] for event in relocation)
        preceding = [event for event in owner_rows if event["line"] < first_error]
        addresses = set(re.findall(r"gnu=([0-9A-Fa-f]+)", "\n".join(event["text"] for event in preceding)))
        if len(preceding) != 3 or len(addresses) != 1:
            raise ValueError("resident counterexample changed")
        (HERE / "evidence" / (key + "-hilog.txt")).write_text("\n".join(str(event["line"]) + ": " + portable(event["text"]) for event in selected) + "\n")
        consumer = REPO / "benchmark/2026-10-02-u12-disappeared/.artifacts" / (key + "-libmozglue.so")
        capture(key + "-dynamic-version", ["llvm-readelf", "-d", "-V", consumer])
        symbol_text = subprocess.check_output(["llvm-readelf", "--dyn-syms", consumer], text=True)
        relevant = [line for line in symbol_text.splitlines() if any(value in line for value in ["__gnu_strerror_r", "strtoll_l", "strtoull_l", "__pthread_cleanup_"])]
        (HERE / "evidence" / (key + "-symbols.txt")).write_text("\n".join(relevant) + "\n")
        rows.append(dict(key=key, pid=pid, run=row["run"], hilog_sha256=sha(hilog), consumer_sha256=sha(consumer),
                         preceding_owner_logs=preceding, same_gnu_address=next(iter(addresses)), relocation_errors=relocation,
                         terminal=row["pids"][0]["status"], requested_version="LIBC, libc.so, hash0x50d63",
                         namespace="ANL app namespace: actual non-libflutter branch passes domain+0 at406c/40bc; numeric domain id is not logged on this failing call",
                         same_constructor_as_b8=True, same_namespace_instance_as_b8="not established; per-ClassLoader domain instances",
                         candidate_next_missing_symbols=[name for name in ["strtoll_l", "__pthread_cleanup_push", "__pthread_cleanup_pop"]
                                                         if name not in exports and any(name + "@LIBC" in line for line in relevant)],
                         observed_first_fatal_moved=0, conditional_first_fatal_moved=1, next_exact_fatal="unknown", t20="unknown"))
    for name in ["oh-libc-saved-scope.txt", "oh-libc-retain-chain.txt", "oh-libc-check-version.txt", "oh-libc-decode-dyn.txt"]:
        source = REPO / "benchmark/2026-10-02-toutiao-bionic-scope/evidence" / name
        (HERE / "evidence" / name).write_bytes(source.read_bytes())
    save("sources.json", dict(lookup="local receipt-matched source references and actual deployed ELF found; no remote fallback used", files=sources,
         rejected_live_anl_source_sha256="ce216b5a10ff6eb9e1146762a2b5c0c30718238788b050780ecb25b1a92727df",
         anl_provenance_limit="ROUTE_A_INPUTS cc0b48 source predates deployed eebd62 flutter override: ELF contains flutter_prepare and third namespace absent from that input. Do not claim full source reproduction; app dispatch is independently established from ELF406c/40bc, versus flutter domain+0x100 at40b0.",
         factory_libc_sha256="fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2",
         factory_libc_source_provenance="none; disassembly behavior only, reference musl source is not same-source"))
    save("results.json", dict(rows=rows, identities=identities, execution_enabled=False,
         new_native_artifact=False, runtime_variable_changed=0, rollback="no payload changed",
         proven_first_fatal_moved=0, conditional_scope_targets=2,
         coordination="cc-wiki N11h-r2 common host namespace construction; preserve/merge existing compat-owner edge, not a second inherit; bridge/runtime single-copy alone does not prove compat saved relocation scope",
         status="owner-resolution proof pending; no competing namespace patch or unverified global promotion",
         build="not applicable: no new artifact; audited exact deployed ELF bytes",
         expect=dict(confirm="actual app libmozglue relocation binds GNU to the already-resident compat owner; GNU ULE absent before the app terminal",
                     refute="owner_verified remains green but GNU reloc failure persists, as in both exact baseline runs")))
    print("Gecko: app-domain consumer; 3 resident GNU queries precede each failure; 0 proven / 2 conditional moves; no parallel inherit patch")


if __name__ == "__main__":
    main()
