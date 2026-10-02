import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
UPSTREAM = WS / "vm-copies/westlake-current"
PAYLOAD = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload"
FACADE = PAYLOAD / "android/lib64/libOpenSLES.so"
OWNER = WS / "westlake-inputs/oh-system-libs/opensles-5ea-u9/oh-system-lib64-libOpenSLES.so"
HEADERS = WS / "westlake-harness-bms-deploy/bms/src/.work/b87-native/replay-inputs/frozen-sysroot/usr/include"
SDK = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    text = str(value)
    for root, variable in [(REPO, "$REPO"), (WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
        if text == str(root):
            return variable
        text = text.replace(str(root) + "/", variable + "/")
    return text


def save(name, data):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(portable(json.dumps(data, indent=2)) + "\n")


def run(label, command, check=False):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True, cwd=REPO)
    raw = HERE / ".artifacts" / (label + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(result.stdout + result.stderr)
    public = HERE / "evidence" / (label + ".txt")
    public.parent.mkdir(exist_ok=True)
    public.write_text(portable(raw.read_text()))
    print(label + " exit=" + str(result.returncode), flush=True)
    if check and result.returncode:
        raise ValueError("failed experiment: " + label)
    return dict(label=label, command=[portable(value) for value in command], exit_code=result.returncode,
                raw_path=portable(raw), raw_sha256=sha(raw), evidence="evidence/" + public.name, sha256=sha(public))


def main():
    if sha(OWNER) != "05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100":
        raise ValueError("OH real owner changed")
    if sha(FACADE) != "5891f899c2b21dcb24fa2f4cb3db78fbb34597740600c096dd8f633b831c5347":
        actual = subprocess.check_output(["llvm-readelf", "-d", FACADE], text=True)
        print("facade SHA full pin to verify: " + sha(FACADE), actual, flush=True)
        raise ValueError("facade pin mismatch")
    records = []
    commits = []
    for revision in ["0b5c9af", "1e98162", "c7d2992", "5ae6b75"]:
        full = subprocess.check_output(["git", "-C", UPSTREAM, "rev-parse", revision], text=True).strip()
        record = run("commit-" + revision, ["git", "-C", UPSTREAM, "show", "--format=fuller", "--stat", revision], True)
        patch = run("patch-" + revision, ["git", "-C", UPSTREAM, "show", "--format=", revision], True)
        commits.append(dict(commit=full, stat=record, patch=patch))
    for revision, filename, snapshot in [
        ("c7d2992", "framework/webview-shim/opensles_android_adapter.c", "upstream/opensles_android_adapter.c"),
        ("5ae6b75", "framework/javacore-shim/media_natives.c", "upstream/media_natives.c"),
    ]:
        original = subprocess.check_output(["git", "-C", UPSTREAM, "show", revision + ":" + filename])
        if hashlib.sha256(original).hexdigest() != sha(HERE / snapshot):
            raise ValueError("upstream snapshot mismatch")
    for name in ["libOpenSLES.so", "liboh_android_runtime.so", "libnativeloader.so"]:
        records.append(run("whois-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py", name, "--generation", PAYLOAD], True))
    records.append(run("stage", ["python3", HERE / "stage.py"], True))
    frozen_headers = []
    for filename in ["OpenSLES.h", "OpenSLES_Platform.h", "OpenSLES_OpenHarmony.h"]:
        path = HEADERS / "SLES" / filename
        target = HERE / "inputs/SLES" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        frozen_headers.append(dict(path=portable(path), sha256=sha(path), snapshot="inputs/SLES/" + filename))
    host_executable = HERE / ".artifacts/test_adapter"
    records.append(run("host-fixture-compile", ["clang", "-std=gnu11", "-D_GNU_SOURCE", "-I" + str(HERE / "inputs"),
          "-I" + str(HERE), HERE / "test_adapter.c", "-Wl,-undefined,dynamic_lookup", "-o", host_executable], True))
    records.append(run("host-fixture", [host_executable], True))
    compiler = SDK / "llvm/bin/clang"
    if sha(compiler) != "6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1":
        raise ValueError("compiler pin changed")
    candidate = HERE / ".artifacts/libOpenSLES-candidate.so"
    commands = [str(compiler), "--target=aarch64-linux-ohos", "--sysroot=" + str(SDK / "sysroot"), "-fPIC", "-O2", "-g",
                "-D_GNU_SOURCE", "-std=gnu11", "-I" + str(HERE / "inputs"), "-I" + str(HERE),
                "-ffile-prefix-map=" + str(REPO) + "=.", "-shared", "-fuse-ld=lld", "-Wl,-z,defs,-z,now,-z,relro",
                "-Wl,-soname,libOpenSLES.so", "-Wl,--build-id=sha1", HERE / "candidate/opensles_android_adapter.c", "-lc", "-o", candidate]
    repeats = []
    for repeat in [1, 2]:
        records.append(run("build-" + str(repeat), commands, True))
        repeats.append(sha(candidate))
    if repeats[0] != repeats[1]:
        raise ValueError("repeated build drift")
    for name, path in [("deployed", FACADE), ("candidate", candidate)]:
        records.append(run("open-" + name, ["python3", MASTER / "scripts/lab/open_site_scan.py", path,
                     "--json", HERE / ".artifacts" / ("open-" + name + ".json")], True))
        save("evidence/open-" + name + ".json", json.loads((HERE / ".artifacts" / ("open-" + name + ".json")).read_text()))
        records.append(run("dynamic-" + name, ["llvm-readelf", "-d", path], True))
        records.append(run("exports-" + name, ["llvm-nm", "-D", "--defined-only", path], True))
    records.append(run("strings", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", FACADE]))
    inventory = json.loads((REPO / "benchmark/2026-10-02-u11-native-batch/evidence/opensles-consumers.json").read_text())
    raw_members = REPO / "benchmark/2026-10-02-toutiao-bionic-scope/.artifacts/members"
    consumers = []
    for row in inventory["rows"]:
        path = raw_members / (row["sha256"] + ".so")
        if path.is_file() and sha(path) == row["sha256"]:
            consumers.append(path)
    records.append(run("abi", ["python3", MASTER / "scripts/lab/abi_diff.py", "--old", FACADE, "--new", candidate, "--calls",
          *[value for path in sorted(set(consumers)) for value in ["--consumer", path]], "--json", HERE / ".artifacts/abi.json"]))
    save("evidence/abi.json", json.loads((HERE / ".artifacts/abi.json").read_text()))
    ledger_path = MASTER / "benchmark/blockers-ledger.json"
    ledger = json.loads(ledger_path.read_text())
    ledger_rows = [row for row in ledger["blockers"] if row.get("fixed_in") in ["0b5c9af", "1e98162", "c7d2992", "5ae6b75"]]
    save("architecture.json", dict(commits=commits, deployed_facade=sha(FACADE), oh_owner=sha(OWNER),
         framework68_route_A_equivalent=False, upstream_framework_version="68 per outer; historical build not independently activated",
         upstream_snapshots={name: sha(HERE / name) for name in ["upstream/opensles_android_adapter.c", "upstream/media_natives.c"]},
         ledger=dict(path=portable(ledger_path), sha256=sha(ledger_path), historical_rows=ledger_rows, current_batch_unlock_proof=False),
         incomplete=["real PLAY completion", "route-A media owner registration", "canonical backend-handle publication"],
         tools=records, device_io=False, execution_enabled=False))
    save("build-receipt.json", dict(compiler=portable(compiler), compiler_sha256=sha(compiler), sysroot=portable(SDK / "sysroot"),
         libc_link_input_sha256=sha(SDK / "sysroot/usr/lib/aarch64-linux-ohos/libc.so"), frozen_headers=frozen_headers,
         source_sha256=sha(HERE / "candidate/opensles_android_adapter.c"), repeated_sha256=repeats,
         source_recipe="stage.py", candidate=portable(candidate), command=[portable(value) for value in commands],
         status="OFFLINE_PROBE_NOT_OWNER_ADMITTED", consumer_samples=len(set(consumers))))
    print("candidate " + sha(candidate) + " repeated identical; PLAY and media registration remain incomplete", flush=True)


if __name__ == "__main__":
    main()
