import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
UPSTREAM = WS / "vm-copies/westlake-current"
KEYS = ["fd-fluffychat", "fd-immich", "fd-kitchenowl", "fd-libre", "fd-saber", "localsend", "cv2-org-linaro-glmark2", "subwaysurfers"]


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else Path(value).read_bytes()).hexdigest()


def portable(value):
    return str(value).replace(str(REPO), "$REPO").replace(str(WS), "$WORKSPACES").replace(str(Path.home()), "$HOME")


def expand(value):
    return Path(value.replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO)).replace("$HOME", str(Path.home())))


def run(name, command):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True)
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(result.stdout + result.stderr)
    (HERE / "evidence" / raw.name).write_text(portable(raw.read_text()))
    if result.returncode:
        raise RuntimeError(name + ": " + result.stderr)
    return dict(command=[portable(value) for value in command], raw_sha256=sha(raw), raw_path=portable(raw), evidence="evidence/" + raw.name)


def main():
    for name in ["evidence", ".artifacts"]:
        (HERE / name).mkdir(exist_ok=True)
    sources_path = MASTER / "benchmark/2026-10-02-candidate-first-fatal-clusters/sources.json"
    sources = json.loads(sources_path.read_text())
    inventory_path = REPO / "benchmark/2026-10-02-toutiao-bionic-scope/consumers.json"
    inventory = {row["key"]: row for row in json.loads(inventory_path.read_text())["apps"]}
    sys.path.insert(0, str(MASTER / "scripts/lab"))
    import first_fatal
    rows = []
    for key in KEYS:
        folder = expand(sources[key])
        record, events, pids, reports, disappeared, pins = first_fatal.load_run(folder)
        fatal = first_fatal.analyze(events, pids, reports, disappeared)
        fingerprint = folder.parent / "runtime-fingerprint.txt"
        fingerprint_text = fingerprint.read_text()
        for digest, name in [("9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db", "libandroid.so"),
                             ("ac59dec077195bc7678c712505b0d802c56e07edea8d049be4a188d20485b7bf", "liboh_android_runtime.so")]:
            if digest + "  /system/android/lib64/" + name not in fingerprint_text:
                raise ValueError("wrong native baseline for " + key)
        terminal = fatal["terminal"]["event"]
        if terminal["pid"] not in pids or "signo(6)" not in terminal["message"]:
            raise ValueError("wrong candidate attempt: " + key)
        lines = (folder / "hilog.txt").read_text(errors="replace").splitlines()
        root = fatal["root"]
        header = root["report"]["header"]["line"]
        crash_lines = []
        for number in range(header, min(header + 180, len(lines)) + 1):
            text = lines[number - 1]
            crash_lines.append(dict(line=number, text=text))
            if "Registers:" in text:
                break
        frames = [row for row in crash_lines if re.search(r"#\d+ pc ", row["text"])]
        app_frame = next(row for row in frames if "/data/app/" in row["text"])
        match = re.search(r"pc\s+([0-9a-f]+)\s+(/data/app/[^\s(]+)", app_frame["text"])
        address, basename = int(match[1], 16), Path(match[2]).name
        app = inventory[key]
        if record["apk_sha256"] != app["apk_sha256"] or record["package"] != app["package"]:
            raise ValueError("run APK identity mismatch")
        member = next(row for row in app["members"] if row["status"] == "ELF64-AArch64" and Path(row["member"]).name == basename)
        installed = [row for row in record.get("native_assembly", {}).get("files", []) if row["name"] == basename]
        if installed and (not installed[0].get("verified") or installed[0]["sha256"] != member["sha256"]):
            raise ValueError("installed native member mismatch")
        apk = expand(app["path"])
        if sha(apk) != app["apk_sha256"]:
            raise ValueError("APK mismatch")
        with zipfile.ZipFile(apk) as archive:
            data = archive.read(member["member"])
        if sha(data) != member["sha256"]:
            raise ValueError("member mismatch")
        binary = HERE / ".artifacts" / (key + "-" + basename)
        binary.write_bytes(data)
        disassembly = run(key + "-caller", ["llvm-objdump", "-d", "--demangle", "--start-address=" + hex(address - 40), "--stop-address=" + hex(address + 20), binary])
        dynamic = run(key + "-dynamic", ["llvm-readelf", "-d", binary])
        notes = run(key + "-build-id", ["llvm-readelf", "-n", binary])
        build_id = re.search(r"\(([0-9a-f]{32,64})\)\s*$", app_frame["text"])[1]
        if build_id not in (HERE / notes["evidence"]).read_text():
            raise ValueError("crash BuildID mismatch")
        preceding = [dict(line=event["line"], text=event["text"]) for event in events if event["pid"] in pids and
                     event["line"] < terminal["line"] and event["level"] in {"F", "E"}][-20:]
        abort_messages = [dict(line=number, text=text) for number, text in enumerate(lines, 1)
                          if re.search(r"Abort message|AbortMessage|JNI DETECTED ERROR|JNI FATAL", text, re.I)]
        library_errors = [dict(line=event["line"], text=event["text"]) for event in events if event["pid"] in pids and
                          event["line"] < terminal["line"] and re.search(r"libsurface\.z\.so|preload.*libandroid|libandroid.*preload|VKQUALITY|FATAL|Error loading shared library|no inherits", event["message"], re.I)]
        excerpt = {row["line"]: row["text"] for row in [*preceding, *abort_messages, *library_errors, *crash_lines, dict(line=terminal["line"], text=terminal["text"])]}
        evidence = "evidence/" + key + "-hilog.txt"
        (HERE / evidence).write_text(portable("\n".join(str(number) + ": " + text for number, text in sorted(excerpt.items()))) + "\n")
        row = dict(key=key, run=sources[key], pid=terminal["pid"], tid=terminal["tid"], signal_line=terminal["line"],
            pins=pins, runtime_fingerprint_path=portable(fingerprint), runtime_fingerprint_sha256=sha(fingerprint),
            root_runtime_hashes_verified=True, terminal=terminal, bound_report_header=root["report"]["header"], frames=frames,
            abort_message="not captured" if not abort_messages else abort_messages,
            faultlogs=[dict(path=portable(path), sha256=sha(path)) for path in (folder / "faultlogs").glob("*") if path.is_file()],
            app_caller=app_frame, caller_pc=hex(address), member=member["member"], member_sha256=member["sha256"],
            apk_sha256=app["apk_sha256"], run_apk_identity_verified=True, installed_native_receipt_matched=bool(installed),
            crash_build_id=build_id, build_id_verified=True, build_id_evidence=notes, disassembly=disassembly, dynamic=dynamic,
            last_app_FE=preceding, loader_evidence=library_errors, evidence=evidence,
            observable_abort_site="ART FatalError" if key == "subwaysurfers" else "ART JniAbort <- GetLongField <- app",
            exact_future_first_fatal="unknown; no post-repair run")
        rows.append(row)
        print(key + " SIGABRT hilog:" + str(terminal["line"]) + " " + row["observable_abort_site"] + " caller=" + basename + ":" + hex(address), flush=True)
    (HERE / "observations.json").write_text(portable(json.dumps(dict(source_commit="2aa6c49df0", sources_sha256=sha(sources_path), inventory_sha256=sha(inventory_path), keys=8,
        execution_enabled=False, device_io=False, rows=rows), indent=2)) + "\n")
    for revision in ["b24a118", "cea21e0", "f20217a", "bbcb25d"]:
        run("upstream-" + revision, ["git", "-C", UPSTREAM, "show", "--format=fuller", revision])
    donor_search = run("upstream-media-history", ["git", "-C", UPSTREAM, "log", "--all", "--oneline", "--grep=mediandk", "--grep=Unity", "-i"])
    for name in ["libandroid.so", "liboh_android_runtime.so"]:
        run("whois-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py", name, "--generation",
            WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload"])
    payload = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload/android/lib64"
    providers = []
    for name, address in [("libandroid.so", 0x7d9d8), ("liboh_android_runtime.so", 0x1db7a4)]:
        binary = payload / name
        disassembly = run("converter-" + name, ["llvm-objdump", "-d", "--demangle", "--start-address=" + hex(address), "--stop-address=" + hex(address + 24), binary])
        symbols = run("symbols-" + name, ["llvm-nm", "-D", "--defined-only", binary])
        providers.append(dict(name=name, path=portable(binary), sha256=sha(binary), converter_pc=hex(address), disassembly=disassembly, symbols=symbols))
    run("subwaysurfers-load-path", ["llvm-objdump", "-d", "--demangle", "--start-address=0x4cd8", "--stop-address=0x4e20", HERE / ".artifacts/subwaysurfers-libmain.so"])
    run("subwaysurfers-string-data", ["llvm-objdump", "-s", "--section=.rodata", HERE / ".artifacts/subwaysurfers-libmain.so"])
    unity = next(member for member in inventory["subwaysurfers"]["members"] if member["member"] == "lib/arm64-v8a/libunity.so")
    with zipfile.ZipFile(expand(inventory["subwaysurfers"]["path"])) as archive:
        data = archive.read(unity["member"])
    if sha(data) != unity["sha256"]:
        raise ValueError("Unity identity mismatch")
    unity_binary = HERE / ".artifacts/subwaysurfers-libunity.so"
    unity_binary.write_bytes(data)
    run("subwaysurfers-unity-needed", ["llvm-readelf", "-d", unity_binary])
    run("subwaysurfers-unity-symbols", ["llvm-readelf", "--dyn-syms", "-W", unity_binary])
    snapshots = []
    for revision, source in [("b24a118", "framework/webview-shim/android_asset_manager_bridge.cpp"), ("b24a118", "tools/build_asset_bridge.sh")]:
        data = subprocess.check_output(["git", "-C", UPSTREAM, "show", revision + ":" + source])
        target = HERE / "evidence" / (revision + "-" + Path(source).name)
        target.write_bytes(data)
        snapshots.append(dict(commit=subprocess.check_output(["git", "-C", UPSTREAM, "rev-parse", revision], text=True).strip(), source=source,
            sha256=sha(data), snapshot="evidence/" + target.name))
    (HERE / "providers.json").write_text(json.dumps(dict(rows=providers, upstream_snapshots=snapshots,
        unity_member_sha256=unity["sha256"], actual_AAsset_GOT_owner="unknown; no relocation-owner capture for these dead processes",
        upstream_head=subprocess.check_output(["git", "-C", UPSTREAM, "rev-parse", "HEAD"], text=True).strip(),
        media_history_search=donor_search, execution_enabled=False), indent=2) + "\n")
    references = []
    for label, path, ranges in [
        ("aosp14-cache", WS / "westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/jni/android_util_AssetManager.cpp", [(1548, 1565)]),
        ("upstream-cache", UPSTREAM / "framework/android-runtime/src/android_util_AssetManager_aosp.cpp", [(139, 148), (1634, 1652)]),
        ("upstream-owner-routing", UPSTREAM / "framework/webview-shim/libandroid_webview_shim.c", [(415, 450), (470, 476)]),
    ]:
        lines = path.read_text().splitlines()
        excerpt = "\n".join(str(number) + ": " + lines[number - 1] for start, end in ranges for number in range(start, end + 1))
        target = HERE / "evidence" / (label + ".txt")
        target.write_text(excerpt + "\n")
        references.append(dict(path=portable(path), sha256=sha(path), excerpt="evidence/" + target.name, ranges=ranges,
                               deployed_source_reproduction_proof=False))
    (HERE / "source-references.json").write_text(json.dumps(references, indent=2) + "\n")


if __name__ == "__main__":
    main()
