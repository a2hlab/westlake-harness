#!/usr/bin/env bash
set -uo pipefail

# Verify one L03.A12 ARM64 provider generation without loading any artifact.
# The manifest is JSON; artifact paths are relative to ARTIFACT_ROOT.

usage() {
    cat <<'EOF'
Usage: verify_l03_a12_provider_closure.sh MANIFEST.json ARTIFACT_ROOT

Required manifest shape:
{
  "schema": "westlake.l03_a12.provider_closure.v3",
  "generation_id": "...",
  "architecture": "aarch64",
  "payload_complete": true,
  "inputs": {
    "source_before_sha256": "<64 hex>",
    "source_after_sha256": "<same 64 hex>",
    "toolchain_manifest_sha256": "<64 hex>",
    "sysroot_manifest_sha256": "<64 hex>",
    "external_source_manifest_sha256": "<64 hex>",
    "immutable_base_manifest_sha256": "<64 hex>",
    "generated_input_manifest_sha256": "<64 hex>",
    "deploy_plan_sha256": "<64 hex>"
  },
  "build": {
    "strict_link": true,
    "relaxed_link": false,
    "log": "relative/path/from/manifest.json",
    "sha256": "<64 hex>"
  },
  "artifacts": [
    {"role":"backend",       "path":".../libapp_native_loader.so", "sha256":"..."},
    {"role":"bridge",        "path":".../liboh_adapter_bridge.so", "sha256":"..."},
    {"role":"native_loader", "path":".../libnativeloader.so",      "sha256":"..."},
    {"role":"runtime",       "path":".../liboh_android_runtime.so", "sha256":"..."},
    {"role":"profile",       "path":".../libprofile.so",          "sha256":"..."},
    {"role":"unwindstack",   "path":".../libunwindstack.so",      "sha256":"..."},
    {"role":"art",           "path":".../libart.so",              "sha256":"..."},
    {"role":"appspawn",      "path":".../appspawn-x",             "sha256":"..."}
  ]
}

Every regular file under ARTIFACT_ROOT must appear exactly once in artifacts.
Additional payload roles are allowed and are included in the symbol scan.
EOF
}

checks=0
failures=0

ok() {
    checks=$((checks + 1))
    printf 'PROVIDER_CLOSURE_OK code=%s detail=%s\n' "$1" "$2"
}

fail() {
    checks=$((checks + 1))
    failures=$((failures + 1))
    printf 'PROVIDER_CLOSURE_FAIL code=%s detail=%s\n' "$1" "$2" >&2
}

finish() {
    printf 'PROVIDER_CLOSURE_SUMMARY checks=%d failures=%d\n' "$checks" "$failures"
    if [ "$failures" -eq 0 ]; then
        printf 'PROVIDER_SUBGRAPH_PASS generation=%s\n' "${generation_id:-unknown}"
        return 0
    fi
    printf 'PROVIDER_CLOSURE_REJECT generation=%s\n' "${generation_id:-unknown}" >&2
    return 1
}

if [ "$#" -ne 2 ]; then
    usage >&2
    exit 2
fi

manifest=$1
artifact_root=$2

if [ ! -e "$manifest" ]; then
    fail manifest_missing "path=$manifest"
    finish
    exit $?
fi
if [ ! -f "$manifest" ] || [ -L "$manifest" ]; then
    fail manifest_not_regular "path=$manifest"
    finish
    exit $?
fi
if [ ! -d "$artifact_root" ] || [ -L "$artifact_root" ]; then
    fail artifact_root_invalid "path=$artifact_root"
    finish
    exit $?
fi

PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    printf 'provider closure gate: python3 is required\n' >&2
    exit 2
fi

READELF=${READELF:-${OH_READELF:-}}
if [ -z "$READELF" ]; then
    sdk_readelf=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf
    if [ -x "$sdk_readelf" ]; then
        READELF=$sdk_readelf
    elif command -v llvm-readelf >/dev/null 2>&1; then
        READELF=$(command -v llvm-readelf)
    elif command -v readelf >/dev/null 2>&1; then
        READELF=$(command -v readelf)
    else
        printf 'provider closure gate: llvm-readelf/readelf is required\n' >&2
        exit 2
    fi
fi
if [ ! -x "$READELF" ]; then
    printf 'provider closure gate: READELF is not executable: %s\n' "$READELF" >&2
    exit 2
fi

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        return 127
    fi
}

if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
    printf 'provider closure gate: sha256sum or shasum is required\n' >&2
    exit 2
fi

tmp_parent=${TMPDIR:-/tmp}
tmp=$(mktemp -d "$tmp_parent/l03a12-provider-closure.XXXXXX") || exit 2
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

manifest_start_sha=$(sha256_file "$manifest") || {
    printf 'provider closure gate: failed to hash manifest\n' >&2
    exit 2
}

normalized=$tmp/manifest.tsv
"$PYTHON" - "$manifest" "$artifact_root" >"$normalized" <<'PY'
import json
import os
import re
import stat
import sys
from pathlib import PurePosixPath

manifest_path = os.path.abspath(sys.argv[1])
artifact_root = os.path.abspath(sys.argv[2])
manifest_dir = os.path.realpath(os.path.dirname(manifest_path))
errors = []

def clean(value):
    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")

def error(code, detail):
    errors.append((code, clean(detail)))

def is_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None

def safe_rel(value):
    if not isinstance(value, str) or not value or "\\" in value or "\t" in value or "\n" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in ("", ".", "..") for part in path.parts)

def path_has_symlink(base, relative):
    current = base
    for part in PurePosixPath(relative).parts:
        current = os.path.join(current, part)
        if os.path.islink(current):
            return True
    return False

try:
    with open(manifest_path, "r", encoding="utf-8") as stream:
        data = json.load(stream)
except Exception as exc:
    error("manifest_parse", exc)
    data = None

records = []
if isinstance(data, dict):
    if data.get("schema") != "westlake.l03_a12.provider_closure.v3":
        error("manifest_schema", data.get("schema"))

    generation = data.get("generation_id")
    if not isinstance(generation, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", generation) is None:
        error("generation_id", generation)

    if data.get("architecture") != "aarch64":
        error("manifest_architecture", data.get("architecture"))
    if data.get("payload_complete") is not True:
        error("payload_complete", data.get("payload_complete"))

    inputs = data.get("inputs")
    input_keys = (
        "source_before_sha256",
        "source_after_sha256",
        "toolchain_manifest_sha256",
        "sysroot_manifest_sha256",
        "external_source_manifest_sha256",
        "immutable_base_manifest_sha256",
        "generated_input_manifest_sha256",
        "deploy_plan_sha256",
    )
    if not isinstance(inputs, dict):
        error("inputs_missing", type(inputs).__name__)
        inputs = {}
    for key in input_keys:
        if not is_sha(inputs.get(key)):
            error("input_digest", key)
    if is_sha(inputs.get("source_before_sha256")) and is_sha(inputs.get("source_after_sha256")):
        if inputs["source_before_sha256"] != inputs["source_after_sha256"]:
            error("source_manifest_mismatch", "before!=after")

    provenance_specs = {
        "source_manifest": ("inputs/source.sha256", "source_after_sha256"),
        "toolchain_manifest": ("inputs/toolchain.sha256", "toolchain_manifest_sha256"),
        "sysroot_manifest": ("inputs/sysroot.sha256", "sysroot_manifest_sha256"),
        "external_source_manifest": (
            "inputs/external-source.sha256",
            "external_source_manifest_sha256",
        ),
        "immutable_base_manifest": (
            "inputs/immutable-base.sha256",
            "immutable_base_manifest_sha256",
        ),
        "generated_input_manifest": (
            "generated-inputs.sha256",
            "generated_input_manifest_sha256",
        ),
        "deploy_plan": ("inputs/deploy-plan.json", "deploy_plan_sha256"),
    }
    provenance = data.get("provenance_files")
    provenance_records = []
    if not isinstance(provenance, dict):
        error("provenance_files", type(provenance).__name__)
        provenance = {}
    if set(provenance) != set(provenance_specs):
        error(
            "provenance_keys",
            f"missing={sorted(set(provenance_specs) - set(provenance))} "
            f"extra={sorted(set(provenance) - set(provenance_specs))}",
        )
    for name, (expected_path, input_key) in provenance_specs.items():
        item = provenance.get(name)
        if not isinstance(item, dict):
            error("provenance_record", name)
            continue
        relative = item.get("path")
        digest = item.get("sha256")
        if relative != expected_path or not safe_rel(relative):
            error("provenance_path", f"name={name} path={relative}")
            continue
        if not is_sha(digest):
            error("provenance_digest", name)
            continue
        if digest != inputs.get(input_key):
            error(
                "provenance_input_mismatch",
                f"name={name} input={input_key}",
            )
        absolute = os.path.join(manifest_dir, *PurePosixPath(relative).parts)
        if path_has_symlink(manifest_dir, relative):
            error("provenance_symlink", f"name={name} path={relative}")
        elif os.path.commonpath((manifest_dir, os.path.realpath(absolute))) != manifest_dir:
            error("provenance_outside", f"name={name} path={relative}")
        elif not os.path.isfile(absolute):
            error("provenance_missing", f"name={name} path={relative}")
        else:
            provenance_records.append((name, relative, digest, absolute))

    build = data.get("build")
    if not isinstance(build, dict):
        error("build_manifest", type(build).__name__)
        build = {}
    if build.get("strict_link") is not True:
        error("strict_link_flag", build.get("strict_link"))
    if build.get("relaxed_link") is not False:
        error("relaxed_link_flag", build.get("relaxed_link"))
    log_rel = build.get("log")
    log_sha = build.get("sha256")
    if not safe_rel(log_rel):
        error("build_log_path", log_rel)
    if not is_sha(log_sha):
        error("build_log_digest", log_sha)
    if safe_rel(log_rel):
        log_abs = os.path.join(manifest_dir, *PurePosixPath(log_rel).parts)
        if path_has_symlink(manifest_dir, log_rel):
            error("build_log_symlink", log_rel)
        elif os.path.commonpath((manifest_dir, os.path.realpath(log_abs))) != manifest_dir:
            error("build_log_outside", log_rel)
        elif not os.path.isfile(log_abs):
            error("build_log_missing", log_rel)
        else:
            records.append(("BUILD", log_rel, log_sha, log_abs))

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        error("artifacts_missing", type(artifacts).__name__)
        artifacts = []

    required = {
        "backend": "libapp_native_loader.so",
        "bridge": "liboh_adapter_bridge.so",
        "native_loader": "libnativeloader.so",
        "runtime": "liboh_android_runtime.so",
        "profile": "libprofile.so",
        "unwindstack": "libunwindstack.so",
        "art": "libart.so",
        "appspawn": "appspawn-x",
    }
    seen_roles = {}
    seen_paths = {}
    expected_paths = set()
    artifact_records = []

    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            error("artifact_record", index)
            continue
        role = item.get("role")
        path = item.get("path")
        digest = item.get("sha256")
        if not isinstance(role, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", role) is None:
            error("artifact_role", role)
            continue
        if role in seen_roles:
            error("duplicate_role", role)
        seen_roles[role] = index
        if path == "aosp/libart_runtime_stubs.so" or role == "runtime_stubs":
            error("forbidden_broad_runtime_stub", path)
        if not safe_rel(path):
            error("artifact_path", path)
            continue
        if path in seen_paths:
            error("duplicate_path", path)
        seen_paths[path] = index
        if not is_sha(digest):
            error("artifact_digest", path)
        if role in required and PurePosixPath(path).name != required[role]:
            error("role_basename", f"{role}:{path}")
        expected_paths.add(path)
        artifact_records.append((role, path, digest))

    for role in sorted(required):
        if role not in seen_roles:
            error("required_role", role)

    actual_paths = set()
    for directory, dirs, files in os.walk(artifact_root, followlinks=False):
        for name in list(dirs):
            absolute = os.path.join(directory, name)
            relative = os.path.relpath(absolute, artifact_root).replace(os.sep, "/")
            if os.path.islink(absolute):
                error("artifact_symlink", relative)
                dirs.remove(name)
        for name in files:
            absolute = os.path.join(directory, name)
            relative = os.path.relpath(absolute, artifact_root).replace(os.sep, "/")
            try:
                mode = os.lstat(absolute).st_mode
            except OSError as exc:
                error("artifact_stat", f"{relative}:{exc}")
                continue
            if stat.S_ISLNK(mode):
                error("artifact_symlink", relative)
            elif stat.S_ISREG(mode):
                actual_paths.add(relative)
            else:
                error("artifact_not_regular", relative)

    for path in sorted(expected_paths - actual_paths):
        error("artifact_missing", path)
    for path in sorted(actual_paths - expected_paths):
        error("stale_extra", path)

    if not errors:
        records.insert(0, ("META", generation, "", ""))
        for name, path, digest, absolute in provenance_records:
            records.append(("PROV", name, digest, absolute))
        for role, path, digest in artifact_records:
            records.append(("ART", role, path, digest))
elif data is not None:
    error("manifest_root", type(data).__name__)

if errors:
    for code, detail in errors:
        print("ERROR", code, detail, "", sep="\t")
else:
    for record in records:
        print(*record, sep="\t")
PY
manifest_parser_rc=$?
if [ "$manifest_parser_rc" -ne 0 ]; then
    fail manifest_parser_runtime "rc=$manifest_parser_rc"
    finish
    exit $?
fi

generation_id=
build_log=
build_log_sha=
artifact_count=0
provenance_count=0
roles=()
paths=()
digests=()
provenance_names=()
provenance_paths=()
provenance_digests=()

while IFS=$'\t' read -r kind a b c; do
    case "$kind" in
        ERROR) fail "$a" "$b" ;;
        META) generation_id=$a ;;
        BUILD) build_log=$c; build_log_sha=$b ;;
        PROV)
            provenance_names[$provenance_count]=$a
            provenance_digests[$provenance_count]=$b
            provenance_paths[$provenance_count]=$c
            provenance_count=$((provenance_count + 1))
            ;;
        ART)
            roles[$artifact_count]=$a
            paths[$artifact_count]=$b
            digests[$artifact_count]=$c
            artifact_count=$((artifact_count + 1))
            ;;
    esac
done <"$normalized"

if [ "$failures" -ne 0 ]; then
    finish
    exit $?
fi

ok manifest_valid "generation=$generation_id artifacts=$artifact_count provenance=$provenance_count"

actual_log_sha=$(sha256_file "$build_log") || {
    printf 'provider closure gate: failed to hash build log\n' >&2
    exit 2
}
if [ "$actual_log_sha" = "$build_log_sha" ]; then
    ok build_log_hash "sha256=$actual_log_sha"
else
    fail build_log_hash "expected=$build_log_sha actual=$actual_log_sha"
fi

for ((i = 0; i < provenance_count; i++)); do
    actual_provenance_sha=$(sha256_file "${provenance_paths[$i]}") || {
        fail provenance_hash "name=${provenance_names[$i]} unreadable"
        continue
    }
    if [ "$actual_provenance_sha" = "${provenance_digests[$i]}" ]; then
        ok provenance_hash "name=${provenance_names[$i]} sha256=$actual_provenance_sha"
    else
        fail provenance_hash "name=${provenance_names[$i]} expected=${provenance_digests[$i]} actual=$actual_provenance_sha"
    fi
done

if grep -Eiq '\[link:[[:space:]]*relaxed\]|--unresolved-symbols=ignore-all|--allow-shlib-undefined|relaxed_link[[:space:]=:]+true|strict_link[[:space:]=:]+false' "$build_log"; then
    fail relaxed_marker "log=$build_log"
else
    ok relaxed_marker_absent "log=$build_log"
fi

deploy_gate=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verify_l03_a12_deploy_closure.py
if ! "$PYTHON" "$deploy_gate" "$manifest" "$artifact_root" --readelf "$READELF"; then
    exit 1
fi

role_index() {
    local wanted=$1
    local i
    for ((i = 0; i < artifact_count; i++)); do
        if [ "${roles[$i]}" = "$wanted" ]; then
            printf '%s\n' "$i"
            return 0
        fi
    done
    return 1
}

expected_soname() {
    case "$1" in
        backend) printf '%s\n' libapp_native_loader.so ;;
        bridge) printf '%s\n' liboh_adapter_bridge.so ;;
        native_loader) printf '%s\n' libnativeloader.so ;;
        runtime) printf '%s\n' liboh_android_runtime.so ;;
        profile) printf '%s\n' libprofile.so ;;
        unwindstack) printf '%s\n' libunwindstack.so ;;
        art) printf '%s\n' libart.so ;;
        *) return 1 ;;
    esac
}

symbol_records=$tmp/symbols.tsv
: >"$symbol_records"

for ((i = 0; i < artifact_count; i++)); do
    rel=${paths[$i]}
    role=${roles[$i]}
    abs=$artifact_root/$rel
    expected_sha=${digests[$i]}
    if [ ! -f "$abs" ] || [ -L "$abs" ]; then
        fail artifact_replaced "role=$role path=$rel"
        continue
    fi
    actual_sha=$(sha256_file "$abs") || {
        printf 'provider closure gate: failed to hash artifact: %s\n' "$rel" >&2
        exit 2
    }
    if [ "$actual_sha" = "$expected_sha" ]; then
        ok artifact_hash "role=$role path=$rel sha256=$actual_sha"
    else
        fail hash_mismatch "role=$role path=$rel expected=$expected_sha actual=$actual_sha"
    fi

    header=$tmp/elf.$i.header
    dynamic=$tmp/elf.$i.dynamic
    dynsym=$tmp/elf.$i.dynsym
    relocs=$tmp/elf.$i.relocs
    notes=$tmp/elf.$i.notes

    if ! "$READELF" -h --wide "$abs" >"$header" 2>&1; then
        fail elf_header "role=$role path=$rel"
        : >"$dynamic"; : >"$dynsym"; : >"$relocs"; : >"$notes"
        continue
    fi

    if grep -Eq 'Class:[[:space:]]+ELF64' "$header"; then
        ok elf_class "role=$role path=$rel"
    else
        fail wrong_class "role=$role path=$rel"
    fi
    if grep -Eq 'Machine:[[:space:]]+AArch64' "$header"; then
        ok elf_machine "role=$role path=$rel"
    else
        fail wrong_machine "role=$role path=$rel"
    fi
    if [ "$role" = appspawn ]; then
        if grep -Eq 'Type:[[:space:]]+(DYN|EXEC)' "$header"; then
            ok elf_type "role=$role path=$rel"
        else
            fail elf_type "role=$role path=$rel expected=DYN_or_EXEC"
        fi
    elif grep -Eq 'Type:[[:space:]]+DYN' "$header"; then
        ok elf_type "role=$role path=$rel"
    else
        fail elf_type "role=$role path=$rel expected=DYN"
    fi

    "$READELF" -d --wide "$abs" >"$dynamic" 2>&1 || :
    "$READELF" --dyn-syms --wide "$abs" >"$dynsym" 2>&1 || :
    "$READELF" -r --wide "$abs" >"$relocs" 2>&1 || :
    "$READELF" -n --wide "$abs" >"$notes" 2>&1 || :

    if grep -Eq 'Build ID:[[:space:]]*[0-9a-fA-F]+' "$notes"; then
        ok build_id "role=$role path=$rel"
    else
        fail build_id "role=$role path=$rel"
    fi
    if grep -Eq '\((RPATH|RUNPATH|TEXTREL)\)' "$dynamic"; then
        fail unsafe_dynamic_tag "role=$role path=$rel"
    else
        ok unsafe_dynamic_tag_absent "role=$role path=$rel"
    fi

    if soname=$(expected_soname "$role"); then
        soname_count=$(awk -F'[][]' -v wanted="$soname" '/Library soname:/ && $2 == wanted {count++} END {print count + 0}' "$dynamic")
        if [ "$soname_count" -eq 1 ]; then
            ok soname "role=$role soname=$soname"
        else
            fail soname "role=$role expected=$soname count=$soname_count"
        fi
    fi

    awk -v artifact="$rel" '
        $1 ~ /^[0-9]+:$/ && NF >= 8 {
            name = $8
            sub(/@.*/, "", name)
            printf "%s\t%s\t%s\t%s\t%s\t%s\n", artifact, $4, $5, $6, $7, name
        }
    ' "$dynsym" >>"$symbol_records"
done

needed_count() {
    local index=$1
    local soname=$2
    awk -F'[][]' -v wanted="$soname" '/Shared library:/ && $2 == wanted {count++} END {print count + 0}' "$tmp/elf.$index.dynamic"
}

require_needed() {
    local role=$1
    local soname=$2
    local index count
    index=$(role_index "$role") || return 1
    count=$(needed_count "$index" "$soname")
    if [ "$count" -eq 1 ]; then
        ok direct_needed "role=$role soname=$soname"
    else
        fail direct_needed "role=$role soname=$soname count=$count"
    fi
}

dynsym_und_count() {
    local index=$1
    local symbol=$2
    awk -v wanted="$symbol" '
        $1 ~ /^[0-9]+:$/ && NF >= 8 {
            name = $8
            sub(/@.*/, "", name)
            if (name == wanted && $4 == "FUNC" && $5 == "GLOBAL" && $6 == "DEFAULT" && $7 == "UND") count++
        }
        END {print count + 0}
    ' "$tmp/elf.$index.dynsym"
}

relocation_count() {
    local index=$1
    local symbol=$2
    awk -v wanted="$symbol" '
        {
            for (field = 1; field <= NF; field++) {
                name = $field
                sub(/@.*/, "", name)
                if (name == wanted) count++
            }
        }
        END {print count + 0}
    ' "$tmp/elf.$index.relocs"
}

require_und_relocation() {
    local role=$1
    local symbol=$2
    local index und reloc
    index=$(role_index "$role") || return 1
    und=$(dynsym_und_count "$index" "$symbol")
    reloc=$(relocation_count "$index" "$symbol")
    if [ "$und" -eq 1 ]; then
        ok symbol_und "role=$role symbol=$symbol"
    else
        fail symbol_und "role=$role symbol=$symbol count=$und"
    fi
    if [ "$reloc" -eq 1 ]; then
        ok symbol_relocation "role=$role symbol=$symbol"
    else
        fail symbol_relocation "role=$role symbol=$symbol count=$reloc"
    fi
}

require_needed native_loader libapp_native_loader.so
require_needed runtime libnativeloader.so
require_needed art libnativeloader.so

ANL_SYMBOLS=(
    ANL_CreateDomain
    ANL_Dlopen
    ANL_Dlclose
    ANL_Dlerror
    ANL_ReleaseDomainHandle
)
for symbol in "${ANL_SYMBOLS[@]}"; do
    require_und_relocation native_loader "$symbol"
done

PROFILE_B_SYMBOLS=(
    OpenNativeLibrary
    CloseNativeLibrary
    NativeLoaderFreeErrorMessage
    InitializeNativeLoader
    ResetNativeLoader
    CreateClassLoaderNamespace
)

ART_CONSUMERS=(
    OpenNativeLibrary
    CloseNativeLibrary
    NativeLoaderFreeErrorMessage
    InitializeNativeLoader
    ResetNativeLoader
)

CREATE_SYMBOL=CreateClassLoaderNamespace
require_und_relocation runtime "$CREATE_SYMBOL"
for symbol in "${ART_CONSUMERS[@]}"; do
    require_und_relocation art "$symbol"
done

native_loader_index=$(role_index native_loader)
native_loader_path=${paths[$native_loader_index]}
backend_index=$(role_index backend)
backend_path=${paths[$backend_index]}

for symbol in "${PROFILE_B_SYMBOLS[@]}"; do
    total_defs=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $5 != "UND" {count++} END {print count + 0}' "$symbol_records")
    strong_defs=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $2 == "FUNC" && $3 == "GLOBAL" && $4 == "DEFAULT" && $5 != "UND" {count++} END {print count + 0}' "$symbol_records")
    weak_rows=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $3 == "WEAK" && $5 != "UND" {count++} END {print count + 0}' "$symbol_records")
    owners=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $5 != "UND" {print $1}' "$symbol_records")

    if [ "$total_defs" -eq 1 ] && [ "$strong_defs" -eq 1 ]; then
        ok provider_cardinality "symbol=$symbol defs=1 strong=1"
    else
        fail provider_cardinality "symbol=$symbol defs=$total_defs strong=$strong_defs"
    fi
    if [ "$owners" = "$native_loader_path" ]; then
        ok provider_owner "symbol=$symbol path=$owners"
    else
        fail provider_owner "symbol=$symbol expected=$native_loader_path actual=${owners:-none}"
    fi
    if [ "$weak_rows" -eq 0 ]; then
        ok weak_native_loader_symbol_absent "symbol=$symbol"
    else
        fail weak_native_loader_symbol "symbol=$symbol rows=$weak_rows"
    fi
done

for symbol in "${ANL_SYMBOLS[@]}"; do
    total_defs=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $5 != "UND" {count++} END {print count + 0}' "$symbol_records")
    strong_defs=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $2 == "FUNC" && $3 == "GLOBAL" && $4 == "DEFAULT" && $5 != "UND" {count++} END {print count + 0}' "$symbol_records")
    owners=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $5 != "UND" {print $1}' "$symbol_records")
    if [ "$total_defs" -eq 1 ] && [ "$strong_defs" -eq 1 ] && [ "$owners" = "$backend_path" ]; then
        ok backend_provider "symbol=$symbol path=$owners"
    else
        fail backend_provider "symbol=$symbol defs=$total_defs strong=$strong_defs expected=$backend_path actual=${owners:-none}"
    fi
done

LEGACY_SYMBOLS=(
    _ZN7android17OpenNativeLibraryEP7_JNIEnviPKcP8_jobjectS3_P8_jstringPbPPc
    _ZN7android18CloseNativeLibraryEPvbPPc
    _ZN7android28NativeLoaderFreeErrorMessageEPc
    _ZN7android22InitializeNativeLoaderEv
    _ZN7android17ResetNativeLoaderEv
    _ZN7android26CreateClassLoaderNamespaceEP7_JNIEnviP8_jobjectbP8_jstringS5_S5_S5_
    FindNativeLoaderNamespaceByClassLoader
    FindSymbolInNativeLoaderNamespace
)

for symbol in "${LEGACY_SYMBOLS[@]}"; do
    definitions=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $5 != "UND" {count++} END {print count + 0}' "$symbol_records")
    weak_rows=$(awk -F'\t' -v wanted="$symbol" '$6 == wanted && $3 == "WEAK" && $5 != "UND" {count++} END {print count + 0}' "$symbol_records")
    if [ "$definitions" -eq 0 ]; then
        ok legacy_provider_absent "symbol=$symbol"
    else
        fail legacy_provider "symbol=$symbol definitions=$definitions"
    fi
    if [ "$weak_rows" -eq 0 ]; then
        ok weak_native_loader_symbol_absent "symbol=$symbol"
    else
        fail weak_native_loader_symbol "symbol=$symbol rows=$weak_rows"
    fi
done

manifest_end_sha=$(sha256_file "$manifest") || manifest_end_sha=unreadable
if [ "$manifest_end_sha" = "$manifest_start_sha" ]; then
    ok manifest_stable "sha256=$manifest_end_sha"
else
    fail manifest_changed "before=$manifest_start_sha after=$manifest_end_sha"
fi

log_end_sha=$(sha256_file "$build_log") || log_end_sha=unreadable
if [ "$log_end_sha" = "$build_log_sha" ]; then
    ok build_log_stable "sha256=$log_end_sha"
else
    fail build_log_changed "expected=$build_log_sha actual=$log_end_sha"
fi

for ((i = 0; i < provenance_count; i++)); do
    end_sha=$(sha256_file "${provenance_paths[$i]}") || end_sha=unreadable
    if [ "$end_sha" = "${provenance_digests[$i]}" ]; then
        ok provenance_stable "name=${provenance_names[$i]} sha256=$end_sha"
    else
        fail provenance_changed "name=${provenance_names[$i]} expected=${provenance_digests[$i]} actual=$end_sha"
    fi
done

for ((i = 0; i < artifact_count; i++)); do
    rel=${paths[$i]}
    role=${roles[$i]}
    expected_sha=${digests[$i]}
    end_sha=$(sha256_file "$artifact_root/$rel") || end_sha=unreadable
    if [ "$end_sha" = "$expected_sha" ]; then
        ok artifact_stable "role=$role path=$rel sha256=$end_sha"
    else
        fail artifact_changed "role=$role path=$rel expected=$expected_sha actual=$end_sha"
    fi
done

finish
