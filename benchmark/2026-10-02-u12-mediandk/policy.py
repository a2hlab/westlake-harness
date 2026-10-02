import difflib
import json
import shutil
import subprocess

from collect import BASE, HERE, MASTER, REPO, SDK, WS, portable, run, save, sha


def main():
    donor = WS / "westlake-inputs/generations/u10.1-policy-repro/native-loader-u10.1"
    snapshot = HERE / "inputs/native-loader"
    if not snapshot.exists():
        shutil.copytree(donor, snapshot)
    inputs = {path.relative_to(snapshot).as_posix(): sha(path) for path in snapshot.rglob("*") if path.is_file()}
    policy_path = "policy/native_bridge_policy.v1.json"
    header_path = "include/nativeloader/native_bridge_policy.h"
    original = json.loads((snapshot / policy_path).read_text())
    if len(original["system_libraries"]) != 5 or len(original["shared_sonames"]) != 7:
        raise ValueError("require actual SoundPool-preserving U10.1 policy")
    updated = json.loads(json.dumps(original))
    updated["system_libraries"].append(dict(soname="libmediandk.so", path="/system/android/lib64/libmediandk.so"))
    header = (snapshot / header_path).read_text()
    changed = header.replace("std::array<SystemLibrary, 5>", "std::array<SystemLibrary, 6>")
    anchor = '    {"liboh_adapter_bridge.so", "/system/android/lib64/liboh_adapter_bridge.so"},'
    if header.count(anchor) != 1 or changed == header:
        raise ValueError("policy anchor drift")
    changed = changed.replace(anchor, anchor + '\n    {"libmediandk.so", "/system/android/lib64/libmediandk.so"},')
    overlay = {policy_path: json.dumps(updated, indent=2) + "\n", header_path: changed}
    patches = []
    for name, text in overlay.items():
        patches.extend(difflib.unified_diff((snapshot / name).read_text().splitlines(True), text.splitlines(True),
                       fromfile="a/native-loader-oh/" + name, tofile="b/native-loader-oh/" + name))
    (HERE / "policy.patch").write_text("".join(patches))
    support = HERE / "inputs/build-support"
    support.mkdir(exist_ok=True)
    prior = REPO / "benchmark/2026-10-01-u10-native-shims/native-loader"
    shutil.copyfile(prior / "platform-config.h", support / "platform-config.h")
    if not (support / "dependencies").exists():
        shutil.copytree(prior / "dependencies", support / "dependencies")
    recipe_path = REPO / "benchmark/2026-10-01-u10-native-shims/evidence/policy-build-receipt.json"
    recipe = json.loads(recipe_path.read_text())["commands"][-4:]
    outputs, commands = {}, []
    for variant in ["baseline", "candidate1", "candidate2"]:
        output = HERE / ".artifacts/policy" / variant
        tree = output / "source" if variant != "candidate2" else HERE / ".artifacts/policy/candidate1/source"
        if variant != "candidate2":
            if tree.exists():
                shutil.rmtree(tree)
            shutil.copytree(snapshot, tree)
        (output / "candidate").mkdir(exist_ok=True)
        if variant != "baseline":
            for name, text in overlay.items():
                (tree / name).write_text(text)
        commands.append(run("policy-verify-" + variant, ["python3", tree / "tests/verify_bridge_policy.py"]))
        for number, original_command in enumerate(recipe):
            command = []
            for value in original_command:
                value = value.replace("$OHOS_SDK", str(SDK)).replace("$OUT", str(output)).replace("$REPO", str(REPO))
                value = value.replace("$U9_NATIVE_PAYLOAD", str(WS / "westlake-generation-u9-j10g-238ffc14/native/payload/android/lib64"))
                value = value.replace("$OH61_LINK_INPUTS", str(WS / "westlake-inputs/oh61-link-inputs/system-lib64"))
                for suffix in ["overlay/include", "baseline/include", "baseline/src", "baseline/native_loader.map"]:
                    value = value.replace(str(prior / suffix), str(tree / suffix.replace("overlay/", "").replace("baseline/", "")))
                value = value.replace(str(prior / "platform-config.h"), str(support / "platform-config.h"))
                value = value.replace(str(prior / "dependencies"), str(support / "dependencies"))
                command.append(value)
            commands.append(run("policy-build-" + variant + "-" + str(number), command))
        outputs[variant] = output / "libnativeloader-candidate.so"
    deployed = BASE / "payload/android/lib64/libnativeloader.so"
    if sha(deployed) != "0718f01e237d322b5a16a1858265f8cc05cddd5ddca6d1ceb28bcc33023913a9":
        raise ValueError("actual policy deployment drift")
    for name, path in [("baseline", deployed), ("candidate", outputs["candidate1"])]:
        commands.append(run("open-policy-" + name, ["python3", MASTER / "scripts/lab/open_site_scan.py", path,
                           "--json", HERE / ".artifacts" / ("open-policy-" + name + ".json")]))
        save("evidence/open-policy-" + name + ".json", json.loads((HERE / ".artifacts" / ("open-policy-" + name + ".json")).read_text()))
    for name, candidate in [("rebuild", outputs["baseline"]), ("candidate", outputs["candidate1"])]:
        commands.append(run("strings-policy-" + name, ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", candidate,
                            "--deployed", deployed], allowed=(0, 1)))
        commands.append(run("abi-policy-" + name, ["python3", MASTER / "scripts/lab/abi_diff.py", "--old", deployed,
                            "--new", candidate, "--calls", "--consumer", BASE / "payload/android/lib64/libopenjdk.so",
                            "--json", HERE / ".artifacts" / ("abi-policy-" + name + ".json")]))
        save("evidence/abi-policy-" + name + ".json", json.loads((HERE / ".artifacts" / ("abi-policy-" + name + ".json")).read_text()))
    if sha(outputs["candidate1"]) != sha(outputs["candidate2"]):
        raise ValueError("identical source paths must reproduce policy candidate bytes")
    save("policy-receipt.json", dict(inputs=inputs, original=original, candidate=updated,
         artifacts={name: dict(path=portable(path), sha256=sha(path)) for name, path in outputs.items()},
         deployed=dict(path=portable(deployed), sha256=sha(deployed)), commands=commands,
         recipe_sha256=sha(recipe_path), comparison_only=True, frozen_linux_rebuild_required=True,
         repeat_semantics_identical=sha(outputs["candidate1"]) == sha(outputs["candidate2"])))
    print("policy trusted=5->6 shared=7 unchanged SoundPool retained; comparison candidate=" + sha(outputs["candidate1"]))


if __name__ == "__main__":
    main()
