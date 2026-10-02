import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

from collect import BASE, HERE, REPO, WS, portable, save, sha

ADDED = ["__pthread_cleanup_pop", "__pthread_cleanup_push", "strtoll_l", "strtoull_l"]


def main():
    out = HERE / ".artifacts"
    out.mkdir(exist_ok=True)
    previous = REPO / "benchmark/2026-10-01-u10-native-shims"
    receipt_path = previous / "evidence/build-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    sdk = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native")
    providers = WS / "westlake-inputs/oh61-link-inputs/system-lib64"
    link = [value.replace("$REPO", str(REPO)).replace("$OUT", str(previous / ".artifacts"))
            .replace("$OHOS_SDK", str(sdk)).replace("$OH61_LINK_INPUTS", str(providers))
            for value in receipt["commands"][-1]]
    compiler = Path(link[0])
    if sha(compiler) != receipt["compiler_sha256"]:
        raise ValueError("frozen compiler mismatch")
    identities = {str(compiler): sha(compiler), str(receipt_path): sha(receipt_path)}
    for name, digest in receipt["link_inputs"].items():
        path = providers / name
        if sha(path) != digest:
            raise ValueError("link provider mismatch")
        identities[str(path)] = digest
    objects = out / "frozen-objects"
    objects.mkdir(exist_ok=True)
    for index, value in enumerate(link):
        if value.endswith(".o"):
            source = Path(value)
            digest = sha(source)
            target = objects / (digest + ".o")
            shutil.copyfile(source, target)
            identities[str(target)] = digest
            link[index] = str(target)
    snapshots = HERE / "inputs"
    snapshots.mkdir(exist_ok=True)
    source_receipt = json.loads((previous / "baseline-inputs.json").read_text())
    for row in source_receipt["files"]:
        relative = row["path"].removeprefix(source_receipt["compat_prefix"])
        source = previous / "baseline" / relative
        if sha(source) != row["sha256"]:
            raise ValueError("accepted baseline source mismatch")
        target = snapshots / "compat" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        identities[str(target)] = sha(target)
    for relative, digest in receipt["overlay_inputs"].items():
        source = previous / relative
        if sha(source) != digest:
            raise ValueError("accepted overlay source mismatch")
        target = snapshots / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        identities[str(target)] = digest
    deployed = BASE / "payload/android/lib64/libbionic_compat.so"
    old_sha = "015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58"
    if sha(deployed) != old_sha:
        raise ValueError("actual deployment identity drift")
    exported = subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", deployed], text=True).splitlines()
    overlay = HERE / "vlc_bionic_residue.c"
    identities[str(overlay)] = sha(overlay)
    commands = []

    def execute(command):
        print(shlex.join([str(value) for value in command]), flush=True)
        process = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
        print(process.stdout, end="", flush=True)
        print(process.stderr, end="", flush=True)
        commands.append(dict(command=[portable(value) for value in command], exit_code=process.returncode))
        if process.returncode:
            raise ValueError("build failed")

    repeated = []
    overlay_object = out / "vlc_bionic_residue.o"
    dependency_file = out / "vlc_bionic_residue.d"
    for repeat in [1, 2]:
        execute([compiler, "--target=aarch64-linux-ohos", "--sysroot=" + str(sdk / "sysroot"),
                 "-std=c11", "-O2", "-g", "-fPIC", "-MD", "-MF", dependency_file,
                 "-ffile-prefix-map=" + str(REPO) + "=.", "-c", overlay, "-o", overlay_object])
        hashes = {}
        for variant in ["baseline", "candidate"]:
            mapping = out / (variant + ".map")
            allowed = exported if variant == "baseline" else sorted(set(exported + ADDED))
            mapping.write_text("{ global: " + "; ".join(allowed) + "; local: *; };\n")
            candidate = out / (variant + str(repeat) + ".so")
            command = ["-Wl,--version-script=" + str(mapping) if value.startswith("-Wl,--version-script=") else value for value in link]
            command[command.index("-o") + 1] = str(candidate)
            if variant == "candidate":
                command.append(str(overlay_object))
            execute(command)
            hashes[variant] = sha(candidate)
            if variant == "baseline" and hashes[variant] != old_sha:
                raise ValueError("015aa byte reproduction failed; stop")
        repeated.append(hashes)
        print("REPEAT " + str(repeat) + " " + json.dumps(hashes), flush=True)
    if repeated[0] != repeated[1]:
        raise ValueError("repeated build differs")
    dependency_text = dependency_file.read_text().replace("\\\n", " ")
    for value in shlex.split(dependency_text.split(":", 1)[1]):
        source = Path(value)
        if source == overlay:
            continue
        relative = source.relative_to(sdk)
        target = snapshots / "sdk" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        identities[str(target)] = sha(target)
    save("build-receipt.json", dict(compiler_sha256=sha(compiler), old_sha256=old_sha,
         repeated=repeated, same_bytes=True, baseline_reproduced=True, commands=commands,
         source_and_object_inputs=[dict(path=portable(path), sha256=digest) for path, digest in sorted(identities.items())],
         method="Exact accepted015aa objects relinked byte-for-byte; source snapshots verified against original receipt; new overlay compiled twice",
         added_exports=ADDED, execution_enabled=False))


if __name__ == "__main__":
    main()
