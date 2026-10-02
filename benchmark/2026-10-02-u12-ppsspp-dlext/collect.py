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


def capture(name, command, allowed=(0,)):
    try:
        result = subprocess.run([str(value) for value in command], capture_output=True, text=True, errors="replace", timeout=8)
        output, code = result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        output = "TIMEOUT8s; no successful source query; " + str(error)
        code = 124
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(output)
    public_output = portable(output)
    if name.startswith("lookup-"):
        public_output = re.sub(r"\.ssh/sockets/[^)]+", ".ssh/sockets/<host-control-socket>", public_output)
        public_output = re.sub(r"(?<=host )[0-9.]+(?= port)", "<host-address>", public_output)
        public_output = "SSH identity/address redacted; complete raw SHA is recorded.\n" + public_output
    (HERE / "evidence" / raw.name).write_text(public_output)
    if code not in allowed:
        raise ValueError(name + ": " + output)
    return dict(command=[portable(value) for value in command], exit_code=code, raw_sha256=sha(raw))


def main():
    for name in ["inputs", "evidence", ".artifacts"]:
        (HERE / name).mkdir(exist_ok=True)
    records = []
    consumer = REPO / "benchmark/2026-10-02-u12-disappeared/.artifacts/ppsspp-libppsspp_jni.so"
    if sha(consumer) != "8956cbe542ac02607d9f4ceffc50b2db23dfc090f118b9a1cbc0eba456b50f62":
        raise ValueError("actual consumer drift")
    records.append(capture("consumer-calls", ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=0x10b3ec4", "--stop-address=0x10b3f20", consumer]))
    records.append(capture("consumer-fd-call", ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=0x10b4018", "--stop-address=0x10b4064", consumer]))
    records.append(capture("consumer-dynamic-version", ["llvm-readelf", "-d", "-V", consumer]))
    symbol_text = subprocess.check_output(["llvm-readelf", "--dyn-syms", consumer], text=True)
    (HERE / "evidence/consumer-target-symbols.txt").write_text("\n".join(line for line in symbol_text.splitlines() if re.search(r"\b(?:android_dlopen_ext|__errno|strtoll_l|strtoull_l)(?:@|\b)", line)) + "\n")
    compat = BASE / "payload/android/lib64/libbionic_compat.so"
    libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    if sha(compat) != "015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58" or sha(libc) != "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2":
        raise ValueError("deployed/factory identity drift")
    exports = set(subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", compat], text=True).splitlines())
    if "android_dlopen_ext" not in exports:
        raise ValueError("existing export unexpectedly absent")
    records.append(capture("whois-compat", ["python3", MASTER / "scripts/lab/deployed_whois.py", "libbionic_compat.so", "--generation", BASE]))
    scan_path = HERE / "evidence/open-compat.json"
    records.append(capture("open-compat", ["python3", REPO / "scripts/lab/open_site_scan.py", compat, "--json", scan_path]))
    scan_path.write_text(portable(scan_path.read_text()))
    records.append(capture("strings-baseline", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", compat, "--deployed", compat]))
    records.append(capture("compat-dlext", ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=0x373c", "--stop-address=0x37c0", compat]))
    factory_symbols = subprocess.check_output(["llvm-readelf", "--dyn-syms", libc], text=True)
    relevant = [line for line in factory_symbols.splitlines() if "dlopen_ext" in line or "dlopen_ns_ext" in line or "__loader_android" in line]
    (HERE / "evidence/factory-backends.txt").write_text("\n".join(relevant) + "\n")
    package = json.loads((BASE / "package.json").read_text())
    providers = []
    queried = []
    for relative, digest in package["files"].items():
        path = BASE / relative
        if not relative.endswith(".so") or path.read_bytes()[:4] != b"\x7fELF":
            continue
        if sha(path) != digest:
            raise ValueError("package backend-scan drift")
        symbols = subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", path], text=True, stderr=subprocess.DEVNULL).splitlines()
        queried.append(dict(path=relative, sha256=digest))
        if "__loader_android_dlopen_ext" in symbols:
            providers.append(relative)
    save("backend-scan.json", dict(package_manifest_sha256=sha(BASE / "package.json"), queried=queried,
         providers=providers, factory_libc_has_backend="__loader_android_dlopen_ext" in factory_symbols,
         scope="all package ELF .so aliases and exact factory libc; not a complete live system-library mapping proof"))
    source = WS / "westlake-inputs/aosp-14.0.0_r1-src/bionic/libdl/libdl.cpp"
    (HERE / "inputs/libdl.cpp").write_bytes(source.read_bytes())
    for name in ["android_dlopen_ext.c", "android_dlext_abi.h"]:
        original = REPO / "benchmark/2026-10-01-u10-native-shims/overlay" / name
        (HERE / "inputs" / name).write_bytes(original.read_bytes())
    save("sources.json", dict(files=[dict(path="inputs/" + path.name, sha256=sha(path)) for path in sorted((HERE / "inputs").iterdir()) if path.is_file()],
         origin="local verified AOSP14 libdl public wrapper and accepted U10 overlay source, not a real linker backend"))
    prior = json.loads((REPO / "benchmark/2026-10-02-u12-disappeared/observations.json").read_text())
    row = next(row for row in prior["rows"] if row["key"] == "ppsspp")
    hilog = Path(row["run"].replace("$WORKSPACES", str(WS))) / "hilog.txt"
    if sha(hilog) != row["hashes"]["hilog.txt"]:
        raise ValueError("run drift")
    lines = hilog.read_text(errors="replace").splitlines()
    numbers = [30637, 30638, 30781, 30855, 30857, 30859, 30860, 30861, 32594, 32947]
    (HERE / "evidence/ppsspp-hilog.txt").write_text("\n".join(str(number) + ": " + portable(lines[number - 1]) for number in numbers) + "\n")
    lookups = []
    remote = 'test -n "$AOSP14_SOURCE_ROOT" && test -r "$AOSP14_SOURCE_ROOT/bionic/linker/linker.cpp"'
    for host in ["a2hlab", "hw248"]:
        lookups.append(capture("lookup-" + host, ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", host, remote], allowed=(0, 1, 124, 255)))
    save("results.json", dict(key="ppsspp", execution_enabled=False, new_native_artifact=False, rollback="no payload changed",
         consumer_sha256=sha(consumer), compat_sha256=sha(compat), factory_libc_sha256=sha(libc),
         current_wall="app libppsspp_jni cannot relocate android_dlopen_ext@LIBC despite resident015aa exporting it",
         evidence=dict(run=row["run"], hilog_sha256=sha(hilog), lines=numbers),
         calls=[dict(pc="0x10b3ef8", flags="0x200", semantics=["USE_NAMESPACE"], extinfo_null=False),
                dict(pc="0x10b405c", flags="0x210", semantics=["USE_NAMESPACE", "USE_LIBRARY_FD"], extinfo_null=False)],
         force_load="0x40, absent from these two calls; earlier FORCE_LOAD label was incorrect",
         backend_status="existing wrapper forwards only to weak __loader_android_dlopen_ext; not exported by factory libc; OH dlopen_ext/dlopen_ns_ext exist but Android namespace identity/FD ABI translation is unproven",
         local_source="AOSP14 libdl.cpp only forwards to linker backend; no matching backend/namespace mapping in local verified inputs",
         source_lookups=lookups, records=records, standalone_first_fatal_move=0, conditional_target_count=1,
         remaining_static_imports=[name for name in ["__errno", "strtoll_l", "strtoull_l"] if name not in exports],
         next_exact_fatal="unknown", t20="unknown",
         plan="coordinate app saved-scope proof first; then provide real namespace identity and FD-aware loader backend as separate verified change; do not cast Android namespace pointers to OH Dl_namespace or silently ordinary-dlopen nonzero flags",
         expect=dict(confirm="real app relocation binds the resident wrapper and nonzero namespace/FD calls dispatch to a verified matching backend",
                     refute="old ULE remains, or U10-DLEXT backend absent refusing0x200/0x210 appears; neither counts as full repair")))
    print("PPSSPP: existing export, unresolved app scope, real namespace/FD backend absent; standalone prediction0, no fake candidate")


if __name__ == "__main__":
    main()
