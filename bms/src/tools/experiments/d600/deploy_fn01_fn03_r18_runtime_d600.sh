#!/usr/bin/env zsh
set -eu

usage()
{
    print -u2 "Usage:"
    print -u2 "  $0 --p0 --serial SERIAL --candidate-root DIR --apk APK"
    print -u2 "     --deploy-manifest JSON --expected-hashes JSON [--preflight-only]"
    print -u2 "  $0 <device-serial>  # legacy non-P0 mode"
}

P0_MODE=0
PREFLIGHT_ONLY=0
P0_SERIAL=""
P0_CANDIDATE_ROOT=""
P0_APK=""
P0_DEPLOY_MANIFEST=""
P0_EXPECTED_HASHES=""

if [[ "${1:-}" == "--p0" ]]; then
    P0_MODE=1
    shift
    while (( $# > 0 )); do
        case "$1" in
            --serial)
                (( $# >= 2 )) || { usage; exit 2; }
                P0_SERIAL="$2"
                shift 2
                ;;
            --candidate-root)
                (( $# >= 2 )) || { usage; exit 2; }
                P0_CANDIDATE_ROOT="$2"
                shift 2
                ;;
            --apk)
                (( $# >= 2 )) || { usage; exit 2; }
                P0_APK="$2"
                shift 2
                ;;
            --deploy-manifest)
                (( $# >= 2 )) || { usage; exit 2; }
                P0_DEPLOY_MANIFEST="$2"
                shift 2
                ;;
            --expected-hashes)
                (( $# >= 2 )) || { usage; exit 2; }
                P0_EXPECTED_HASHES="$2"
                shift 2
                ;;
            --preflight-only)
                PREFLIGHT_ONLY=1
                shift
                ;;
            *)
                print -u2 "P0_ARGUMENT_ERROR: unknown or positional argument: $1"
                usage
                exit 2
                ;;
        esac
    done
    [[ -n "$P0_SERIAL" && -n "$P0_CANDIDATE_ROOT" && -n "$P0_APK" &&
       -n "$P0_DEPLOY_MANIFEST" && -n "$P0_EXPECTED_HASHES" ]] || {
        print -u2 "P0_ARGUMENT_ERROR: serial, candidate root, APK, deploy manifest and expected hashes are all required"
        usage
        exit 2
    }
    [[ "$P0_SERIAL" =~ ^[A-Za-z0-9._-]+$ ]] || {
        print -u2 "P0_ARGUMENT_ERROR: invalid serial: $P0_SERIAL"
        exit 2
    }
elif [[ "${1:-}" == --* ]]; then
    print -u2 "P0_ARGUMENT_ERROR: named deployment arguments require an explicit --p0"
    usage
    exit 2
else
    [[ $# == 1 ]] || { usage; exit 2; }
fi

HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
ROOT="${BRIDGE_ROOT:-/opt/Bridge}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ "$P0_MODE" == "1" ]]; then
    TARGET="$P0_SERIAL"
    [[ -d "$P0_CANDIDATE_ROOT" ]] || {
        print -u2 "P0_PREFLIGHT_ERROR: CANDIDATE_ROOT_MISSING: $P0_CANDIDATE_ROOT"
        exit 1
    }
    SRC="$(cd "$P0_CANDIDATE_ROOT" && pwd -P)"
    NOHARD_SRC="$SRC"
    APK="$P0_APK"
    DEPLOY_MANIFEST="$P0_DEPLOY_MANIFEST"
    EXPECTED_HASHES_MANIFEST="$P0_EXPECTED_HASHES"
    CFG="$SRC/appspawn_x.cfg"
    SANDBOX_CFG="$SRC/appdata-sandbox.json"
else
    TARGET="$1"
    SRC="${SRC:-/opt/Bridge/.work/d600-deploy-no-hardcode-appspawnrebuilt-20260727T000000Z}"
    NOHARD_SRC="${NOHARD_SRC:-$SRC}"
    APK="${APK:-$SRC/HelloWorld.apk}"
    CFG="${CFG:-$SRC/appspawn_x.cfg}"
    SANDBOX_CFG="${SANDBOX_CFG:-$SRC/appdata-sandbox.json}"
fi

SHORT="${TARGET:0:8}"
SYSTEM_ANDROID=$SRC/system/android
if [[ "$P0_MODE" == "1" ]]; then
    APP_PACKAGE="com.example.helloworld"
    APP_ACTIVITY="com.example.helloworld.MainActivity"
    APP_REMOTE_NAME="$(basename "$APK")"
    RUN_APK_SANITY=1
    PRESERVE_SELINUX=1
    ALLOW_ONDEMAND_NO_PARENT=0
else
    APP_PACKAGE="${APP_PACKAGE:-com.example.helloworld}"
    APP_ACTIVITY="${APP_ACTIVITY:-com.example.helloworld.MainActivity}"
    APP_REMOTE_NAME="${APP_REMOTE_NAME:-$(basename "$APK")}"
    RUN_APK_SANITY="${RUN_APK_SANITY:-1}"
    PRESERVE_SELINUX="${PRESERVE_SELINUX:-1}"
    ALLOW_ONDEMAND_NO_PARENT="${ALLOW_ONDEMAND_NO_PARENT:-0}"
fi
REMOTE_GENERATION="/data/a64deploy/fn0103-r18-merged-$SHORT"
REMOTE_SYSTEM_ANDROID="$REMOTE_GENERATION/android"
STAGE="/data/local/tmp/fn0103-r18-merged-$SHORT-$TS"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-$ROOT/evidence/runs}"
EVIDENCE="$EVIDENCE_ROOT/fn01-fn03-r18-runtime-deploy-$SHORT-$TS"

if [[ "$P0_MODE" == "1" ]]; then
    P0_GENERATION_ID=$(/usr/bin/python3 - \
        "$SRC" "$APK" "$DEPLOY_MANIFEST" "$EXPECTED_HASHES_MANIFEST" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import sys


candidate_root = Path(sys.argv[1]).resolve()
apk_path = Path(sys.argv[2]).resolve()
manifest_path = Path(sys.argv[3]).resolve()
hashes_path = Path(sys.argv[4]).resolve()
APK_SHA256 = "2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def reject(code, detail):
    print(f"P0_PREFLIGHT_ERROR: {code}: {detail}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path, label):
    if not path.is_file():
        reject(f"{label}_MISSING", str(path))
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        reject(f"{label}_INVALID", str(error))
    if not isinstance(value, dict):
        reject(f"{label}_INVALID", "top level must be an object")
    return value


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_sha(value, label):
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        reject("INVALID_SHA256", label)
    return value


def safe_candidate_file(relative_path):
    if not isinstance(relative_path, str) or not relative_path:
        reject("INVALID_ARTIFACT_PATH", repr(relative_path))
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path:
        reject("INVALID_ARTIFACT_PATH", relative_path)
    current = candidate_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            reject("CANDIDATE_SYMLINK_REJECTED", relative_path)
    resolved = current.resolve()
    try:
        resolved.relative_to(candidate_root)
    except ValueError:
        reject("ARTIFACT_OUTSIDE_CANDIDATE_ROOT", relative_path)
    if not resolved.is_file():
        reject("CANDIDATE_FILE_MISSING", relative_path)
    return resolved


manifest = load_json(manifest_path, "DEPLOY_MANIFEST")
expected = load_json(hashes_path, "EXPECTED_HASHES")

if "skia_provider" not in manifest:
    reject("MISSING_SKIA_PROVIDER", "skia_provider object is required")
if "namespace_manifest" not in manifest:
    reject("INVALID_NAMESPACE_MANIFEST", "namespace_manifest object is required")
if set(manifest) != {
    "schema_version", "generation_id", "apk", "artifacts", "skia_provider",
    "namespace_manifest",
}:
    reject("DEPLOY_MANIFEST_INVALID", "unexpected or missing top-level fields")
if set(expected) != {
    "schema_version", "generation_id", "apk_sha256", "candidate_files", "device_files",
}:
    reject("EXPECTED_HASHES_INVALID", "unexpected or missing top-level fields")
if manifest.get("schema_version") != "bridge.helloworld-p0.deploy.v1":
    reject("DEPLOY_MANIFEST_INVALID", "unsupported schema_version")
if expected.get("schema_version") != "bridge.helloworld-p0.expected-hashes.v1":
    reject("EXPECTED_HASHES_INVALID", "unsupported schema_version")

generation_id = manifest.get("generation_id")
if not isinstance(generation_id, str) or not SHA256.fullmatch(generation_id):
    reject("DEPLOY_MANIFEST_INVALID", "generation_id must be lowercase SHA-256")
if expected.get("generation_id") != generation_id:
    reject("MIXED_GENERATION", "deploy manifest and expected hashes disagree")

apk = manifest.get("apk")
if not isinstance(apk, dict):
    reject("APK_IDENTITY_INVALID", "apk object is required")
if apk != {
    "sha256": APK_SHA256,
    "package_name": "com.example.helloworld",
    "activity_name": "com.example.helloworld.MainActivity",
}:
    reject("APK_IDENTITY_INVALID", "manifest does not select the frozen HelloWorld APK")
if expected.get("apk_sha256") != APK_SHA256:
    reject("APK_IDENTITY_INVALID", "expected hashes do not bind the frozen APK")
if not apk_path.is_file() or apk_path.is_symlink() or sha256(apk_path) != APK_SHA256:
    reject("APK_HASH_MISMATCH", str(apk_path))

required_role_paths = {
    "appspawn": "appspawn-x",
    "appspawn_config": "appspawn_x.cfg",
    "sandbox_config": "appdata-sandbox.json",
    "hap_domain_wrapper": "system/lib64/libwestlake_hap_domain_wrapper.so",
    "route_a_child_plugin": "system/lib64/appspawn/libwestlake_android_child.z.so",
    "art": "system/android/lib64/libart.so",
    "route_a_runtime_provider": "system/android/lib64/libwestlake_android_runtime_provider.so",
    "android_runtime": "system/android/lib64/liboh_android_runtime.so",
    "adapter_bridge": "system/android/lib64/liboh_adapter_bridge.so",
    "hwui": "system/android/lib64/libhwui.so",
    "hwui_shim": "system/android/lib64/liboh_hwui_shim.so",
    "skia_rtti_shim": "system/android/lib64/liboh_skia_rtti_shim.so",
    "androidfw": "system/android/lib64/libandroidfw.so",
    "minikin": "system/android/lib64/libminikin.so",
    "profile": "system/android/lib64/libprofile.so",
    "unwindstack": "system/android/lib64/libunwindstack.so",
    "fonts_config": "system/android/etc/fonts.xml",
    "framework_jar": "system/android/framework/oh-adapter-framework.jar",
    "boot_art": "system/android/framework/arm64/boot.art",
    "boot_oat": "system/android/framework/arm64/boot.oat",
    "boot_vdex": "system/android/framework/arm64/boot.vdex",
    "appms": "system/lib64/libappms.z.so",
    "appspawn_client": "system/lib64/libappspawn_client.z.so",
    "bms": "system/lib64/libbms.z.so",
    "installs": "system/lib64/libinstalls.z.so",
    "apk_installer": "system/lib64/libapk_installer.so",
    "abilityms": "system/lib64/platformsdk/libabilityms.z.so",
    "lzma": "system/android/lib64/liblzma.so",
    "shared_libz": "system/android/lib64/libshared_libz.z.so",
    "thread_guard_registry": "system/android/lib64/libwestlake_thread_guard_registry.so",
}
static_destinations = {
    "appspawn": ["/system/bin/appspawn-x"],
    "appspawn_config": ["/system/etc/init/appspawn_x.cfg"],
    "sandbox_config": ["/system/etc/sandbox/appdata-sandbox.json"],
    "hap_domain_wrapper": ["/system/lib64/libwestlake_hap_domain_wrapper.so"],
    "route_a_child_plugin": ["/system/lib64/appspawn/libwestlake_android_child.z.so"],
    "appms": ["/system/lib64/libappms.z.so", "/system/lib64/platformsdk/libappms.z.so"],
    "appspawn_client": ["/system/lib64/libappspawn_client.z.so", "/system/lib64/platformsdk/libappspawn_client.z.so"],
    "bms": ["/system/lib64/libbms.z.so", "/system/lib64/platformsdk/libbms.z.so"],
    "installs": ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"],
    "apk_installer": ["/system/lib64/libapk_installer.so", "/system/lib64/platformsdk/libapk_installer.so"],
    "abilityms": ["/system/lib64/platformsdk/libabilityms.z.so"],
}

artifacts = manifest.get("artifacts")
if not isinstance(artifacts, list) or not artifacts:
    reject("DEPLOY_MANIFEST_INVALID", "artifacts must be a non-empty list")
artifact_by_role = {}
artifact_by_path = {}
for artifact in artifacts:
    if not isinstance(artifact, dict) or set(artifact) != {"role", "path", "destinations", "sha256"}:
        reject("DEPLOY_MANIFEST_INVALID", "artifact fields must be role/path/destinations/sha256")
    role = artifact["role"]
    relative_path = artifact["path"]
    if not isinstance(role, str) or not role:
        reject("DEPLOY_MANIFEST_INVALID", "artifact role must be non-empty")
    if role == "skia_provider" or relative_path.endswith("/libskia_canvaskit.z.so"):
        reject("PROVIDER_MUST_NOT_BE_DEPLOYED", relative_path)
    if role in artifact_by_role or relative_path in artifact_by_path:
        reject("DEPLOY_MANIFEST_INVALID", f"duplicate role or path: {role}/{relative_path}")
    destinations = artifact["destinations"]
    if not isinstance(destinations, list) or not destinations or any(
        not isinstance(item, str) or (not item.startswith("/") and item != "STAGING_ONLY")
        for item in destinations
    ):
        reject("DEPLOY_MANIFEST_INVALID", f"invalid destinations for {role}")
    require_sha(artifact["sha256"], f"artifact {relative_path}")
    artifact_by_role[role] = artifact
    artifact_by_path[relative_path] = artifact

for role, relative_path in required_role_paths.items():
    artifact = artifact_by_role.get(role)
    if not artifact or artifact["path"] != relative_path:
        reject("DEPLOY_ARTIFACT_MISSING", f"{role}:{relative_path}")
    wanted_destinations = static_destinations.get(role, [f"/{relative_path}"])
    if artifact["destinations"] != wanted_destinations:
        reject("DEPLOY_DESTINATION_MISMATCH", role)

candidate_files = expected.get("candidate_files")
if not isinstance(candidate_files, dict):
    reject("EXPECTED_HASHES_INVALID", "candidate_files must be an object")
if set(candidate_files) != set(artifact_by_path):
    reject("DEPLOY_SET_MISMATCH", "manifest artifacts and expected hashes differ")
for relative_path, expected_digest in candidate_files.items():
    require_sha(expected_digest, f"candidate_files {relative_path}")
    artifact = artifact_by_path[relative_path]
    if artifact["sha256"] != expected_digest:
        reject("MIXED_GENERATION", f"artifact hash disagrees for {relative_path}")
    actual_digest = sha256(safe_candidate_file(relative_path))
    if actual_digest != expected_digest:
        reject("CANDIDATE_HASH_MISMATCH", relative_path)

# system/android is transferred as a directory, so every regular file below it
# must be selected.  Otherwise hdc would silently deploy bytes outside the
# selected manifest.
system_android = candidate_root / "system/android"
system_android_symlinks = [path for path in system_android.rglob("*") if path.is_symlink()]
if system_android_symlinks:
    reject("CANDIDATE_SYMLINK_REJECTED", system_android_symlinks[0].relative_to(candidate_root))
actual_system_android_files = {
    path.relative_to(candidate_root).as_posix()
    for path in system_android.rglob("*")
    if path.is_file() and not path.is_symlink()
}
selected_system_android_files = {
    path for path in artifact_by_path if path.startswith("system/android/")
}
if actual_system_android_files != selected_system_android_files:
    reject("DEPLOY_SET_MISMATCH", "system/android directory is not fully covered")

# These are exactly the other candidate-root paths copied by this script.
# Optional sealed Route-A bytes are allowed only when their seal manifest and
# every sealed member are selected together.
actual_deploy_paths = set(required_role_paths.values()) | actual_system_android_files
sealed_manifest_path = candidate_root / "route-a-sealed.sha256"
sealed_root = candidate_root / "system/lib64/westlake/route-a"
if sealed_manifest_path.exists() or sealed_root.exists():
    if not sealed_manifest_path.is_file() or not sealed_root.is_dir():
        reject("DEPLOY_SET_MISMATCH", "sealed Route-A directory and manifest must be present together")
    sealed_generations = [path for path in sealed_root.iterdir() if path.is_dir()]
    if len(sealed_generations) != 1:
        reject("DEPLOY_SET_MISMATCH", "exactly one sealed Route-A generation is required")
    sealed_symlinks = [path for path in sealed_root.rglob("*") if path.is_symlink()]
    if sealed_symlinks:
        reject("CANDIDATE_SYMLINK_REJECTED", sealed_symlinks[0].relative_to(candidate_root))
    sealed_paths = {
        path.relative_to(candidate_root).as_posix()
        for path in sealed_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    actual_deploy_paths.add("route-a-sealed.sha256")
    actual_deploy_paths.update(sealed_paths)
    for relative_path in sealed_paths:
        artifact = artifact_by_path.get(relative_path)
        if not artifact or artifact["destinations"] != [f"/{relative_path}"]:
            reject("DEPLOY_DESTINATION_MISMATCH", relative_path)
    seal_artifact = artifact_by_path.get("route-a-sealed.sha256")
    if not seal_artifact or seal_artifact["destinations"] != ["STAGING_ONLY"]:
        reject("DEPLOY_DESTINATION_MISMATCH", "route-a-sealed.sha256")
if set(artifact_by_path) != actual_deploy_paths:
    reject("DEPLOY_SET_MISMATCH", "selected manifest contains bytes this script does not deploy")

skia_provider = manifest.get("skia_provider")
if not isinstance(skia_provider, dict):
    reject("MISSING_SKIA_PROVIDER", "skia_provider object is required")
if skia_provider != {
    "device_path": "/system/lib64/libskia_canvaskit.z.so",
    "sha256": skia_provider.get("sha256"),
    "soname": "libskia_canvaskit.z.so",
    "policy": "PRESERVE_DEVICE_BASELINE",
}:
    reject("MISSING_SKIA_PROVIDER", "provider identity/policy is not the preserved target provider")
require_sha(skia_provider["sha256"], "skia_provider.sha256")

namespace = manifest.get("namespace_manifest")
if not isinstance(namespace, dict):
    reject("INVALID_NAMESPACE_MANIFEST", "namespace_manifest object is required")
if namespace != {
    "device_path": "/system/etc/ld-musl-namespace-aarch64.ini",
    "sha256": namespace.get("sha256"),
    "selected_section": "systemscence",
    "provider_search_paths": ["/system/lib64"],
    "mutation": "UNCHANGED",
}:
    reject("INVALID_NAMESPACE_MANIFEST", "must preserve systemscence with /system/lib64 provider search")
require_sha(namespace["sha256"], "namespace_manifest.sha256")

device_files = expected.get("device_files")
if not isinstance(device_files, dict):
    reject("EXPECTED_HASHES_INVALID", "device_files must be an object")
required_device_files = {
    "/system/lib64/libskia_canvaskit.z.so": skia_provider["sha256"],
    "/system/etc/ld-musl-namespace-aarch64.ini": namespace["sha256"],
}
for path, digest in required_device_files.items():
    if device_files.get(path) != digest:
        reject("MIXED_GENERATION", f"device baseline disagrees for {path}")
musl_path = "/system/lib/ld-musl-aarch64.so.1"
require_sha(device_files.get(musl_path), musl_path)
if set(device_files) != set(required_device_files) | {musl_path}:
    reject("EXPECTED_HASHES_INVALID", "device_files contains an unconsumed baseline")

print(generation_id)
PY
    )
    REMOTE_GENERATION="/data/a64deploy/helloworld-$P0_GENERATION_ID-$SHORT"
    REMOTE_SYSTEM_ANDROID="$REMOTE_GENERATION/android"
    STAGE="/data/local/tmp/helloworld-$P0_GENERATION_ID-$SHORT-$TS"
    EVIDENCE="$EVIDENCE_ROOT/helloworld-p0-deploy-$SHORT-$TS"
    if [[ "$PREFLIGHT_ONLY" == "1" ]]; then
        print "P0_PREFLIGHT_OK generation_id=$P0_GENERATION_ID"
        exit 0
    fi
fi

ROUTE_A_PLUGIN="$SRC/system/lib64/appspawn/libwestlake_android_child.z.so"
ROUTE_A_SEALED_MANIFEST="$SRC/route-a-sealed.sha256"
ROUTE_A_SEALED_DIR=""
SEALED_GENERATION=""
if [[ -f "$ROUTE_A_SEALED_MANIFEST" ]]; then
    ROUTE_A_SEALED_DIR=$(find "$SRC/system/lib64/westlake/route-a" \
        -mindepth 1 -maxdepth 1 -type d | head -n 1)
    [[ -n "$ROUTE_A_SEALED_DIR" ]] || {
        print -u2 "ERROR: sealed Route-A manifest has no generation directory"
        exit 1
    }
    SEALED_GENERATION=$(basename "$ROUTE_A_SEALED_DIR")
fi

if [[ "$P0_MODE" == "1" ]]; then
    p0_candidate_hash()
    {
        /usr/bin/jq -er --arg path "$1" '.candidate_files[$path]' "$EXPECTED_HASHES_MANIFEST"
    }

    p0_device_hash()
    {
        /usr/bin/jq -er --arg path "$1" '.device_files[$path]' "$EXPECTED_HASHES_MANIFEST"
    }

    # No EXPECTED_* environment override is honored in P0.  Every selected
    # byte comes from the separately supplied expected-hashes manifest.
    EXPECTED_APPSPAWN="$(p0_candidate_hash appspawn-x)"
    EXPECTED_CFG="$(p0_candidate_hash appspawn_x.cfg)"
    EXPECTED_SANDBOX_CFG="$(p0_candidate_hash appdata-sandbox.json)"
    EXPECTED_HAP_WRAPPER="$(p0_candidate_hash system/lib64/libwestlake_hap_domain_wrapper.so)"
    EXPECTED_ROUTE_A_PLUGIN="$(p0_candidate_hash system/lib64/appspawn/libwestlake_android_child.z.so)"
    EXPECTED_APK="$(/usr/bin/jq -er '.apk_sha256' "$EXPECTED_HASHES_MANIFEST")"
    EXPECTED_ART="$(p0_candidate_hash system/android/lib64/libart.so)"
    EXPECTED_ANDROID_RUNTIME="$(p0_candidate_hash system/android/lib64/liboh_android_runtime.so)"
    EXPECTED_BRIDGE="$(p0_candidate_hash system/android/lib64/liboh_adapter_bridge.so)"
    EXPECTED_ROUTE_A_PROVIDER="$(p0_candidate_hash system/android/lib64/libwestlake_android_runtime_provider.so)"
    EXPECTED_HWUI="$(p0_candidate_hash system/android/lib64/libhwui.so)"
    EXPECTED_HWUI_SHIM="$(p0_candidate_hash system/android/lib64/liboh_hwui_shim.so)"
    EXPECTED_RTTI="$(p0_candidate_hash system/android/lib64/liboh_skia_rtti_shim.so)"
    EXPECTED_ANDROIDFW="$(p0_candidate_hash system/android/lib64/libandroidfw.so)"
    EXPECTED_MINIKIN="$(p0_candidate_hash system/android/lib64/libminikin.so)"
    EXPECTED_PROFILE="$(p0_candidate_hash system/android/lib64/libprofile.so)"
    EXPECTED_UNWINDSTACK="$(p0_candidate_hash system/android/lib64/libunwindstack.so)"
    EXPECTED_FONTS="$(p0_candidate_hash system/android/etc/fonts.xml)"
    EXPECTED_APPMS="$(p0_candidate_hash system/lib64/libappms.z.so)"
    EXPECTED_CLIENT="$(p0_candidate_hash system/lib64/libappspawn_client.z.so)"
    EXPECTED_BMS="$(p0_candidate_hash system/lib64/libbms.z.so)"
    EXPECTED_INSTALLS="$(p0_candidate_hash system/lib64/libinstalls.z.so)"
    EXPECTED_INSTALLER="$(p0_candidate_hash system/lib64/libapk_installer.so)"
    EXPECTED_LZMA="$(p0_candidate_hash system/android/lib64/liblzma.so)"
    EXPECTED_SHARED_LIBZ="$(p0_candidate_hash system/android/lib64/libshared_libz.z.so)"
    EXPECTED_THREAD_GUARD="$(p0_candidate_hash system/android/lib64/libwestlake_thread_guard_registry.so)"
    ABILITYMS_SRC="$SRC/system/lib64/platformsdk/libabilityms.z.so"
    EXPECTED_ABILITYMS="$(p0_candidate_hash system/lib64/platformsdk/libabilityms.z.so)"
    EXPECTED_MUSL="$(p0_device_hash /system/lib/ld-musl-aarch64.so.1)"
    EXPECTED_SKIA_PROVIDER="$(p0_device_hash /system/lib64/libskia_canvaskit.z.so)"
    EXPECTED_NAMESPACE_MANIFEST="$(p0_device_hash /system/etc/ld-musl-namespace-aarch64.ini)"
    EXPECTED_OH_ADAPTER_FRAMEWORK="$(p0_candidate_hash system/android/framework/oh-adapter-framework.jar)"
    EXPECTED_BOOT_ART="$(p0_candidate_hash system/android/framework/arm64/boot.art)"
    EXPECTED_BOOT_OAT="$(p0_candidate_hash system/android/framework/arm64/boot.oat)"
    EXPECTED_BOOT_VDEX="$(p0_candidate_hash system/android/framework/arm64/boot.vdex)"
else
    # Legacy non-P0 compatibility.  This branch deliberately retains its old
    # defaults; it is unreachable from the explicit P0 interface above.
    EXPECTED_APPSPAWN="${EXPECTED_APPSPAWN:-$(/usr/bin/shasum -a 256 "$SRC/appspawn-x" | /usr/bin/awk '{print $1}')}"
    EXPECTED_CFG="${EXPECTED_CFG:-$(/usr/bin/shasum -a 256 "$CFG" | /usr/bin/awk '{print $1}')}"
    if [[ -f "$SANDBOX_CFG" ]]; then
        EXPECTED_SANDBOX_CFG="${EXPECTED_SANDBOX_CFG:-$(/usr/bin/shasum -a 256 "$SANDBOX_CFG" | /usr/bin/awk '{print $1}')}"
    else
        EXPECTED_SANDBOX_CFG="${EXPECTED_SANDBOX_CFG:-SKIPPED}"
    fi
    EXPECTED_HAP_WRAPPER="${EXPECTED_HAP_WRAPPER:-$(/usr/bin/shasum -a 256 "$SRC/system/lib64/libwestlake_hap_domain_wrapper.so" | /usr/bin/awk '{print $1}')}"
    if [[ -f "$ROUTE_A_PLUGIN" ]]; then
        EXPECTED_ROUTE_A_PLUGIN="${EXPECTED_ROUTE_A_PLUGIN:-$(/usr/bin/shasum -a 256 "$ROUTE_A_PLUGIN" | /usr/bin/awk '{print $1}')}"
    else
        EXPECTED_ROUTE_A_PLUGIN="${EXPECTED_ROUTE_A_PLUGIN:-SKIPPED}"
    fi
    if [[ "$RUN_APK_SANITY" == "1" ]]; then
        EXPECTED_APK="${EXPECTED_APK:-$(/usr/bin/shasum -a 256 "$APK" | /usr/bin/awk '{print $1}')}"
    else
        EXPECTED_APK="${EXPECTED_APK:-SKIPPED}"
    fi
    EXPECTED_ART="${EXPECTED_ART:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/libart.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_ANDROID_RUNTIME="${EXPECTED_ANDROID_RUNTIME:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/liboh_android_runtime.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_BRIDGE="${EXPECTED_BRIDGE:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so" | /usr/bin/awk '{print $1}')}"
    if [[ -f "$SYSTEM_ANDROID/lib64/libwestlake_android_runtime_provider.so" ]]; then
        EXPECTED_ROUTE_A_PROVIDER="${EXPECTED_ROUTE_A_PROVIDER:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/libwestlake_android_runtime_provider.so" | /usr/bin/awk '{print $1}')}"
    else
        EXPECTED_ROUTE_A_PROVIDER="${EXPECTED_ROUTE_A_PROVIDER:-SKIPPED}"
    fi
    EXPECTED_HWUI="${EXPECTED_HWUI:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/libhwui.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_HWUI_SHIM="${EXPECTED_HWUI_SHIM:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/liboh_hwui_shim.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_RTTI="${EXPECTED_RTTI:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/liboh_skia_rtti_shim.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_ANDROIDFW="${EXPECTED_ANDROIDFW:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/libandroidfw.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_MINIKIN="${EXPECTED_MINIKIN:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/libminikin.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_PROFILE="${EXPECTED_PROFILE:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/libprofile.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_UNWINDSTACK="${EXPECTED_UNWINDSTACK:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/lib64/libunwindstack.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_FONTS="${EXPECTED_FONTS:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/etc/fonts.xml" | /usr/bin/awk '{print $1}')}"
    EXPECTED_APPMS="${EXPECTED_APPMS:-$(/usr/bin/shasum -a 256 "$SRC/system/lib64/libappms.z.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_CLIENT=f4df7769e64bf836015b5374f4f98915a1279a88e97f05714879855d55d3658f
    EXPECTED_BMS=f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105
    EXPECTED_INSTALLS=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
    EXPECTED_INSTALLER=184d40a56a9116ab87d079413ba31d92e3d45c86a2f9b1088ffc97725ec650f9
    EXPECTED_LZMA="${EXPECTED_LZMA:-$(/usr/bin/shasum -a 256 "$SRC/system/android/lib64/liblzma.so" | /usr/bin/awk '{print $1}')}"
    EXPECTED_SHARED_LIBZ="${EXPECTED_SHARED_LIBZ:-$(/usr/bin/shasum -a 256 "$SRC/system/android/lib64/libshared_libz.z.so" | /usr/bin/awk '{print $1}')}"
    ABILITYMS_SRC="${ABILITYMS_SRC:-$SRC/system/lib64/platformsdk/libabilityms.z.so}"
    if [[ ! -f "$ABILITYMS_SRC" ]]; then
        ABILITYMS_SRC="$ROOT/out/alexpc-rebuild-20260726/libabilityms.z.so.fn04.v2"
    fi
    EXPECTED_ABILITYMS="${EXPECTED_ABILITYMS:-$(/usr/bin/shasum -a 256 "$ABILITYMS_SRC" | /usr/bin/awk '{print $1}')}"
    EXPECTED_MUSL=fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2
    EXPECTED_OH_ADAPTER_FRAMEWORK="${EXPECTED_OH_ADAPTER_FRAMEWORK:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/framework/oh-adapter-framework.jar" | /usr/bin/awk '{print $1}')}"
    EXPECTED_BOOT_ART="${EXPECTED_BOOT_ART:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/framework/arm64/boot.art" | /usr/bin/awk '{print $1}')}"
    EXPECTED_BOOT_OAT="${EXPECTED_BOOT_OAT:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/framework/arm64/boot.oat" | /usr/bin/awk '{print $1}')}"
    EXPECTED_BOOT_VDEX="${EXPECTED_BOOT_VDEX:-$(/usr/bin/shasum -a 256 "$SYSTEM_ANDROID/framework/arm64/boot.vdex" | /usr/bin/awk '{print $1}')}"
fi

mkdir -p "$EVIDENCE"
if [[ "$P0_MODE" == "1" ]]; then
    /bin/cp "$DEPLOY_MANIFEST" "$EVIDENCE/selected-deploy-manifest.json"
    /bin/cp "$EXPECTED_HASHES_MANIFEST" "$EVIDENCE/expected-hashes.json"
fi
exec > >(tee -a "$EVIDENCE/script.log")
exec 2>&1

dev()
{
    "$HDC" -t "$TARGET" shell "$1"
}

local_hash()
{
    /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'
}

device_hash()
{
    dev "sha256sum $1" | /usr/bin/awk '{print $1}'
}

verify_remote_sealed_tree()
{
    local remote_root="$1"
    local phase="$2"
    local expected relative_path name actual

    while read -r expected relative_path; do
        [[ -n "$expected" && -n "$relative_path" ]] || continue
        name=$(basename "$relative_path")
        actual=$(device_hash "$remote_root/$name")
        [[ "$actual" == "$expected" ]] ||
            fail_and_stop "$phase sealed Route-A hash mismatch: $name expected=$expected actual=${actual:-MISSING}"
    done <"$ROUTE_A_SEALED_MANIFEST"
}

app_pid_by_bundle()
{
    local package="$1"
    local pid
    pid=$(dev "pidof $package" | /usr/bin/tr -d '\r ' || true)
    if [[ -n "$pid" ]]; then
        print -r -- "$pid"
        return 0
    fi

    pid=$(
      dev "aa dump -a 2>/dev/null" |
        /usr/bin/tr -d '\r' |
        /usr/bin/awk -v package="$package" '
          /process name \[/ {
            owner = index($0, "[" package "]") > 0
            next
          }
          owner && match($0, /pid #[0-9]+/) {
            value = substr($0, RSTART, RLENGTH)
            sub(/^pid #/, "", value)
            print value
            exit
          }
        '
    )
    if [[ "$pid" =~ ^[0-9]+$ ]] &&
       [[ "$(dev "test -d /proc/$pid && echo PRESENT || true" | /usr/bin/tr -d '\r ')" == "PRESENT" ]]; then
        print -r -- "$pid"
    fi
}

wait_for_device()
{
    local attempt probe
    for attempt in {1..180}; do
        if "$HDC" list targets | /usr/bin/awk -v serial="$TARGET" \
            '$1 == serial { found=1 } END { exit !found }'; then
            probe=$(dev "echo ok" 2>&1 || true)
            if [[ "$probe" == "ok" ]]; then
                return 0
            fi
        fi
        sleep 1
    done
    print -u2 "ERROR: $TARGET did not return"
    return 1
}

fail_and_stop()
{
    print -u2 "FAIL: $*"
    {
        print "experiment: fn01-fn03-r18-runtime-deploy"
        print "target: $TARGET"
        print "timestamp: $TS"
        print "verdict: FAIL"
        print "reason: $*"
    } >"$EVIDENCE/DEPLOY-VERDICT.yaml"
    exit 1
}

{
    print "target=$TARGET"
    print "run_dir=$EVIDENCE"
    print "src=$SRC"
    print "system_android=$SYSTEM_ANDROID"
    print "cfg=$CFG"
    print "sandbox_cfg=$SANDBOX_CFG"
    print "expected_sandbox_cfg=$EXPECTED_SANDBOX_CFG"
    print "apk=$APK"
    print "app_package=$APP_PACKAGE"
    print "app_activity=$APP_ACTIVITY"
    print "run_apk_sanity=$RUN_APK_SANITY"
    print "hap_domain_wrapper=$SRC/system/lib64/libwestlake_hap_domain_wrapper.so"
    print "route_a_plugin=$ROUTE_A_PLUGIN"
    print "expected_route_a_plugin=$EXPECTED_ROUTE_A_PLUGIN"
    print "expected_route_a_provider=$EXPECTED_ROUTE_A_PROVIDER"
    print "abilityms_src=$ABILITYMS_SRC"
    print "expected_abilityms=$EXPECTED_ABILITYMS"
    print "remote_generation=$REMOTE_GENERATION"
    print "stage=$STAGE"
    print "p0_mode=$P0_MODE"
    if [[ "$P0_MODE" == "1" ]]; then
        print "generation_id=$P0_GENERATION_ID"
        print "selected_deploy_manifest=$EVIDENCE/selected-deploy-manifest.json"
        print "expected_hashes_manifest=$EVIDENCE/expected-hashes.json"
        print "expected_skia_provider=$EXPECTED_SKIA_PROVIDER"
        print "expected_namespace_manifest=$EXPECTED_NAMESPACE_MANIFEST"
    fi
    date -u
} >"$EVIDENCE/METADATA.txt"

# --- local artifact preflight ---
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]] || fail_and_stop "local libart.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_android_runtime.so")" == "$EXPECTED_ANDROID_RUNTIME" ]] || fail_and_stop "local liboh_android_runtime.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_adapter_bridge.so")" == "$EXPECTED_BRIDGE" ]] || fail_and_stop "local liboh_adapter_bridge.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libhwui.so")" == "$EXPECTED_HWUI" ]] || fail_and_stop "local libhwui.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_hwui_shim.so")" == "$EXPECTED_HWUI_SHIM" ]] || fail_and_stop "local liboh_hwui_shim.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/liboh_skia_rtti_shim.so")" == "$EXPECTED_RTTI" ]] || fail_and_stop "local liboh_skia_rtti_shim.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libandroidfw.so")" == "$EXPECTED_ANDROIDFW" ]] || fail_and_stop "local libandroidfw.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libminikin.so")" == "$EXPECTED_MINIKIN" ]] || fail_and_stop "local libminikin.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libprofile.so")" == "$EXPECTED_PROFILE" ]] || fail_and_stop "local libprofile.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/lib64/libunwindstack.so")" == "$EXPECTED_UNWINDSTACK" ]] || fail_and_stop "local libunwindstack.so hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/etc/fonts.xml")" == "$EXPECTED_FONTS" ]] || fail_and_stop "local fonts.xml hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/framework/oh-adapter-framework.jar")" == "$EXPECTED_OH_ADAPTER_FRAMEWORK" ]] || fail_and_stop "local oh-adapter-framework.jar hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/framework/arm64/boot.art")" == "$EXPECTED_BOOT_ART" ]] || fail_and_stop "local boot.art hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/framework/arm64/boot.oat")" == "$EXPECTED_BOOT_OAT" ]] || fail_and_stop "local boot.oat hash mismatch"
[[ "$(local_hash "$SYSTEM_ANDROID/framework/arm64/boot.vdex")" == "$EXPECTED_BOOT_VDEX" ]] || fail_and_stop "local boot.vdex hash mismatch"
[[ "$(local_hash "$CFG")" == "$EXPECTED_CFG" ]] || fail_and_stop "local appspawn_x.cfg hash mismatch"
if [[ "$EXPECTED_SANDBOX_CFG" != "SKIPPED" ]]; then
    [[ "$(local_hash "$SANDBOX_CFG")" == "$EXPECTED_SANDBOX_CFG" ]] || fail_and_stop "local appdata-sandbox.json hash mismatch"
    jq -e --arg package "$APP_PACKAGE" --arg owner "android:$APP_PACKAGE" \
        '.individual[0][$package][0] |
         select(.appIdentifier == $owner) |
         .["mount-paths"][] |
         select(.["src-path"] == "/system/android" and
                .["sandbox-path"] == "/system/android" and
                .["sandbox-flags"] == ["bind", "rec"] and
                .["check-action-status"] == "true")' \
        "$SANDBOX_CFG" >/dev/null || fail_and_stop "local Android package sandbox mapping missing"
    jq -e --arg package "$APP_PACKAGE" --arg apk_dir "/data/app/el1/bundle/public/$APP_PACKAGE/android" \
        '.individual[0][$package][0] |
         .["mount-paths"][] |
         select(.["src-path"] == $apk_dir and
                .["sandbox-path"] == $apk_dir and
                .["sandbox-flags"] == ["bind", "rec"] and
                .["check-action-status"] == "true")' \
        "$SANDBOX_CFG" >/dev/null || fail_and_stop "local Android APK sourceDir sandbox mapping missing"
fi
[[ "$(local_hash "$SRC/appspawn-x")" == "$EXPECTED_APPSPAWN" ]] || fail_and_stop "local appspawn-x hash mismatch"
[[ "$(local_hash "$SRC/system/lib64/libwestlake_hap_domain_wrapper.so")" == "$EXPECTED_HAP_WRAPPER" ]] || fail_and_stop "local libwestlake_hap_domain_wrapper.so hash mismatch"
if [[ "$EXPECTED_ROUTE_A_PLUGIN" != "SKIPPED" ]]; then
    [[ "$(local_hash "$ROUTE_A_PLUGIN")" == "$EXPECTED_ROUTE_A_PLUGIN" ]] || fail_and_stop "local Route-A child plugin hash mismatch"
fi
if [[ "$EXPECTED_ROUTE_A_PROVIDER" != "SKIPPED" ]]; then
    [[ "$(local_hash "$SYSTEM_ANDROID/lib64/libwestlake_android_runtime_provider.so")" == "$EXPECTED_ROUTE_A_PROVIDER" ]] || fail_and_stop "local Route-A runtime provider hash mismatch"
fi
if [[ -n "$ROUTE_A_SEALED_DIR" ]]; then
    [[ "$(find "$ROUTE_A_SEALED_DIR" -type f | wc -l | tr -d ' ')" == "27" ]] ||
        fail_and_stop "sealed Route-A generation file count mismatch"
    (cd "$SRC" && /usr/bin/shasum -a 256 -c "$ROUTE_A_SEALED_MANIFEST" >/dev/null) ||
        fail_and_stop "sealed Route-A generation manifest mismatch"
fi
if [[ "$RUN_APK_SANITY" == "1" ]]; then
    [[ "$(local_hash "$APK")" == "$EXPECTED_APK" ]] || fail_and_stop "local APK hash mismatch"
fi
[[ "$(local_hash "$SRC/system/lib64/libappms.z.so")" == "$EXPECTED_APPMS" ]] || fail_and_stop "local libappms.z.so hash mismatch"
[[ "$(local_hash "$SRC/system/lib64/libappspawn_client.z.so")" == "$EXPECTED_CLIENT" ]] || fail_and_stop "local libappspawn_client.z.so hash mismatch"
[[ "$(local_hash "$SRC/system/lib64/libbms.z.so")" == "$EXPECTED_BMS" ]] || fail_and_stop "local libbms.z.so hash mismatch"
[[ "$(local_hash "$SRC/system/lib64/libinstalls.z.so")" == "$EXPECTED_INSTALLS" ]] || fail_and_stop "local libinstalls.z.so hash mismatch"
[[ "$(local_hash "$SRC/system/lib64/libapk_installer.so")" == "$EXPECTED_INSTALLER" ]] || fail_and_stop "local libapk_installer.so hash mismatch"
[[ "$(local_hash "$SRC/system/android/lib64/liblzma.so")" == "$EXPECTED_LZMA" ]] || fail_and_stop "local liblzma.so hash mismatch"
[[ "$(local_hash "$SRC/system/android/lib64/libshared_libz.z.so")" == "$EXPECTED_SHARED_LIBZ" ]] || fail_and_stop "local libshared_libz.z.so hash mismatch"
[[ "$(local_hash "$ABILITYMS_SRC")" == "$EXPECTED_ABILITYMS" ]] || fail_and_stop "local libabilityms.z.so hash mismatch"
if [[ "$P0_MODE" == "1" ]]; then
    [[ "$(local_hash "$SRC/system/android/lib64/libwestlake_thread_guard_registry.so")" == "$EXPECTED_THREAD_GUARD" ]] ||
        fail_and_stop "local libwestlake_thread_guard_registry.so hash mismatch"
fi
[[ "$(/usr/bin/find "$SYSTEM_ANDROID/framework/arm64" -maxdepth 1 -type f | /usr/bin/wc -l | /usr/bin/tr -d ' ')" == "27" ]] || fail_and_stop "framework/arm64 file count mismatch"

wait_for_device
fullname=$(dev "param get const.ohos.fullname" | /usr/bin/tr -d '\r ')
arch=$(dev "uname -m" | /usr/bin/tr -d '\r')
initial_selinux=$(dev "getenforce" | /usr/bin/tr -d '\r ')
print "OS=$fullname arch=$arch"
[[ "$fullname" == "OpenHarmony-6.1.0.31" ]] || fail_and_stop "unexpected OS: $fullname"
[[ "$arch" == "aarch64" ]] || fail_and_stop "unexpected arch: $arch"
if [[ "$P0_MODE" == "1" ]]; then
    # These checks happen before target mount, force-stop, file send or any
    # other mutation.  A missing target provider or drifted namespace makes
    # this a different generation and must fail closed.
    [[ "$(device_hash /system/lib64/libskia_canvaskit.z.so)" == "$EXPECTED_SKIA_PROVIDER" ]] ||
        fail_and_stop "pre-deploy Skia provider missing or hash mismatch"
    [[ "$(device_hash /system/etc/ld-musl-namespace-aarch64.ini)" == "$EXPECTED_NAMESPACE_MANIFEST" ]] ||
        fail_and_stop "pre-deploy namespace manifest hash mismatch"
    [[ "$(device_hash /system/lib/ld-musl-aarch64.so.1)" == "$EXPECTED_MUSL" ]] ||
        fail_and_stop "pre-deploy musl loader hash mismatch"
fi

# --- record pre-deploy identity and any existing system files for rollback ---
{
    print "boot_id:"
    dev "cat /proc/sys/kernel/random/boot_id"
    print "getenforce:"
    dev "getenforce"
    print "uptime:"
    dev "cat /proc/uptime"
    print "existing system files:"
    dev "sha256sum /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg /system/etc/sandbox/appdata-sandbox.json /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib64/libskia_canvaskit.z.so /system/etc/ld-musl-namespace-aarch64.ini /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/lib/libc_musl.so 2>/dev/null || true"
    dev "ls -lZ /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg /system/etc/sandbox/appdata-sandbox.json /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/lib/libc_musl.so /system/android 2>/dev/null || true"
} >"$EVIDENCE/pre-deploy-identity.txt"

"$HDC" -t "$TARGET" target mount >"$EVIDENCE/target-mount-1.txt" 2>&1
dev "aa force-stop $APP_PACKAGE 2>/dev/null || true"
dev "mkdir -p $STAGE $REMOTE_GENERATION /system/etc/init /system/lib64/platformsdk /system/lib64/appspawn"
"$HDC" -t "$TARGET" file send "$SYSTEM_ANDROID" "$REMOTE_GENERATION" >"$EVIDENCE/send-systemandroid.txt" 2>&1
dev "mkdir -p $REMOTE_GENERATION/android/lib64"
"$HDC" -t "$TARGET" file send "$CFG" "$STAGE/appspawn_x.cfg" >"$EVIDENCE/send-appspawn-cfg.txt" 2>&1
if [[ "$EXPECTED_SANDBOX_CFG" != "SKIPPED" ]]; then
    "$HDC" -t "$TARGET" file send "$SANDBOX_CFG" "$STAGE/appdata-sandbox.json" >"$EVIDENCE/send-appdata-sandbox.txt" 2>&1
fi
"$HDC" -t "$TARGET" file send "$SRC/appspawn-x" "$STAGE/appspawn-x" >"$EVIDENCE/send-appspawn-x.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libwestlake_hap_domain_wrapper.so" "$STAGE/libwestlake_hap_domain_wrapper.so" >"$EVIDENCE/send-hap-domain-wrapper.txt" 2>&1
if [[ "$EXPECTED_ROUTE_A_PLUGIN" != "SKIPPED" ]]; then
    "$HDC" -t "$TARGET" file send "$ROUTE_A_PLUGIN" "$STAGE/libwestlake_android_child.z.so" >"$EVIDENCE/send-route-a-child-plugin.txt" 2>&1
fi
if [[ -n "$ROUTE_A_SEALED_DIR" ]]; then
    dev "rm -rf $STAGE/$SEALED_GENERATION && mkdir -p $STAGE/$SEALED_GENERATION"
    : >"$EVIDENCE/send-route-a-sealed-generation.txt"
    for sealed_file in "$ROUTE_A_SEALED_DIR"/*; do
        [[ -f "$sealed_file" && ! -L "$sealed_file" ]] || continue
        sealed_name=$(basename "$sealed_file")
        print "sending $sealed_name" >>"$EVIDENCE/send-route-a-sealed-generation.txt"
        "$HDC" -t "$TARGET" file send "$sealed_file" \
            "$STAGE/$SEALED_GENERATION/$sealed_name" \
            >>"$EVIDENCE/send-route-a-sealed-generation.txt" 2>&1 ||
            fail_and_stop "sealed Route-A file send failed: $sealed_name"
    done
    "$HDC" -t "$TARGET" file send "$ROUTE_A_SEALED_MANIFEST" "$STAGE/route-a-sealed.sha256" >"$EVIDENCE/send-route-a-sealed-manifest.txt" 2>&1
    # hdc can report a successful directory transfer while materializing
    # individual files as zero bytes.  Host-side per-file comparisons make
    # that failure explicit before appspawn is stopped or /system is changed.
    verify_remote_sealed_tree "$STAGE/$SEALED_GENERATION" "post-transfer"
fi
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libappms.z.so" "$STAGE/libappms.z.so" >"$EVIDENCE/send-libappms.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libappspawn_client.z.so" "$STAGE/libappspawn_client.z.so" >"$EVIDENCE/send-libappspawn-client.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libbms.z.so" "$STAGE/libbms.z.so" >"$EVIDENCE/send-libbms.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libinstalls.z.so" "$STAGE/libinstalls.z.so" >"$EVIDENCE/send-libinstalls.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/lib64/libapk_installer.so" "$STAGE/libapk_installer.so" >"$EVIDENCE/send-libapk-installer.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/android/lib64/liblzma.so" "$STAGE/liblzma.so" >"$EVIDENCE/send-liblzma.txt" 2>&1
"$HDC" -t "$TARGET" file send "$SRC/system/android/lib64/libshared_libz.z.so" "$STAGE/libshared_libz.z.so" >"$EVIDENCE/send-libshared-libz.txt" 2>&1
dev "cp $STAGE/liblzma.so $REMOTE_GENERATION/android/lib64/liblzma.so"
dev "cp $STAGE/libshared_libz.z.so $REMOTE_GENERATION/android/lib64/libshared_libz.z.so"
dev "chmod 0644 $REMOTE_GENERATION/android/lib64/liblzma.so $REMOTE_GENERATION/android/lib64/libshared_libz.z.so"
"$HDC" -t "$TARGET" file send "$ABILITYMS_SRC" "$STAGE/libabilityms.z.so" >"$EVIDENCE/send-libabilityms.txt" 2>&1
if [[ "$RUN_APK_SANITY" == "1" ]]; then
    "$HDC" -t "$TARGET" file send "$APK" "$STAGE/$APP_REMOTE_NAME" >"$EVIDENCE/send-apk.txt" 2>&1
fi

dev "begetctl stop_service appspawn-x >/dev/null 2>&1 || true"
dev "cp $STAGE/appspawn-x /system/bin/appspawn-x"
dev "cp $STAGE/libwestlake_hap_domain_wrapper.so /system/lib64/libwestlake_hap_domain_wrapper.so"
if [[ "$EXPECTED_ROUTE_A_PLUGIN" != "SKIPPED" ]]; then
    dev "mkdir -p /system/lib64/appspawn"
    dev "cp $STAGE/libwestlake_android_child.z.so /system/lib64/appspawn/libwestlake_android_child.z.so"
fi
if [[ -n "$ROUTE_A_SEALED_DIR" ]]; then
    # Route-A generations are immutable and generation-addressed.  Keeping
    # abandoned generations on the small /system filesystem can truncate a
    # later copy even when hdc/cp returns success.  Record and prune only this
    # experiment-owned directory after the new generation has been staged and
    # hash-verified on /data.
    dev "find /system/lib64/westlake/route-a -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null || true" \
        >"$EVIDENCE/pre-copy-route-a-generations.txt"
    dev "find /system/lib64/westlake/route-a -mindepth 1 -maxdepth 1 -type d ! -name '$SEALED_GENERATION' -exec rm -rf {} \; 2>/dev/null || true"
    dev "mkdir -p /system/lib64/westlake/route-a"
    dev "rm -rf /system/lib64/westlake/route-a/$SEALED_GENERATION"
    dev "cp -R $STAGE/$SEALED_GENERATION /system/lib64/westlake/route-a/$SEALED_GENERATION"
    dev "chown -R root:root /system/lib64/westlake/route-a/$SEALED_GENERATION"
    dev "find /system/lib64/westlake/route-a/$SEALED_GENERATION -type d -exec chmod 0755 {} \;"
    dev "find /system/lib64/westlake/route-a/$SEALED_GENERATION -type f -exec chmod 0644 {} \;"
    dev "find /system/lib64/westlake/route-a/$SEALED_GENERATION -exec chcon u:object_r:system_lib_file:s0 {} \;"
    verify_remote_sealed_tree "/system/lib64/westlake/route-a/$SEALED_GENERATION" "post-copy"
fi
dev "cp $STAGE/libappms.z.so /system/lib64/libappms.z.so"
dev "cp $STAGE/libappspawn_client.z.so /system/lib64/libappspawn_client.z.so"
dev "cp $STAGE/libbms.z.so /system/lib64/libbms.z.so"
dev "cp $STAGE/libinstalls.z.so /system/lib64/libinstalls.z.so"
dev "cp $STAGE/libapk_installer.so /system/lib64/libapk_installer.so"
dev "cp $STAGE/libappms.z.so /system/lib64/platformsdk/libappms.z.so"
dev "cp $STAGE/libappspawn_client.z.so /system/lib64/platformsdk/libappspawn_client.z.so"
dev "cp $STAGE/libbms.z.so /system/lib64/platformsdk/libbms.z.so"
dev "cp $STAGE/libinstalls.z.so /system/lib64/platformsdk/libinstalls.z.so"
dev "cp $STAGE/libapk_installer.so /system/lib64/platformsdk/libapk_installer.so"
dev "cp $STAGE/libabilityms.z.so /system/lib64/platformsdk/libabilityms.z.so"
dev "cp $STAGE/appspawn_x.cfg /system/etc/init/appspawn_x.cfg"
if [[ "$EXPECTED_SANDBOX_CFG" != "SKIPPED" ]]; then
    dev "mkdir -p /system/etc/sandbox"
    dev "cp $STAGE/appdata-sandbox.json /system/etc/sandbox/appdata-sandbox.json"
fi
dev "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so"

dev "chown root:root /system/bin/appspawn-x /system/lib64/libwestlake_hap_domain_wrapper.so /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/lib64/platformsdk/libappms.z.so /system/lib64/platformsdk/libappspawn_client.z.so /system/lib64/platformsdk/libbms.z.so /system/lib64/platformsdk/libinstalls.z.so /system/lib64/platformsdk/libapk_installer.so /system/lib64/platformsdk/libabilityms.z.so /system/etc/init/appspawn_x.cfg 2>/dev/null || true"
dev "chmod 0755 /system/bin/appspawn-x /system/lib64/libwestlake_hap_domain_wrapper.so /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/lib64/platformsdk/libappms.z.so /system/lib64/platformsdk/libappspawn_client.z.so /system/lib64/platformsdk/libbms.z.so /system/lib64/platformsdk/libinstalls.z.so /system/lib64/platformsdk/libapk_installer.so /system/lib64/platformsdk/libabilityms.z.so 2>/dev/null || true"
dev "chmod 0550 /system/etc/init/appspawn_x.cfg"
if [[ "$EXPECTED_SANDBOX_CFG" != "SKIPPED" ]]; then
    dev "chown root:root /system/etc/sandbox/appdata-sandbox.json"
    dev "chmod 0644 /system/etc/sandbox/appdata-sandbox.json"
    dev "chcon u:object_r:system_etc_file:s0 /system/etc/sandbox/appdata-sandbox.json 2>/dev/null || restorecon -F /system/etc/sandbox/appdata-sandbox.json"
fi
dev "chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x"
dev "restorecon -F /system/lib64/libwestlake_hap_domain_wrapper.so /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/lib64/platformsdk/libappms.z.so /system/lib64/platformsdk/libappspawn_client.z.so /system/lib64/platformsdk/libbms.z.so /system/lib64/platformsdk/libinstalls.z.so /system/lib64/platformsdk/libapk_installer.so /system/lib64/platformsdk/libabilityms.z.so 2>/dev/null || true"
dev "chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg 2>/dev/null || restorecon -F /system/etc/init/appspawn_x.cfg"
dev "chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"

[[ "$(device_hash /system/bin/appspawn-x)" == "$EXPECTED_APPSPAWN" ]] || fail_and_stop "post-copy appspawn-x hash mismatch"
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]] || fail_and_stop "post-copy appspawn_x.cfg hash mismatch"
if [[ "$EXPECTED_SANDBOX_CFG" != "SKIPPED" ]]; then
    [[ "$(device_hash /system/etc/sandbox/appdata-sandbox.json)" == "$EXPECTED_SANDBOX_CFG" ]] || fail_and_stop "post-copy appdata-sandbox.json hash mismatch"
fi
[[ "$(device_hash /system/lib64/libwestlake_hap_domain_wrapper.so)" == "$EXPECTED_HAP_WRAPPER" ]] || fail_and_stop "post-copy libwestlake_hap_domain_wrapper.so hash mismatch"
if [[ "$EXPECTED_ROUTE_A_PLUGIN" != "SKIPPED" ]]; then
    [[ "$(device_hash /system/lib64/appspawn/libwestlake_android_child.z.so)" == "$EXPECTED_ROUTE_A_PLUGIN" ]] || fail_and_stop "post-copy Route-A child plugin hash mismatch"
fi
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_APPMS" ]] || fail_and_stop "post-copy libappms.z.so hash mismatch"
[[ "$(device_hash /system/lib64/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]] || fail_and_stop "post-copy libappspawn_client.z.so hash mismatch"
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]] || fail_and_stop "post-copy libbms.z.so hash mismatch"
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]] || fail_and_stop "post-copy libinstalls.z.so hash mismatch"
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]] || fail_and_stop "post-copy libapk_installer.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libappms.z.so)" == "$EXPECTED_APPMS" ]] || fail_and_stop "post-copy platformsdk libappms.z.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]] || fail_and_stop "post-copy platformsdk libappspawn_client.z.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libbms.z.so)" == "$EXPECTED_BMS" ]] || fail_and_stop "post-copy platformsdk libbms.z.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]] || fail_and_stop "post-copy platformsdk libinstalls.z.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]] || fail_and_stop "post-copy platformsdk libapk_installer.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libabilityms.z.so)" == "$EXPECTED_ABILITYMS" ]] || fail_and_stop "post-copy platformsdk libabilityms.z.so hash mismatch"
[[ "$(device_hash "$REMOTE_SYSTEM_ANDROID/lib64/libart.so")" == "$EXPECTED_ART" ]] || fail_and_stop "remote libart.so hash mismatch"
[[ "$(device_hash /system/lib/libc_musl.so)" == "$EXPECTED_MUSL" ]] || fail_and_stop "libc_musl.so hash mismatch"
dev "sync"

print "Pre-reboot disk install verified; rebooting $TARGET"
"$HDC" -t "$TARGET" target boot >"$EVIDENCE/target-boot.txt" 2>&1 || true
wait_for_device
# Some D600 boards need extra settle time before shell commands are reliable.
sleep 30

"$HDC" -t "$TARGET" target mount >"$EVIDENCE/target-mount-2.txt" 2>&1
# target mount can bounce the hdc daemon; wait again.
wait_for_device
sleep 5

dev "mkdir -p /system/android"
dev "umount /system/android 2>/dev/null || true"
dev "mount --bind $REMOTE_SYSTEM_ANDROID /system/android"
# hdc file send creates remote directories as root:root 0750.  Android app
# children run under application UIDs and must be able to traverse the
# system-image tree; match normal /system directory semantics before spawn.
dev "find /system/android -type d -exec chmod 0755 {} \;"
dev "cp $STAGE/liblzma.so /system/android/lib64/liblzma.so"
dev "cp $STAGE/libshared_libz.z.so /system/android/lib64/libshared_libz.z.so"
dev "chmod 0644 /system/android/lib64/liblzma.so /system/android/lib64/libshared_libz.z.so"
# liboh_adapter_bridge.so links WLTG_* from this generation-local registry.
# appspawn-x resolves its transitive DT_NEEDED set before the Android runtime
# provider extends its namespace, so make the registry visible in the native
# system search path as well as in /system/android/lib64.
if [[ -f "$SRC/system/android/lib64/libwestlake_thread_guard_registry.so" ]]; then
    "$HDC" -t "$TARGET" file send \
        "$SRC/system/android/lib64/libwestlake_thread_guard_registry.so" \
        "$STAGE/libwestlake_thread_guard_registry.so" \
        >"$EVIDENCE/send-thread-guard-registry.txt" 2>&1
    dev "cp $STAGE/libwestlake_thread_guard_registry.so /system/lib64/libwestlake_thread_guard_registry.so"
    dev "chown root:root /system/lib64/libwestlake_thread_guard_registry.so"
    dev "chmod 0755 /system/lib64/libwestlake_thread_guard_registry.so"
    dev "restorecon -F /system/lib64/libwestlake_thread_guard_registry.so 2>/dev/null || chcon u:object_r:system_lib_file:s0 /system/lib64/libwestlake_thread_guard_registry.so"
    [[ "$(device_hash /system/lib64/libwestlake_thread_guard_registry.so)" == \
        "$(local_hash "$SRC/system/android/lib64/libwestlake_thread_guard_registry.so")" ]] ||
        fail_and_stop "post-copy libwestlake_thread_guard_registry.so hash mismatch"
fi
dev "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"

dev "find /system/android -exec chcon u:object_r:system_file:s0 {} \;"
dev "find /system/android -type d -exec chcon u:object_r:system_lib_file:s0 {} \;"
dev "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \;"
dev "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f; done"
dev "chcon u:object_r:system_fonts_file:s0 /system/android/etc/fonts.xml"
dev "cp /system/android/etc/fonts.xml /system/etc/fonts.xml"
dev "chcon u:object_r:system_fonts_file:s0 /system/etc/fonts.xml 2>/dev/null || true"
dev "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so"
dev "chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"
[[ "$PRESERVE_SELINUX" == "1" ]] ||
    fail_and_stop "changing the device SELinux state is not supported"
dev "param set persist.sys.abilityms.support_anco_app true"
dev "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
dev "param set ro.product.cpu.abilist arm64-v8a >/dev/null 2>&1 || true"
dev "param set ro.product.cpu.abilist64 arm64-v8a >/dev/null 2>&1 || true"
dev "power-shell wakeup; power-shell timeout -o 86400000; power-shell display -o 230" >/dev/null 2>&1 || true
dev "sync"

postboot_selinux=$(dev "getenforce" | /usr/bin/tr -d '\r ')
print "SELinux unchanged by script: preboot=$initial_selinux postboot=$postboot_selinux"

dev "
cat /proc/sys/kernel/random/boot_id
param get const.ohos.fullname
getenforce
cat /proc/uptime
param get persist.sys.abilityms.timeout_unit_time_ratio
sha256sum \
  /system/bin/appspawn-x \
  /system/etc/init/appspawn_x.cfg \
  /system/etc/sandbox/appdata-sandbox.json \
  /system/lib64/appspawn/libwestlake_android_child.z.so \
  /system/lib64/libskia_canvaskit.z.so \
  /system/etc/ld-musl-namespace-aarch64.ini \
  /system/android/lib64/libart.so \
  /system/android/lib64/libwestlake_android_runtime_provider.so \
  /system/android/lib64/liboh_android_runtime.so \
  /system/android/lib64/liboh_adapter_bridge.so \
  /system/android/lib64/libhwui.so \
  /system/android/lib64/liboh_hwui_shim.so \
  /system/android/lib64/liboh_skia_rtti_shim.so \
  /system/android/lib64/libandroidfw.so \
  /system/android/lib64/libminikin.so \
  /system/android/lib64/libprofile.so \
  /system/android/lib64/libunwindstack.so \
  /system/android/framework/oh-adapter-framework.jar \
  /system/android/framework/arm64/boot.art \
  /system/android/framework/arm64/boot.oat \
  /system/android/framework/arm64/boot.vdex \
  /system/lib64/libappms.z.so \
  /system/lib64/libappspawn_client.z.so \
  /system/lib64/libbms.z.so \
  /system/lib64/libinstalls.z.so \
  /system/lib64/libapk_installer.so \
  /system/lib64/platformsdk/libappms.z.so \
  /system/lib64/platformsdk/libappspawn_client.z.so \
  /system/lib64/platformsdk/libbms.z.so \
  /system/lib64/platformsdk/libinstalls.z.so \
  /system/lib64/platformsdk/libapk_installer.so \
  /system/lib64/platformsdk/libabilityms.z.so \
  /system/android/lib64/liblzma.so \
  /system/android/lib64/libshared_libz.z.so \
  /system/lib64/libwestlake_thread_guard_registry.so \
  /system/lib/ld-musl-aarch64.so.1 \
  /system/lib/libc_musl.so \
  /system/etc/fonts.xml
grep -n cgroup /system/etc/init/appspawn_x.cfg
readlink -f /system/lib/libc_musl.so
ls -lZ /system/bin/appspawn-x /system/etc/init/appspawn_x.cfg /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib/libc_musl.so /dev/unix/socket/AppSpawnX 2>/dev/null || true
ls -ldZ /system/android /system/android/framework /system/android/framework/framework-res.apk
grep AppSpawnX /proc/net/unix 2>/dev/null || true
cat /proc/cgroups
mount | grep cgroup
" >"$EVIDENCE/post-deploy-receipt.txt"

[[ "$(device_hash /system/android/lib64/libart.so)" == "$EXPECTED_ART" ]] || fail_and_stop "post-reboot libart.so hash mismatch"
if [[ "$EXPECTED_SANDBOX_CFG" != "SKIPPED" ]]; then
    # D600 init restores the stock ON profile during reboot.  The historical
    # Android adapter route requires the verified developer sandbox-off profile
    # to be re-applied after boot, before the first APK trigger.
    dev "cp $STAGE/appdata-sandbox.json /system/etc/sandbox/appdata-sandbox.json"
    dev "chown root:root /system/etc/sandbox/appdata-sandbox.json"
    dev "chmod 0644 /system/etc/sandbox/appdata-sandbox.json"
    dev "chcon u:object_r:system_etc_file:s0 /system/etc/sandbox/appdata-sandbox.json 2>/dev/null || restorecon -F /system/etc/sandbox/appdata-sandbox.json"
fi
[[ "$(device_hash /system/android/lib64/liboh_android_runtime.so)" == "$EXPECTED_ANDROID_RUNTIME" ]] || fail_and_stop "post-reboot liboh_android_runtime.so hash mismatch"
[[ "$(device_hash /system/android/lib64/liboh_adapter_bridge.so)" == "$EXPECTED_BRIDGE" ]] || fail_and_stop "post-reboot liboh_adapter_bridge.so hash mismatch"
if [[ "$P0_MODE" == "1" ]]; then
    [[ "$(device_hash /system/lib64/libskia_canvaskit.z.so)" == "$EXPECTED_SKIA_PROVIDER" ]] ||
        fail_and_stop "post-reboot Skia provider missing or hash mismatch"
    [[ "$(device_hash /system/etc/ld-musl-namespace-aarch64.ini)" == "$EXPECTED_NAMESPACE_MANIFEST" ]] ||
        fail_and_stop "post-reboot namespace manifest hash mismatch"
    [[ "$(device_hash /system/lib64/libwestlake_thread_guard_registry.so)" == "$EXPECTED_THREAD_GUARD" ]] ||
        fail_and_stop "post-reboot libwestlake_thread_guard_registry.so hash mismatch"
fi
if [[ "$EXPECTED_ROUTE_A_PROVIDER" != "SKIPPED" ]]; then
    [[ "$(device_hash /system/android/lib64/libwestlake_android_runtime_provider.so)" == "$EXPECTED_ROUTE_A_PROVIDER" ]] || fail_and_stop "post-reboot Route-A runtime provider hash mismatch"
fi
[[ "$(device_hash /system/android/lib64/libhwui.so)" == "$EXPECTED_HWUI" ]] || fail_and_stop "post-reboot libhwui.so hash mismatch"
[[ "$(device_hash /system/android/lib64/liboh_hwui_shim.so)" == "$EXPECTED_HWUI_SHIM" ]] || fail_and_stop "post-reboot liboh_hwui_shim.so hash mismatch"
[[ "$(device_hash /system/android/lib64/liboh_skia_rtti_shim.so)" == "$EXPECTED_RTTI" ]] || fail_and_stop "post-reboot liboh_skia_rtti_shim.so hash mismatch"
[[ "$(device_hash /system/android/lib64/libandroidfw.so)" == "$EXPECTED_ANDROIDFW" ]] || fail_and_stop "post-reboot libandroidfw.so hash mismatch"
[[ "$(device_hash /system/android/lib64/libminikin.so)" == "$EXPECTED_MINIKIN" ]] || fail_and_stop "post-reboot libminikin.so hash mismatch"
[[ "$(device_hash /system/android/lib64/libprofile.so)" == "$EXPECTED_PROFILE" ]] || fail_and_stop "post-reboot libprofile.so hash mismatch"
[[ "$(device_hash /system/android/lib64/libunwindstack.so)" == "$EXPECTED_UNWINDSTACK" ]] || fail_and_stop "post-reboot libunwindstack.so hash mismatch"
[[ "$(device_hash /system/etc/fonts.xml)" == "$EXPECTED_FONTS" ]] || fail_and_stop "post-reboot fonts.xml hash mismatch"
[[ "$(device_hash /system/android/framework/oh-adapter-framework.jar)" == "$EXPECTED_OH_ADAPTER_FRAMEWORK" ]] || fail_and_stop "post-reboot oh-adapter-framework.jar hash mismatch"
[[ "$(device_hash /system/android/framework/arm64/boot.art)" == "$EXPECTED_BOOT_ART" ]] || fail_and_stop "post-reboot boot.art hash mismatch"
[[ "$(device_hash /system/android/framework/arm64/boot.oat)" == "$EXPECTED_BOOT_OAT" ]] || fail_and_stop "post-reboot boot.oat hash mismatch"
[[ "$(device_hash /system/android/framework/arm64/boot.vdex)" == "$EXPECTED_BOOT_VDEX" ]] || fail_and_stop "post-reboot boot.vdex hash mismatch"
[[ "$(device_hash /system/etc/init/appspawn_x.cfg)" == "$EXPECTED_CFG" ]] || fail_and_stop "post-reboot appspawn_x.cfg hash mismatch"
if [[ "$EXPECTED_SANDBOX_CFG" != "SKIPPED" ]]; then
    [[ "$(device_hash /system/etc/sandbox/appdata-sandbox.json)" == "$EXPECTED_SANDBOX_CFG" ]] || fail_and_stop "post-reboot appdata-sandbox.json hash mismatch"
fi
if [[ "$EXPECTED_ROUTE_A_PLUGIN" != "SKIPPED" ]]; then
    [[ "$(device_hash /system/lib64/appspawn/libwestlake_android_child.z.so)" == "$EXPECTED_ROUTE_A_PLUGIN" ]] || fail_and_stop "post-reboot Route-A child plugin hash mismatch"
fi
if [[ -n "$ROUTE_A_SEALED_DIR" ]]; then
    verify_remote_sealed_tree "/system/lib64/westlake/route-a/$SEALED_GENERATION" "post-reboot"
fi
[[ "$(device_hash /system/lib64/libappms.z.so)" == "$EXPECTED_APPMS" ]] || fail_and_stop "post-reboot libappms.z.so hash mismatch"
[[ "$(device_hash /system/lib64/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]] || fail_and_stop "post-reboot libappspawn_client.z.so hash mismatch"
[[ "$(device_hash /system/lib64/libbms.z.so)" == "$EXPECTED_BMS" ]] || fail_and_stop "post-reboot libbms.z.so hash mismatch"
[[ "$(device_hash /system/lib64/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]] || fail_and_stop "post-reboot libinstalls.z.so hash mismatch"
[[ "$(device_hash /system/lib64/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]] || fail_and_stop "post-reboot libapk_installer.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libappms.z.so)" == "$EXPECTED_APPMS" ]] || fail_and_stop "post-reboot platformsdk libappms.z.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libappspawn_client.z.so)" == "$EXPECTED_CLIENT" ]] || fail_and_stop "post-reboot platformsdk libappspawn_client.z.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libbms.z.so)" == "$EXPECTED_BMS" ]] || fail_and_stop "post-reboot platformsdk libbms.z.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libinstalls.z.so)" == "$EXPECTED_INSTALLS" ]] || fail_and_stop "post-reboot platformsdk libinstalls.z.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libapk_installer.so)" == "$EXPECTED_INSTALLER" ]] || fail_and_stop "post-reboot platformsdk libapk_installer.so hash mismatch"
[[ "$(device_hash /system/lib64/platformsdk/libabilityms.z.so)" == "$EXPECTED_ABILITYMS" ]] || fail_and_stop "post-reboot platformsdk libabilityms.z.so hash mismatch"
[[ "$(device_hash /system/android/lib64/liblzma.so)" == "$EXPECTED_LZMA" ]] || fail_and_stop "post-reboot liblzma.so hash mismatch"
[[ "$(device_hash /system/android/lib64/libshared_libz.z.so)" == "$EXPECTED_SHARED_LIBZ" ]] || fail_and_stop "post-reboot libshared_libz.z.so hash mismatch"

if [[ "$P0_MODE" == "1" ]]; then
    # Publish the identity only after every selected byte has survived reboot
    # and readback.  The first-frame runner consumes these two exact files, so
    # a stale marker can never make a newly deployed generation look old.
    GENERATION_ID_RECEIPT="$EVIDENCE/bridge-current-generation.id"
    GENERATION_READBACK_RECEIPT="$EVIDENCE/bridge-current-generation-readback.json"
    POSTBOOT_ID=$(dev "cat /proc/sys/kernel/random/boot_id" | /usr/bin/tr -d '\r ')
    DEPLOY_MANIFEST_SHA256=$(local_hash "$DEPLOY_MANIFEST")
    EXPECTED_HASHES_SHA256=$(local_hash "$EXPECTED_HASHES_MANIFEST")
    SEALED_MANIFEST_SHA256="SKIPPED"
    if [[ -f "$ROUTE_A_SEALED_MANIFEST" ]]; then
        SEALED_MANIFEST_SHA256=$(local_hash "$ROUTE_A_SEALED_MANIFEST")
    fi
    print -r -- "$P0_GENERATION_ID" >"$GENERATION_ID_RECEIPT"
    /usr/bin/python3 - \
        "$GENERATION_READBACK_RECEIPT" \
        "$TARGET" \
        "$POSTBOOT_ID" \
        "$P0_GENERATION_ID" \
        "$EXPECTED_APK" \
        "$DEPLOY_MANIFEST_SHA256" \
        "$EXPECTED_HASHES_SHA256" \
        "$SEALED_MANIFEST_SHA256" \
        "$EXPECTED_APPSPAWN" \
        "$EXPECTED_ROUTE_A_PLUGIN" \
        "$EXPECTED_ROUTE_A_PROVIDER" \
        "$EXPECTED_ANDROID_RUNTIME" \
        "$EXPECTED_BRIDGE" <<'PY'
import json
import pathlib
import sys

(
    output,
    serial,
    boot_id,
    generation_id,
    apk_sha256,
    deploy_manifest_sha256,
    expected_hashes_sha256,
    sealed_manifest_sha256,
    appspawn_sha256,
    child_plugin_sha256,
    runtime_provider_sha256,
    android_runtime_sha256,
    adapter_bridge_sha256,
) = sys.argv[1:]
receipt = {
    "schema_version": "bridge.p0.device-generation-readback.v1",
    "serial": serial,
    "boot_id": boot_id,
    "generation_id": generation_id,
    "apk_sha256": apk_sha256,
    "deploy_manifest_sha256": deploy_manifest_sha256,
    "expected_hashes_sha256": expected_hashes_sha256,
    "sealed_manifest_sha256": sealed_manifest_sha256,
    "artifacts": {
        "appspawn-x": appspawn_sha256,
        "libwestlake_android_child.z.so": child_plugin_sha256,
        "libwestlake_android_runtime_provider.so": runtime_provider_sha256,
        "liboh_android_runtime.so": android_runtime_sha256,
        "liboh_adapter_bridge.so": adapter_bridge_sha256,
    },
}
pathlib.Path(output).write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY
    "$HDC" -t "$TARGET" file send "$GENERATION_ID_RECEIPT" \
        /data/local/tmp/bridge-current-generation.id \
        >"$EVIDENCE/send-generation-id.txt" 2>&1
    "$HDC" -t "$TARGET" file send "$GENERATION_READBACK_RECEIPT" \
        /data/local/tmp/bridge-current-generation-readback.json \
        >"$EVIDENCE/send-generation-readback.txt" 2>&1
    [[ "$(dev 'cat /data/local/tmp/bridge-current-generation.id' | /usr/bin/tr -d '\r ')" == \
        "$P0_GENERATION_ID" ]] || fail_and_stop "published generation id mismatch"
    [[ "$(device_hash /data/local/tmp/bridge-current-generation-readback.json)" == \
        "$(local_hash "$GENERATION_READBACK_RECEIPT")" ]] ||
        fail_and_stop "published generation readback mismatch"
fi

# --- appspawn-x service verification ---
# The AppSpawnX socket is owned by init in ondemand mode.  Its presence proves
# transport setup only; it must never substitute for a live daemon PID.
print "Verifying stable appspawn-x parent..."
dev "begetctl start_service appspawn-x >/dev/null 2>&1 || true"
# Some D600 init revisions materialize this declared ondemand socket with the
# generic root:root/dev_unix_socket identity after a development deployment.
# Re-apply the exact identity already declared by appspawn_x.cfg before AMS
# connects; foundation is a member of the appspawn group (6005).
for attempt in {1..30}; do
    [[ "$(dev 'test -S /dev/unix/socket/AppSpawnX && echo READY' | /usr/bin/tr -d '\r ')" == \
        "READY" ]] && break
    sleep 1
done
dev "chown root:appspawn /dev/unix/socket/AppSpawnX && chmod 0660 /dev/unix/socket/AppSpawnX && chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX"
SOCKET_DAC=$(dev "stat -c '%a:%u:%g' /dev/unix/socket/AppSpawnX" | /usr/bin/tr -d '\r ')
[[ "$SOCKET_DAC" == "660:0:6005" ]] ||
    fail_and_stop "AppSpawnX socket DAC identity mismatch: $SOCKET_DAC"
dev "ls -lZ /dev/unix/socket/AppSpawnX" | /usr/bin/grep -q \
    'u:object_r:appspawn_socket:s0' ||
    fail_and_stop "AppSpawnX socket SELinux identity mismatch"
APP_SPAWN_PID=""
for attempt in {1..30}; do
    APP_SPAWN_PID=$(dev "pidof appspawn-x" | /usr/bin/tr -d '\r' || true)
    [[ -n "$APP_SPAWN_PID" ]] && break
    sleep 1
done
APP_SPAWN_STATE=FAILED_NO_PARENT
APP_SPAWN_PID_AFTER=""
if [[ -n "$APP_SPAWN_PID" ]]; then
    sleep 5
    APP_SPAWN_PID_AFTER=$(dev "pidof appspawn-x" | /usr/bin/tr -d '\r' || true)
    if [[ "$APP_SPAWN_PID_AFTER" == "$APP_SPAWN_PID" ]] &&
       [[ "$(print -r -- "$APP_SPAWN_PID" | /usr/bin/awk '{print NF}')" == "1" ]]; then
        APP_SPAWN_STATE=RUNNING_STABLE
    else
        APP_SPAWN_STATE=FAILED_UNSTABLE_PARENT
    fi
fi
print "appspawn-x pid=$APP_SPAWN_PID stable_pid=$APP_SPAWN_PID_AFTER state=$APP_SPAWN_STATE"

{
    print "appspawn_x_pid: $APP_SPAWN_PID"
    print "appspawn_x_pid_after_5s: $APP_SPAWN_PID_AFTER"
    print "appspawn_x_state: $APP_SPAWN_STATE"
    dev "pidof appspawn-x || true"
    dev "ls -lZ /system/bin/appspawn-x"
    dev "ls -lZ /system/lib64/appspawn/libwestlake_android_child.z.so 2>/dev/null || true"
    dev "ls -lZ /dev/unix/socket/AppSpawnX 2>/dev/null || true"
    dev "grep AppSpawnX /proc/net/unix 2>/dev/null || true"
    dev "hilog -x | grep -E 'appspawn-x|AppSpawnX|ROUTE-A|MUSL-LDSO' | tail -n 200 || true"
} >"$EVIDENCE/appspawn-x-service.txt"

if [[ "$APP_SPAWN_STATE" != "RUNNING_STABLE" ]]; then
    if [[ "$ALLOW_ONDEMAND_NO_PARENT" == "1" ]] &&
       [[ "$APP_SPAWN_STATE" == "FAILED_NO_PARENT" ]] &&
       [[ "$RUN_APK_SANITY" == "1" ]]; then
        APP_SPAWN_STATE=DEFERRED_UNTIL_APK_TRIGGER
        print "appspawn-x is init-ondemand; deferring live-parent proof until APK trigger"
    else
        fail_and_stop "appspawn-x parent is not a single stable process: initial=$APP_SPAWN_PID after_5s=$APP_SPAWN_PID_AFTER state=$APP_SPAWN_STATE"
    fi
fi

# --- optional APK install and launch verification ---
activity_thread=0
oncreate=0
art_started=0
appspawn_accept=0
app_pid=""
APK_VERDICT=SKIPPED
BLOCKER=""
if [[ "$RUN_APK_SANITY" == "1" ]]; then
    print "Installing sanity APK $APP_REMOTE_NAME..."
    dev "bm install -p $STAGE/$APP_REMOTE_NAME" >"$EVIDENCE/bm-install.txt" 2>&1 || fail_and_stop "bm install failed"

    dev "bm dump -n $APP_PACKAGE" >"$EVIDENCE/bm-dump.txt" 2>&1 || true
    APP_UID=$(/usr/bin/awk '/"uid": [0-9]+/ {
        value=$2
        gsub(/,/, "", value)
        if (value > 0) { print value; exit }
    }' "$EVIDENCE/bm-dump.txt")
    APP_USER_ID=$(/usr/bin/awk '/"userId": [0-9]+/ {
        value=$2
        gsub(/,/, "", value)
        print value
        exit
    }' "$EVIDENCE/bm-dump.txt")
    [[ "$APP_UID" =~ ^[0-9]+$ ]] || fail_and_stop "unable to resolve installed app uid"
    [[ "$APP_USER_ID" =~ ^[0-9]+$ ]] || APP_USER_ID=100
    # The Android APK installer currently creates the bundle payload but not
    # every standard OH app-data mount source on a freshly provisioned board.
    # Create the same per-UID roots that BMS creates for native HAPs so the
    # stock appspawn sandbox does not fail before the Android child hook runs.
    dev "mkdir -p \
      /data/app/el1/$APP_USER_ID/base/$APP_PACKAGE \
      /data/app/el1/$APP_USER_ID/database/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/base/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/database/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/log/$APP_PACKAGE"
    dev "chown -R ${APP_UID}:${APP_UID} \
      /data/app/el1/$APP_USER_ID/base/$APP_PACKAGE \
      /data/app/el1/$APP_USER_ID/database/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/base/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/database/$APP_PACKAGE"
    dev "chmod 0700 \
      /data/app/el1/$APP_USER_ID/base/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/base/$APP_PACKAGE"
    dev "chmod 0770 \
      /data/app/el1/$APP_USER_ID/database/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/database/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/log/$APP_PACKAGE"
    dev "chown ${APP_UID}:log /data/app/el2/$APP_USER_ID/log/$APP_PACKAGE"
    dev "chcon -R u:object_r:appdat:s0 \
      /data/app/el1/$APP_USER_ID/base/$APP_PACKAGE \
      /data/app/el1/$APP_USER_ID/database/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/base/$APP_PACKAGE \
      /data/app/el2/$APP_USER_ID/database/$APP_PACKAGE"
    dev "chcon -R u:object_r:data_app_el2_file:s0 /data/app/el2/$APP_USER_ID/log/$APP_PACKAGE"
    print "Launching sanity APK $APP_PACKAGE..."
    dev "aa force-stop $APP_PACKAGE 2>/dev/null || true"
    dev "hilog -r >/dev/null 2>&1 || true"
    sleep 1
    dev "aa start -a $APP_ACTIVITY -b $APP_PACKAGE" >"$EVIDENCE/aa-start.txt" 2>&1 || true
    sleep 10
    dev "hilog -x" >"$EVIDENCE/hilog.txt" 2>&1 || true

    {
        dev "ps -A -o PID,PPID,UID,NAME,ARGS | grep -E 'appspawn-x|$APP_PACKAGE' || true"
    } >"$EVIDENCE/processes.txt"

    HILOG="$EVIDENCE/hilog.txt"
    activity_thread=$(grep -c "ActivityThread" "$HILOG" 2>/dev/null || true)
    oncreate=$(grep -c "onCreate" "$HILOG" 2>/dev/null || true)
    art_started=$(grep -c "AndroidRuntime" "$HILOG" 2>/dev/null || true)
    appspawn_accept=$(grep -c "AppSpawnX" "$HILOG" 2>/dev/null || true)
    app_pid=$(app_pid_by_bundle "$APP_PACKAGE")
    APP_SPAWN_PID_AFTER=$(dev "pidof appspawn-x" | /usr/bin/tr -d '\r' || true)
    if [[ -n "$APP_SPAWN_PID_AFTER" ]] &&
       print -r -- "$APP_SPAWN_PID_AFTER" | /usr/bin/awk -v parent="$APP_SPAWN_PID" '
           { for (i = 1; i <= NF; i++) if ($i == parent) found = 1 }
           END { exit !found }
       '; then
        APP_SPAWN_STATE=RUNNING_AFTER_APK_TRIGGER
    else
        APP_SPAWN_STATE=FAILED_AFTER_APK_TRIGGER
    fi
    activity_thread=${activity_thread:-0}
    oncreate=${oncreate:-0}
    art_started=${art_started:-0}
    appspawn_accept=${appspawn_accept:-0}

    APK_VERDICT=FAIL
    if [[ -n "$app_pid" ]] && [[ "$activity_thread" -gt 0 ]]; then
        APK_VERDICT=PASS
        BLOCKER=""
    elif [[ -n "$app_pid" ]] && [[ "$activity_thread" -eq 0 ]]; then
        APK_VERDICT=PARTIAL
        BLOCKER="App child process $app_pid found but no ActivityThread logs"
    elif [[ "$activity_thread" -gt 0 ]]; then
        APK_VERDICT=PARTIAL
        BLOCKER="ActivityThread logs observed but app child process not found"
    else
        BLOCKER="App did not enter AOSP-on-OH path: no ActivityThread logs"
    fi
    print "APK verification: package=$APP_PACKAGE pid=$app_pid ActivityThread=$activity_thread onCreate=$oncreate AndroidRuntime=$art_started AppSpawnX=$appspawn_accept appspawn_state=$APP_SPAWN_STATE verdict=$APK_VERDICT"
fi

FINAL_VERDICT="PASS"
if [[ "$RUN_APK_SANITY" == "1" ]] && [[ "$APK_VERDICT" != "PASS" ]]; then
    FINAL_VERDICT="PARTIAL"
fi

{
    print "experiment: fn01-fn03-r18-runtime-deploy"
    print "target: $TARGET"
    print "timestamp: $TS"
    print "device_write: true"
    print "rebooted: true"
    print "cfg_cgroup_false: true"
    print "runtime_generation: $(basename "$SRC")"
    print "appspawn_x_pid: $APP_SPAWN_PID"
    print "appspawn_x_pid_after_5s: $APP_SPAWN_PID_AFTER"
    print "appspawn_x_state: $APP_SPAWN_STATE"
    print "app_package: $APP_PACKAGE"
    print "app_activity: $APP_ACTIVITY"
    print "app_pid: $app_pid"
    print "activity_thread_hits: $activity_thread"
    print "oncreate_hits: $oncreate"
    print "android_runtime_hits: $art_started"
    print "appspawnx_hits: $appspawn_accept"
    print "apk_verdict: $APK_VERDICT"
    print "verdict: $FINAL_VERDICT"
    print "blocker: $BLOCKER"
    print "claim_boundary: RUNTIME_AND_SYSTEM_SERVICE_DEPLOY_AND_APK_LAUNCH"
} >"$EVIDENCE/DEPLOY-VERDICT.yaml"

print "$FINAL_VERDICT: fn01-fn03 r18/merged runtime deployed on $TARGET"
print "Evidence=$EVIDENCE"
