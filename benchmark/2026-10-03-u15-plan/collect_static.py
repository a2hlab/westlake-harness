import json
import subprocess
import sys

from prepare import HERE, MASTER, PRIVATE, WS, portable, save, sha


def capture(name, argv):
    command = [str(value) for value in argv]
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    with raw.open("w") as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT)
    destination = HERE / "evidence" / (name + ".txt")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(portable(raw.read_text()))
    row = dict(name=name, argv=command, exit_code=result.returncode, raw=raw, raw_sha256=sha(raw),
        evidence=str(destination.relative_to(HERE)), evidence_sha256=sha(destination), normalization="home/workspace paths only")
    print(name + " exit=" + str(result.returncode))
    return row


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    base = WS / "westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/.artifacts/common-reviewed"
    old = base / "native/payload/android/lib64/liboh_android_runtime.so"
    candidate = PRIVATE / "native/liboh_android_runtime.so"
    tools = MASTER / "scripts/lab"
    rows = []
    for suffix, path in [("u14", old), ("u15", candidate)]:
        output = HERE / ".artifacts/raw" / ("runtime-open-" + suffix + ".json")
        rows.append(capture("runtime-open-" + suffix, [sys.executable, tools / "open_site_scan.py", path, "--json", output]))
        if output.exists():
            save("evidence/runtime-open-" + suffix + ".json", json.loads(output.read_text()))
    rows.append(capture("runtime-strings-vs-u14", [sys.executable, tools / "deployed_strings_diff.py", candidate, "--deployed", old]))
    old_jar = base / "native/payload/android/framework/framework.jar"
    if sha(old_jar) != plan["bcp"][7]["u14_sha256"]:
        raise ValueError("Explicit framework comparison is not the effective U14 member")
    rows.append(capture("framework-classes-vs-u14", [sys.executable, tools / "deployed_class_diff.py",
        PRIVATE / "jars9/framework.jar", "--deployed", old_jar, "--frozen"]))
    save("static-input-checks.json", dict(scope="fresh Mac input comparisons to U14 content, not promotion or final production gates", results=rows,
        runtime_base=dict(path=old, sha256=sha(old)), framework_base=dict(path=old_jar, sha256=sha(old_jar)),
        board_deployment_verified=False, native_gate="PENDING composed manifest/inputs", image_gates="NOT_RUN; U15 images absent",
        class_tool_limitation="Retain any UnicodeDecodeError as tool failure, never claim class-diff PASS from donor verifier evidence"))


if __name__ == "__main__":
    main()
