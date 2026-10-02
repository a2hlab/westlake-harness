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
BASE = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native"
SDK = Path(os.environ.get("OHOS_SDK", "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native"))


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else Path(value).read_bytes()).hexdigest()


def portable(value):
    return str(value).replace(str(REPO) + "/", "$REPO/").replace(str(WS) + "/", "$WORKSPACES/").replace(str(Path.home()) + "/", "$HOME/")


def expand(value):
    return Path(value.replace("$REPO", str(REPO)).replace("$WORKSPACES", str(WS)).replace("$HOME", str(Path.home())))


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def run(name, command, allowed=(0,)):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True, errors="replace")
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(result.stdout + result.stderr)
    (HERE / "evidence" / raw.name).write_text(portable(raw.read_text()))
    receipt = dict(command=[portable(value) for value in command], exit_code=result.returncode,
                   raw_path=portable(raw), raw_sha256=sha(raw), evidence="evidence/" + raw.name)
    if result.returncode not in allowed:
        raise RuntimeError(name + ": " + result.stderr)
    return receipt


def main():
    for name in ["evidence", ".artifacts", "inputs"]:
        (HERE / name).mkdir(exist_ok=True)
    source_path = MASTER / "benchmark/2026-10-02-candidate-first-fatal-clusters/sources.json"
    sources = json.loads(source_path.read_text())
    sys.path.insert(0, str(MASTER / "scripts/lab"))
    import first_fatal
    rows = []
    ranges = {"subwaysurfers": [(44180, 44195), (44354, 44362)], "cv2-com-chessclock-android": [(43043, 43055), (43072, 43089)]}
    for key in ranges:
        folder = expand(sources[key])
        record, events, pids, reports, gone, pins = first_fatal.load_run(folder)
        fatal = first_fatal.analyze(events, pids, reports, gone)
        lines = (folder / "hilog.txt").read_text(errors="replace").splitlines()
        excerpt = HERE / "evidence" / (key + "-hilog.txt")
        excerpt.write_text("\n".join(str(number) + ": " + portable(lines[number - 1]) for start, stop in ranges[key]
                                     for number in range(start, stop + 1)) + "\n")
        matched = [event for event in events if event["pid"] in pids and re.search(r"mediandk|adapter manifest|MediaPlayer\.<clinit>", event["message"])]
        boot = folder.parent / "boot-image-fingerprint.txt"
        rows.append(dict(key=key, package=record["package"], apk_sha256=record["apk_sha256"], pids=sorted(pids),
                         run=sources[key], hilog_sha256=sha(folder / "hilog.txt"), record_sha256=sha(folder / "record.json"),
                         fingerprint_sha256=sha(boot), framework_pin=[line for line in boot.read_text().splitlines() if "  /system/android/framework/framework.jar" in line],
                         fatal=fatal, matched=matched, excerpt="evidence/" + excerpt.name))
    framework = BASE / "payload/android/framework/framework.jar"
    if sha(framework) != "3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af":
        raise ValueError("wrong framework")
    with zipfile.ZipFile(framework) as archive:
        data = archive.read("classes2.dex")
    path = HERE / ".artifacts/framework-classes2.dex"
    path.write_bytes(data)
    tool = Path.home() / "Library/Android/sdk/build-tools/37.0.0/dexdump"
    process = subprocess.Popen([str(tool), "-d", str(path)], stdout=subprocess.PIPE, text=True, errors="replace")
    owner = method = ""
    block = []
    for number, text in enumerate(process.stdout, 1):
        if "Class descriptor  : '" in text:
            owner = text.split("'")[1]
            method = ""
        elif re.match(r"    #\d+\s+: \(in ", text):
            method = ""
        elif text.startswith("      name"):
            method = text.split("'")[1]
        if owner == "Landroid/media/MediaPlayer;" and method == "<clinit>":
            block.append(dict(line=number, text=text.rstrip("\n")))
    if process.wait():
        raise ValueError("DEX extraction failed")
    save("evidence/MediaPlayer-clinit.json", dict(framework_path=portable(framework), framework_sha256=sha(framework),
        dex="classes2.dex", dex_sha256=sha(data), tool_sha256=sha(tool), dexdump=block))
    raw_inventory = json.loads((REPO / "benchmark/2026-10-02-toutiao-bionic-scope/consumers.json").read_text())
    app = next(row for row in raw_inventory["apps"] if row["key"] == "subwaysurfers")
    apk = expand(app["path"])
    member = next(row for row in app["members"] if row["member"] == "lib/arm64-v8a/libunity.so")
    if sha(apk) != app["apk_sha256"] or rows[0]["apk_sha256"] != app["apk_sha256"]:
        raise ValueError("Unity APK mismatch")
    with zipfile.ZipFile(apk) as archive:
        data = archive.read(member["member"])
    if sha(data) != member["sha256"]:
        raise ValueError("Unity member mismatch")
    unity = HERE / ".artifacts/libunity.so"
    unity.write_bytes(data)
    symbols = subprocess.check_output(["llvm-nm", "-D", "--undefined-only", "--format=just-symbols", str(unity)], text=True)
    imports = sorted({symbol.split("@")[0] for symbol in symbols.splitlines() if symbol.startswith(("AMedia", "AImage"))})
    if len(imports) != 50:
        raise ValueError("actual API coverage changed")
    records = [run("unity-dynamic", ["llvm-readelf", "-d", unity]),
               run("unity-media-imports", ["llvm-nm", "-D", "--undefined-only", unity]),
               run("whois-mediandk", [sys.executable, MASTER / "scripts/lab/deployed_whois.py", "libmediandk.so"]),
               run("whois-loader", [sys.executable, MASTER / "scripts/lab/deployed_whois.py", "libnativeloader.so"]),
               run("whois-runtime", [sys.executable, MASTER / "scripts/lab/deployed_whois.py", "liboh_android_runtime.so"])]
    upstream = WS / "vm-copies/westlake-current"
    records.append(run("upstream-mediandk-history", ["git", "-C", upstream, "log", "--all", "--format=%H %s", "--", "*mediandk*", "*NdkMedia*"]))
    save("observations.json", dict(source_commit="2aa6c49df0", source_sha256=sha(source_path), rows=rows,
        unity=dict(apk_sha256=sha(apk), member=member["member"], sha256=sha(unity), imports=imports),
        records=records, execution_enabled=False))
    print("Unity: PID3245 hilog44187-44192 -> libmediandk.so; imported media APIs=50")
    print("Chessclock: PID2315 hilog43043-43055 -> MediaPlayer.clinit requests media_jni, not mediandk")


if __name__ == "__main__":
    main()
