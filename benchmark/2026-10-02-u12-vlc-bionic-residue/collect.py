import hashlib
import json
import os
from pathlib import Path
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
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True, errors="replace")
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(result.stdout + result.stderr)
    (HERE / "evidence" / raw.name).write_text(portable(raw.read_text()))
    if result.returncode not in allowed:
        raise RuntimeError(name + ": " + result.stderr)
    return dict(command=[portable(value) for value in command], exit_code=result.returncode, raw_sha256=sha(raw))


def main():
    for name in ["inputs", "evidence", ".artifacts"]:
        (HERE / name).mkdir(exist_ok=True)
    libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    if sha(libc) != "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2":
        raise ValueError("factory libc changed")
    capture("oh-cleanup", ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=0x12de84", "--stop-address=0x12dec4", libc])
    capture("oh-thread-exit", ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=0x12f240", "--stop-address=0x12f290", libc])
    capture("whois-compat", ["python3", MASTER / "scripts/lab/deployed_whois.py", "libbionic_compat.so", "--generation", BASE])
    sources = []
    expected_sources = {"stdlib_l.cpp": "7399803737fc7c004f4af3a12be5d77a3c52846b3a8519a172fa275cfea857a6",
                        "pthread_exit.cpp": "99db1e4ffba6ce12f1280def244c89791c119f447a71f0261b33396ecb33f5c7"}
    for name in expected_sources:
        source = WS / "westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic" / name
        if sha(source) != expected_sources[name]:
            raise ValueError("verified AOSP14 source drift")
        target = HERE / "inputs" / name
        target.write_bytes(source.read_bytes())
        sources.append(dict(path=portable(source), sha256=sha(source), snapshot="inputs/" + name,
                            origin="AOSP android-14.0.0_r1; copied local verified source", semantic_lines=[49, 57] if name == "stdlib_l.cpp" else [52, 79]))
    prior = json.loads((REPO / "benchmark/2026-10-02-u12-disappeared/observations.json").read_text())
    row = next(row for row in prior["rows"] if row["key"] == "vlc")
    hilog = Path(row["run"].replace("$WORKSPACES", str(WS))) / "hilog.txt"
    if sha(hilog) != row["hashes"]["hilog.txt"]:
        raise ValueError("VLC raw evidence changed")
    lines = hilog.read_text(errors="replace").splitlines()
    numbers = [19447, 19449, 19450, 19606, 24281, 24283, 24284, 24375]
    (HERE / "evidence/vlc-hilog.txt").write_text("\n".join(str(number) + ": " + portable(lines[number - 1]) for number in numbers) + "\n")
    android_header = Path.home() / "Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include/pthread.h"
    (HERE / "evidence/android-cleanup-layout.txt").write_text("\n".join(str(number) + ": " + line for number, line in enumerate(android_header.read_text().splitlines(), 1) if 363 <= number <= 387) + "\n")
    save("sources.json", dict(lookup="local AOSP14 source and factory OH ELF found; no remote source substitution",
         sources=sources, android_header=dict(path=portable(android_header), sha256=sha(android_header), origin="NDK23 header layout reference, not falsely AOSP14 header"),
         factory_libc=dict(path=portable(libc), sha256=sha(libc), source_provenance="none; binary behavior only"),
         upstream_explicit_pop_donor_rejected="webview_bionic_shim.c has TLS explicit-pop-only implementation, not full thread-exit cleanup",
         evidence=dict(run=row["run"], hilog_sha256=sha(hilog), lines=numbers)))
    print("VLC: true AOSP conversion; Android24 layout differs from OH24; real OH cleanup stack push/pop and thread-exit loop pinned")


if __name__ == "__main__":
    main()
