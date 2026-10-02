import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
BASE = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native"
DRAFT = WS / "westlake-inputs/generations/u12-native-draft-icu1e206531-media8fc0752d-policy2a6ec73f-v1/bundle/native"


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
    (HERE / name).write_text(portable(json.dumps(value, indent=2, ensure_ascii=False)) + "\n")


def run(name, command, allowed=(0,)):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(text)
    (HERE / "evidence" / raw.name).write_text(portable(text))
    if result.returncode not in allowed:
        raise RuntimeError(name + ": " + text)
    return dict(command=[portable(value) for value in command], exit_code=result.returncode, raw_sha256=sha(raw))


def main():
    for name in ["evidence", ".artifacts"]:
        (HERE / name).mkdir(exist_ok=True)
    sources = json.loads((MASTER / "benchmark/2026-10-02-candidate-first-fatal-clusters/sources.json").read_text())
    folder = Path(sources["cv2-com-kaajjo-libresudoku"].replace("$WORKSPACES", str(WS)))
    lines = (folder / "hilog.txt").read_text(errors="replace").splitlines()
    (HERE / "evidence/hilog.txt").write_text("\n".join(str(number) + ": " + portable(lines[number - 1]) for number in list(range(38564, 38575)) + [38691]) + "\n")
    jar = BASE / "payload/android/framework/core-oj.jar"
    if sha(jar) != "e5b187702b82f830d18f838406c75f4a375d494bc541c3916d74228564c9fb6d":
        raise ValueError("wrong boot Locale artifact")
    methods = []
    tool = Path.home() / "Library/Android/sdk/build-tools/37.0.0/dexdump"
    with zipfile.ZipFile(jar) as archive:
        for name in archive.namelist():
            if not re.fullmatch(r"classes\d*\.dex", name):
                continue
            data = archive.read(name)
            target = HERE / ".artifacts" / name
            target.write_bytes(data)
            process = subprocess.Popen([str(tool), "-d", str(target)], stdout=subprocess.PIPE, text=True, errors="replace")
            owner = method = ""
            block = []
            for line in process.stdout:
                if "Class descriptor" in line:
                    if block:
                        methods.append(dict(dex=name, owner=owner, method=method, lines=block))
                    owner = line.split("'")[1]
                    block = []
                match = re.search(r"name\s+: '([^']+)'", line)
                if match:
                    if block:
                        methods.append(dict(dex=name, owner=owner, method=method, lines=block))
                    method = match[1]
                    block = []
                if owner == "Ljava/util/Locale;" and method in {"getDisplayName", "getDisplayCountry"}:
                    block.append(line.rstrip())
            if block:
                methods.append(dict(dex=name, owner=owner, method=method, lines=block))
            if process.wait():
                raise RuntimeError("dexdump failed")
    save("dex.json", dict(jar_sha256=sha(jar), tool_sha256=sha(tool), methods=methods))
    old = BASE / "payload/android/lib64/libicu_jni.so"
    candidate = DRAFT / "payload/android/lib64/libicu_jni.so"
    if sha(candidate) != "1e206531ad5994b7d3fe332a050d53163a8ab5cf954b9314d748d7ff2ae8ae8f":
        raise ValueError("ICU candidate drift")
    records = [run("whois", ["python3", MASTER / "scripts/lab/deployed_whois.py", "libicu_jni.so"])]
    symbols = ["_ZN15ScopedIcuLocaleC2EP7_JNIEnvP8_jstring", "_ZL36LocaleNative_getDisplayCountryNativeP7_JNIEnvP7_jclassP8_jstringS4_"]
    for name, path in [("deployed", old), ("candidate", candidate)]:
        records.append(run("open-" + name, ["python3", MASTER / "scripts/lab/open_site_scan.py", path]))
        table = subprocess.check_output(["llvm-nm", "--format=posix", path], text=True)
        for label, symbol in zip(["constructor", "country"], symbols):
            fields = next(line.split() for line in table.splitlines() if line.split()[0] == symbol)
            start, size = int(fields[2], 16), int(fields[3], 16)
            records.append(run(label + "-" + name, ["llvm-objdump", "-d", "--demangle", "--start-address=" + hex(start),
                               "--stop-address=" + hex(start + size), path]))
    records.append(run("strings", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", old], allowed=(0, 1)))
    donor = MASTER / "benchmark/2026-10-02-u12-icu-zeroinit/evidence/scopedicu-source.txt"
    (HERE / "evidence/scopedicu-source.txt").write_text(donor.read_text())
    save("results.json", dict(key="cv2-com-kaajjo-libresudoku", expected_first_fatal_moved=1,
         coverage="same static country-display -> ScopedIcuLocale constructor path; covered by approved 1e206531",
         candidate_sha256=sha(candidate), deployed_sha256=sha(old), run=sources["cv2-com-kaajjo-libresudoku"],
         hilog_sha256=sha(folder / "hilog.txt"), source_excerpt_sha256=sha(donor), records=records,
         next_first_fatal="unknown", t20="unknown", new_native_artifact=False, execution_enabled=False,
         rollback=dict(path="/system/android/lib64/libicu_jni.so", sha256=sha(old)),
         expect=dict(confirm="same Locale.getDisplayName String.isEmpty-on-null root absent with 1e206531; other walls separately scored",
                     refute="same PID country-display null recurs under verified 1e206531: null has an additional source, coverage prediction refuted")))
    print("LibreSudoku: static country-display path matches ICU; covered by 1e206531; conditional first-wall movement=1; no new library")


if __name__ == "__main__":
    main()
