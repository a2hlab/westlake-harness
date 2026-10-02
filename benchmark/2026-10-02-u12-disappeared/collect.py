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
KEYS = ["burgerking", "cv2-com-kaajjo-libresudoku", "fd-fennec_fdroid", "firefox", "ppsspp", "vlc"]
EXIT = re.compile(r"(?P<package>[\w.]+) with pid (?P<pid>\d+) exit with (?P<kind>code|signal):(?P<value>\d+)")
SYMBOLS = ["__gnu_strerror_r", "android_dlopen_ext", "strtoll_l", "__pthread_cleanup_push", "__pthread_cleanup_pop"]


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else Path(value).read_bytes()).hexdigest()


def portable(value):
    return str(value).replace(str(REPO), "$REPO").replace(str(WS), "$WORKSPACES").replace(str(Path.home()), "$HOME")


def expand(value):
    return Path(value.replace("$REPO", str(REPO)).replace("$WORKSPACES", str(WS)).replace("$HOME", str(Path.home())))


def exit_status(event, package, pids):
    match = EXIT.search(event["message"])
    if not match or match["package"] != package or int(match["pid"]) not in pids or "APPSPAWN" not in event["tag"]:
        return None
    return dict(line=event["line"], timestamp=event["timestamp"], reporter_pid=event["pid"],
                pid=int(match["pid"]), kind=match["kind"], value=int(match["value"]), text=event["text"])


def capture(name, command):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True, errors="replace")
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(result.stdout + result.stderr)
    evidence = HERE / "evidence" / raw.name
    evidence.write_text(portable(raw.read_text()))
    if result.returncode:
        raise RuntimeError(name + ": " + result.stderr)
    return dict(command=[portable(value) for value in command], raw_path=portable(raw), raw_sha256=sha(raw),
                evidence="evidence/" + raw.name)


def scan_dex(key, apk, archive):
    tool = Path.home() / "Library/Android/sdk/build-tools/37.0.0/dexdump"
    members = []
    retained = []
    for name in archive.namelist():
        if not re.fullmatch(r"classes\d*\.dex", name):
            continue
        data = archive.read(name)
        path = HERE / ".artifacts" / (key + "-" + name)
        path.write_bytes(data)
        process = subprocess.Popen([str(tool), "-d", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, errors="replace")
        owner = method = ""
        block = []
        counter = 0

        def finish():
            if not block:
                return
            text = "\n".join(row["text"] for row in block)
            targets = [target for target in ["Ljava/lang/System;.exit:", "Landroid/os/Process;.killProcess:"] if target in text]
            focused = (key == "ppsspp" and owner == "Lorg/ppsspp/ppsspp/PpssppActivity;" and
                       (method in {"onCreate", "<clinit>"} or "m_hasNoNativeBinary" in text))
            focused |= (key == "vlc" and owner == "Lorg/videolan/libvlc/LibVLC;" and method == "loadLibraries")
            focused |= (key in {"fd-fennec_fdroid", "firefox"} and owner == "Lmozilla/components/lib/crash/handler/ExceptionHandler;" and method == "uncaughtException")
            focused |= (key == "cv2-com-kaajjo-libresudoku" and owner == "Lcom/kaajjo/libresudoku/core/utils/GlobalExceptionHandler;")
            if focused:
                retained.append(dict(dex=name, dex_sha256=sha(data), owner=owner, method=method,
                                     exit_targets=targets, dexdump_lines=block.copy()))

        for counter, text in enumerate(process.stdout, 1):
            text = text.rstrip("\n")
            if "Class descriptor  : '" in text:
                finish()
                block = []
                owner = text.split("'")[1]
                method = ""
            elif re.match(r"    #\d+\s+: \(in ", text):
                finish()
                block = []
                method = ""
            elif text.startswith("      name"):
                method = text.split("'")[1]
            if method:
                block.append(dict(line=counter, text=text))
        finish()
        errors = process.stderr.read()
        if process.wait():
            raise RuntimeError(errors)
        members.append(dict(member=name, sha256=sha(data), lines=counter))
    return dict(apk_sha256=sha(apk), tool=portable(tool), tool_sha256=sha(tool), members=members, methods=retained)


def main():
    for name in ["evidence", ".artifacts"]:
        (HERE / name).mkdir(exist_ok=True)
    source_path = MASTER / "benchmark/2026-10-02-candidate-first-fatal-clusters/sources.json"
    sources = json.loads(source_path.read_text())
    inventory_path = REPO / "benchmark/2026-10-02-toutiao-bionic-scope/consumers.json"
    inventory = {row["key"]: row for row in json.loads(inventory_path.read_text())["apps"]}
    sys.path.insert(0, str(MASTER / "scripts/lab"))
    import first_fatal
    rows = []
    dex_rows = []
    native_rows = []
    for key in KEYS:
        folder = expand(sources[key])
        record, events, pids, reports, disappeared, pins = first_fatal.load_run(folder)
        original = first_fatal.analyze(events, pids, reports, disappeared)
        app = inventory[key]
        apk = expand(app["path"])
        if record["package"] != app["package"] or record["apk_sha256"] != app["apk_sha256"] or sha(apk) != app["apk_sha256"]:
            raise ValueError("APK/run mismatch: " + key)
        statuses = [value for event in events if (value := exit_status(event, record["package"], pids))]
        if not statuses:
            raise ValueError("missing exact target termination: " + key)
        pid_rows = []
        for pid in sorted(pids):
            status = next(value for value in statuses if value["pid"] == pid)
            app_events = [event for event in events if event["pid"] == pid and event["line"] < status["line"]]
            errors = [event for event in app_events if event["level"] in {"F", "E"}]
            loader = [event for event in app_events if "MUSL" in event["tag"] and re.search(r"relocat.*failed|Error loading shared library", event["message"])]
            uncaught = [event for event in app_events if re.search(r"UNCAUGHT|Uncaught exception handled|main-thread fatal|background thread 'Gecko' uncaught", event["message"])]
            cleanup = [event for event in events if "OnRemoteDied" in event["message"] and re.search(r"\b" + str(pid) + r"\b", event["message"])]
            pid_rows.append(dict(pid=pid, status=status, last_fe=errors[-20:], last_app_events=app_events[-10:],
                                 loader_errors=loader, uncaught_markers=uncaught, downstream_cleanup=cleanup))
        selected_numbers = set()
        for row in pid_rows:
            selected_numbers.add(row["status"]["line"])
            for name in ["last_fe", "last_app_events", "loader_errors", "uncaught_markers", "downstream_cleanup"]:
                for event in row[name]:
                    selected_numbers.update(range(max(1, event["line"] - 2), event["line"] + 7))
        lines = (folder / "hilog.txt").read_text(errors="replace").splitlines()
        excerpt = HERE / "evidence" / (key + "-hilog.txt")
        excerpt.write_text("\n".join(str(number) + ": " + portable(lines[number - 1]) for number in sorted(selected_numbers) if number <= len(lines)) + "\n")
        files = ["record.json", "hilog.txt", "processes-before.txt", "processes-t5.txt", "processes-t20.txt",
                 "processes-after.txt", "faults-before.txt", "faults-after.txt"]
        hashes = {name: sha(folder / name) for name in files if (folder / name).exists()}
        fingerprint = folder.parent / "runtime-fingerprint.txt"
        fingerprint_rows = [line for line in fingerprint.read_text().splitlines() if any("/" + name in line for name in
                            ["libbionic_compat.so", "libandroid.so", "libnativeloader.so", "liboh_android_runtime.so", "libz.so"])]
        faultlogs = [dict(path=portable(path), sha256=sha(path)) for path in (folder / "faultlogs").rglob("*") if path.is_file()]
        rows.append(dict(key=key, package=record["package"], run=sources[key], run_apk_identity_verified=True,
                         apk_sha256=app["apk_sha256"], clicked_at=record["clicked_at"], pids=pid_rows, original=original,
                         hashes=hashes, fingerprint=dict(path=portable(fingerprint), sha256=sha(fingerprint), selected=fingerprint_rows),
                         faultlogs=faultlogs, fault_inventory_unchanged=hashes["faults-before.txt"] == hashes["faults-after.txt"],
                         excerpt="evidence/" + excerpt.name))
        with zipfile.ZipFile(apk) as archive:
            if key != "burgerking":
                dex_rows.append(dict(key=key, **scan_dex(key, apk, archive)))
            targets = {Path(match[1]).name for row in pid_rows for event in row["loader_errors"]
                       if (match := re.search(r"dso=([^ ]+)", event["message"]))}
            if key == "burgerking":
                targets = {"libmmkv.so", "libNitroMmkv.so"}
            for member in app["members"]:
                if member["status"] != "ELF64-AArch64" or Path(member["member"]).name not in targets:
                    continue
                data = archive.read(member["member"])
                if sha(data) != member["sha256"]:
                    raise ValueError("member mismatch")
                path = HERE / ".artifacts" / (key + "-" + Path(member["member"]).name)
                path.write_bytes(data)
                receipt = capture(path.name + "-dynamic-version", ["llvm-readelf", "-d", "-V", path])
                symbols = subprocess.check_output(["llvm-readelf", "--dyn-syms", str(path)], text=True)
                relevant = [line for line in symbols.splitlines() if any(re.search(r"\b" + name + r"(?:@|\b)", line) for name in SYMBOLS)]
                native_rows.append(dict(key=key, member=member["member"], sha256=sha(data), receipt=receipt, symbols=relevant))
        print(key, "; ".join("pid=" + str(row["pid"]) + " exit " + row["status"]["kind"] + "=" + str(row["status"]["value"]) for row in pid_rows), flush=True)
    provider_root = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload/android/lib64"
    provider = provider_root / "libbionic_compat.so"
    provider_receipt = capture("compat-dynsym", ["llvm-readelf", "--dyn-syms", "-d", "-V", provider])
    whois = [capture("whois-" + name, [sys.executable, MASTER / "scripts/lab/deployed_whois.py", name])
             for name in ["libbionic_compat.so", "libz.so", "libdl.so"]]
    report = dict(source_commit="2aa6c49df0", source_path=portable(source_path), source_sha256=sha(source_path),
                  first_fatal_sha256=sha(MASTER / "scripts/lab/first_fatal.py"), rows=rows,
                  provider=dict(path=portable(provider), sha256=sha(provider), receipt=provider_receipt), whois=whois)
    for name, value in [("observations.json", report), ("dex.json", dex_rows), ("native.json", native_rows)]:
        (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
