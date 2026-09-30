"""U5-learned, key-independent requirements; not runtime failure predictions."""

import re
import struct
from pathlib import PurePosixPath

from scan_apps import INVOKE

FAMILIES = {
    "flutter-jni-field-id": {
        "signature": "fid == null + GetLongField + FlutterJNI.nativeRunBundleAndSnapshotFromLibrary",
        "condition": "DEX invoke instruction referencing FlutterJNI runBundleAndSnapshotFromLibrary or nativeRunBundleAndSnapshotFromLibrary",
        "requirement": "FlutterJNI native field IDs must be initialized before GetLongField; DEX presence does not prove a null ID",
    },
    "private-runtime-reload": {
        "signature": "Flutter private preload libandroid.so + Xpm check failed for liboh_android_runtime.so, errno for mmap is: 22",
        "condition": "FlutterJNI bundle invocation AND private westlake_flutter/libandroid.so DT_NEEDED liboh_android_runtime.so",
        "requirement": "Private preload must reuse the resident runtime in its effective namespace; neither file presence nor DT_NEEDED proves XPM failure",
    },
    "realm-libz": {
        "signature": "Error loading shared library libz.so (needed by librealm-jni*.so or librealmc.so)",
        "condition": "AArch64 Realm consumer has DT_NEEDED libz.so",
        "requirement": "Resolve libz.so in the actual Realm consumer namespace, not merely in the package",
    },
    "vibrator-lock": {
        "signature": "Null reference used for synchronization + SystemVibratorManager.getVibratorIds",
        "condition": "DEX invoke Vibrator/SystemVibrator.hasVibrator()Z or VibratorManager/SystemVibratorManager.getVibratorIds()[I",
        "requirement": "Construct a non-null SystemVibratorManager lock before monitor-enter; invocation does not establish the producer state",
    },
    "mozglue-strerror": {
        "signature": "relocating failed dso=libmozglue.so s=__gnu_strerror_r",
        "condition": "libmozglue.so strong undefined __gnu_strerror_r",
        "requirement": "Provide __gnu_strerror_r in the libmozglue load scope; megazord is a different consumer",
    },
    "ppsspp-dlopen-ext": {
        "signature": "libppsspp_jni.so: android_dlopen_ext: symbol not found",
        "condition": "libppsspp_jni.so strong undefined android_dlopen_ext",
        "requirement": "Provide android_dlopen_ext in the libppsspp_jni load scope",
    },
    "jitsi-abort-message": {
        "signature": "libc++_shared.so: android_set_abort_message: symbol not found",
        "condition": "libc++_shared.so strong undefined android_set_abort_message",
        "requirement": "Provide android_set_abort_message in the libc++_shared load scope",
    },
}
SYMBOLS = {
    "libmozglue.so": ("__gnu_strerror_r", "mozglue-strerror"),
    "libppsspp_jni.so": ("android_dlopen_ext", "ppsspp-dlopen-ext"),
    "libc++_shared.so": ("android_set_abort_message", "jitsi-abort-message"),
}


def dex_family(instruction):
    match = INVOKE.search(instruction)
    if not match:
        return None
    _, _, owner, name, signature = match.groups()
    if (owner == "io/flutter/embedding/engine/FlutterJNI" and
            name in {"runBundleAndSnapshotFromLibrary", "nativeRunBundleAndSnapshotFromLibrary"}):
        return "flutter-jni-field-id"
    if ((owner in {"android/os/Vibrator", "android/os/SystemVibrator"} and
         name == "hasVibrator" and signature == "()Z") or
        (owner in {"android/os/VibratorManager", "android/os/SystemVibratorManager"} and
         name == "getVibratorIds" and signature == "()[I")):
        return "vibrator-lock"
    return None


def aarch64_header(data):
    if len(data) < 64:
        return "truncated"
    if data[:4] != b"\x7fELF":
        return "invalid-magic"
    if data[4:6] != b"\x02\x01":
        return "wrong-class-or-endian"
    elf_type, machine = struct.unpack_from("<HH", data, 16)
    if machine != 183:
        return "wrong-machine"
    return "valid-ELF64-AArch64" if elf_type == 3 else "not-ET_DYN"


def input_findings(facts):
    findings = []
    apks = facts["apks"]
    if len(apks) > 1:
        findings.append(dict(category="split-key", evidence=apks,
                             reason="Multiple APKs present; the current batch installs only the selected base, not the set"))
    invalid = [row for row in facts["sidecars"] if row["header"] != "valid-ELF64-AArch64"]
    if invalid:
        findings.append(dict(category="non-aarch64-sidecar", evidence=invalid,
                             reason="The batch rejects the sidecar before launch; do not silently discard it"))
    expected = facts["entry"]["apk_sha256"]
    metadata = facts["metadata_apk_sha256"]
    if (expected and expected != metadata) or not any(row["sha256"] == (expected or metadata) for row in apks):
        findings.append(dict(category="apk-pin-mismatch", expected=expected, metadata=metadata,
                             evidence=apks, reason="apps.json pin, metadata and an actual APK must agree"))
    return findings


def app_requirements(facts, profile):
    grouped = {}
    for witness in facts["dex_calls"]:
        family = dex_family(witness["instruction"])
        if family:
            grouped.setdefault(family, []).append(witness)
    private = profile["private_android"]
    if ("flutter-jni-field-id" in grouped and private["path"].endswith("/westlake_flutter/libandroid.so")
            and private["header"] == "valid-ELF64-AArch64"
            and private["symbol_status"] == "parsed"
            and "liboh_android_runtime.so" in private["needed"]):
        grouped["private-runtime-reload"] = [grouped["flutter-jni-field-id"][0], private]
    for library in facts["libraries"]:
        if library["header"] != "valid-ELF64-AArch64" or library["symbol_status"] != "parsed":
            continue
        name = PurePosixPath(library["path"]).name
        if re.fullmatch(r"librealm-jni(?:[-.][\w.-]+)?\.so|librealmc\.so", name) and "libz.so" in library["needed"]:
            grouped.setdefault("realm-libz", []).append(library)
        if name in SYMBOLS:
            symbol, family = SYMBOLS[name]
            if any(row["name"] == symbol and not row["weak"] for row in library["imports"]):
                grouped.setdefault(family, []).append(library)
    return [dict(family=family, **FAMILIES[family], evidence=grouped[family],
                 verdict="conditional-runtime-requirement", startup_reachable="unknown",
                 active_wall="unknown", resolution="unknown") for family in sorted(grouped)]


def predict(facts, profile):
    inputs = input_findings(facts)
    risks = app_requirements(facts, profile)
    return dict(key=facts["entry"]["key"], package=facts["entry"]["package"] or facts["metadata_package"],
                expected_apk_sha256=facts["entry"]["apk_sha256"],
                pin_status="explicit-apps-json-pin" if facts["entry"]["apk_sha256"] else "unpinned-metadata-resolved",
                scanned_apk_sha256=facts["selected_apk"]["sha256"] if facts["selected_apk"] else None,
                input_findings=inputs, app_wall_risks=risks, scan_errors=facts["scan_errors"],
                prediction=("input-blocked-runtime-fixes-insufficient" if inputs else
                            "unknown-incomplete-scan" if facts["scan_errors"] else
                            "conditional-runtime-requirements" if risks else "no-new-rule-hit-not-pass"),
                first_wall="unknown", t20="unpredicted-requires-visual-review")
