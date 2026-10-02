import json
from pathlib import Path

from finalize import HERE, MASTER, WS, install, save, sha
from validation import OLD_ABI

RELEASE = WS / "westlake-inputs/generations/u14-native-abi-v2"
SOURCE = MASTER / "benchmark/2026-10-03-u14-native-abi-v2"
GECKO = MASTER / "benchmark/2026-10-03-u14-native-abi-gecko"
PIN = "f8619ad5571c92cb3e9da3b8265ee41c17fa67db0a6aabeb9bfb89903e2a2239"


def record(path):
    return dict(path=path, sha256=sha(path))


def main():
    for line in (RELEASE / "SHA256SUMS").read_text().splitlines():
        digest, member = line.split(maxsplit=1)
        source = (RELEASE / member).resolve()
        if not source.is_relative_to(RELEASE) or sha(source) != digest:
            raise ValueError("Donor release SHA256SUMS drift")
    artifacts = [RELEASE / "builds" / ("nabi-v2-" + label + ".so") for label in ["a", "b"]]
    logs = [RELEASE / "logs" / ("nabi-v2-" + label + ".log") for label in ["a", "b"]]
    if any(sha(path) != PIN for path in artifacts):
        raise ValueError("Two donor builds differ")
    for path in logs:
        text = path.read_text()
        if not text.endswith("rc=0\n") or PIN not in text or "feef13a36e78b7a2ff3e9e3f180a958f2782be1e" not in text:
            raise ValueError("Actual tee/compiler/build status evidence missing")
    results = json.loads((SOURCE / "results.json").read_text())
    if results["base"] != OLD_ABI or results["candidate"] != PIN or results["exports_added"] != ["_ctype_@@LIBC"] or results["exports_removed"]:
        raise ValueError("Donor single-variable ABI assertion drift")
    files = sorted((SOURCE / "src").rglob("*"))
    sources = [record(path) for path in files if path.is_file()]
    for path in [GECKO / "src/gecko_abi.c", GECKO / "src/android_dlopen_ext.c", GECKO / "src/android_dlext_abi.h", SOURCE / "build_v2_hw248.sh"]:
        sources.append(record(path))
    scan_sources = {"u14-gecko-abi.c": record(GECKO / "src/gecko_abi.c"),
        "u14-gecko-dlext.c": record(GECKO / "src/android_dlopen_ext.c"),
        "u14-gecko-ctype.c": record(SOURCE / "src/ctype_compat.c")}
    frozen = WS / "westlake-harness-bms-deploy/bms/src/.work/b68-generation/.work/product-tls-generation/frozen/toolchain/bin"
    compiler_sha = "b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913"
    linker_sha = "8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4"
    if sha(frozen / "clang-15") != compiler_sha or sha(frozen / "lld") != linker_sha:
        raise ValueError("Local frozen toolchain crosscheck drift")
    for path in files:
        if path.is_file():
            install(path, HERE / "inputs/donor" / path.relative_to(SOURCE))
    for name in ["build_v2_hw248.sh", "results.json", "README.md"]:
        install(SOURCE / name, HERE / "inputs/donor" / name)
    for path in logs:
        install(path, HERE / "inputs/donor/logs" / path.name)
    for name in ["gates.txt", "equiv-7605812c-vs-f8619ad5.txt", "replay-realm.txt"]:
        install(SOURCE / "evidence" / name, HERE / "inputs/donor/evidence" / name)
    save(HERE / "donor-evidence.json", dict(artifact_sha256=PIN, artifacts=[record(path) for path in artifacts],
        logs=[record(path) for path in logs], sources=sources, scan_sources=scan_sources, build_rc=[0, 0],
        toolchain=dict(producer="OHOS clang 15.0.4 feef13a36e78b7a2ff3e9e3f180a958f2782be1e",
            provenance=record(GECKO / "evidence/toolchains.txt"), donor_commit="e90947270c",
            compiler_sha256=compiler_sha, linker_sha256=linker_sha,
            local_frozen_copy_crosscheck=True),
        build_commands=dict(recipe=record(SOURCE / "build_v2_hw248.sh"),
            evidence_kind="recipe-plus-actual-tee-not-shell-xtrace",
            mirror_root="$HW248_HOME/cc-t3-nabi-2026103/westlake-harness-bms-deploy", mirror_root_length=58,
            extra_objects=["gecko_abi.o", "android_dlopen_ext.o", "ctype_compat.o"], actual_tee_logs=[record(path) for path in logs]),
        release_inventory=record(RELEASE / "SHA256SUMS"), donor_results=record(SOURCE / "results.json"),
        source_snapshot=HERE / "inputs/donor", lane_builds_performed=False))
    print("Donor f8619ad5 SHA256SUMS/two builds/tee/source/version-map verified; lane compilation=0")


if __name__ == "__main__":
    main()
