#!/usr/bin/env bash
#
# Verify and optionally apply the exact OpenHarmony overlay used by the
# hw248 -> D600 Fn01 no-native APK development observation.

set -euo pipefail

usage()
{
    cat <<'EOF'
Usage:
  src/tools/remote/prepare_fn01_r6_legacy_source.sh \
    --repo-root PATH --oh-root PATH --receipt-dir FRESH_PATH [--execute]

Without --execute, validates every adapter source/patch hash and reports whether
each OpenHarmony patch would apply or is already applied. With --execute, applies
only patches that cleanly forward-apply. A conflict is always fatal.
EOF
}

REPO_ROOT=""
OH_ROOT=""
RECEIPT_DIR=""
EXECUTE=0

while (($#)); do
    case "$1" in
        --repo-root) REPO_ROOT="$2"; shift 2 ;;
        --oh-root) OH_ROOT="$2"; shift 2 ;;
        --receipt-dir) RECEIPT_DIR="$2"; shift 2 ;;
        --execute) EXECUTE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

for directory in "$REPO_ROOT" "$OH_ROOT"; do
    [[ "$directory" == /* && -d "$directory" ]] || {
        echo "ERROR: expected existing absolute directory: $directory" >&2
        exit 2
    }
done
[[ "$RECEIPT_DIR" == /* && ! -e "$RECEIPT_DIR" ]] || {
    echo "ERROR: --receipt-dir must be a fresh absolute path" >&2
    exit 2
}

PROFILE_DIR="$REPO_ROOT/src/atoms/Fn01/A01/hw248-r6-legacy"
SOURCE_LOCK="$PROFILE_DIR/adapter-source.sha256"
PATCH_LOCK="$PROFILE_DIR/oh-patches.tsv"
EXPECTED_BUNDLE_COMMIT="ef924ea4198befa65a088863d9812b7f872e4bbc"
BUNDLE_ROOT="$OH_ROOT/foundation/bundlemanager/bundle_framework"
[[ -f "$SOURCE_LOCK" && -f "$PATCH_LOCK" ]] || {
    echo "ERROR: profile lock files are missing: $PROFILE_DIR" >&2
    exit 2
}

mkdir -p "$RECEIPT_DIR"
(
    cd "$REPO_ROOT"
    sha256sum -c "$SOURCE_LOCK"
) | tee "$RECEIPT_DIR/adapter-source-check.txt"

git -C "$REPO_ROOT" rev-parse HEAD >"$RECEIPT_DIR/repository-head.txt"
git -C "$BUNDLE_ROOT" rev-parse HEAD >"$RECEIPT_DIR/bundle-framework-head.txt"
ACTUAL_BUNDLE_COMMIT="$(cat "$RECEIPT_DIR/bundle-framework-head.txt")"
[[ "$ACTUAL_BUNDLE_COMMIT" == "$EXPECTED_BUNDLE_COMMIT" ]] || {
    echo "ERROR: bundle-framework commit mismatch: expected=$EXPECTED_BUNDLE_COMMIT actual=$ACTUAL_BUNDLE_COMMIT" >&2
    exit 1
}
uname -a >"$RECEIPT_DIR/uname.txt"
git --version >"$RECEIPT_DIR/git-version.txt"
python3 --version >"$RECEIPT_DIR/python-version.txt" 2>&1

printf 'execute=%s\n' "$EXECUTE" >"$RECEIPT_DIR/inputs.env"
printf 'repo_root=%s\n' "$REPO_ROOT" >>"$RECEIPT_DIR/inputs.env"
printf 'oh_root=%s\n' "$OH_ROOT" >>"$RECEIPT_DIR/inputs.env"

: >"$RECEIPT_DIR/allowed-bundle-paths.txt"
patch_index=0
while IFS=$'\t' read -r expected_sha patch_path target_path; do
    [[ -n "$expected_sha" && "${expected_sha:0:1}" != "#" ]] || continue
    patch_index=$((patch_index + 1))
    patch_file="$REPO_ROOT/$patch_path"
    target_file="$OH_ROOT/$target_path"
    bundle_relative="${target_path#foundation/bundlemanager/bundle_framework/}"
    [[ "$bundle_relative" != "$target_path" ]] || {
        echo "ERROR: patch target escapes bundle-framework closure: $target_path" >&2
        exit 1
    }
    printf '%s\n' "$bundle_relative" \
        >>"$RECEIPT_DIR/allowed-bundle-paths.txt"
    receipt_stem="$(printf '%02d-%s' "$patch_index" "$target_path" | tr '/.' '__')"
    [[ -f "$patch_file" && -f "$target_file" ]] || {
        echo "ERROR: patch input/target missing: $patch_path -> $target_path" >&2
        exit 1
    }
    actual_sha="$(sha256sum "$patch_file" | awk '{print $1}')"
    [[ "$actual_sha" == "$expected_sha" ]] || {
        echo "ERROR: patch hash mismatch: $patch_path" >&2
        exit 1
    }

    # One historical patch has stale unified-diff hunk counts even though its
    # preimage/postimage is intact. `git apply --recount` deliberately
    # reconstructs those counts from the patch body; ordinary `patch` rejects
    # that file as malformed before checking the source preimage.
    if git -C "$OH_ROOT" apply --check --recount "$patch_file" \
        >"$RECEIPT_DIR/$receipt_stem.forward.txt" 2>&1; then
        state="WOULD_APPLY"
        if [[ "$EXECUTE" -eq 1 ]]; then
            git -C "$OH_ROOT" apply --recount "$patch_file" \
                >>"$RECEIPT_DIR/$receipt_stem.forward.txt" 2>&1
            state="APPLIED"
        fi
    elif git -C "$OH_ROOT" apply --reverse --check --recount "$patch_file" \
        >"$RECEIPT_DIR/$receipt_stem.reverse.txt" 2>&1; then
        state="ALREADY_APPLIED"
    else
        echo "ERROR: patch is neither cleanly applicable nor already applied: $patch_path" >&2
        exit 1
    fi
    printf '%s\t%s\t%s\n' "$state" "$patch_path" "$target_path" \
        | tee -a "$RECEIPT_DIR/patch-status.tsv"
done <"$PATCH_LOCK"
sort -u -o "$RECEIPT_DIR/allowed-bundle-paths.txt" \
    "$RECEIPT_DIR/allowed-bundle-paths.txt"

grep -Fq 'OH_ADAPTER_ANDROID' \
    "$OH_ROOT/foundation/bundlemanager/bundle_framework/common/BUILD.gn" || {
    [[ "$EXECUTE" -eq 0 ]] || {
        echo "ERROR: common BUILD.gn lacks OH_ADAPTER_ANDROID after apply" >&2
        exit 1
    }
}
grep -Fq 'OH_ADAPTER_ANDROID' \
    "$OH_ROOT/foundation/bundlemanager/bundle_framework/services/bundlemgr/BUILD.gn" || {
    [[ "$EXECUTE" -eq 0 ]] || {
        echo "ERROR: bundlemgr BUILD.gn lacks OH_ADAPTER_ANDROID after apply" >&2
        exit 1
    }
}

git -C "$BUNDLE_ROOT" status --porcelain=v1 --untracked-files=all \
    >"$RECEIPT_DIR/bundle-framework-status.txt"
while IFS= read -r status_line; do
    [[ -n "$status_line" ]] || continue
    changed_path="${status_line:3}"
    case "$changed_path" in
        *" -> "*) changed_path="${changed_path##* -> }" ;;
    esac
    grep -Fxq "$changed_path" "$RECEIPT_DIR/allowed-bundle-paths.txt" || {
        echo "ERROR: unexpected bundle-framework drift outside frozen patch closure: $status_line" >&2
        exit 1
    }
done <"$RECEIPT_DIR/bundle-framework-status.txt"

: >"$RECEIPT_DIR/frozen-targets.sha256"
while IFS=$'\t' read -r expected_sha patch_path target_path; do
    [[ -n "$expected_sha" && "${expected_sha:0:1}" != "#" ]] || continue
    sha256sum "$OH_ROOT/$target_path" \
        >>"$RECEIPT_DIR/frozen-targets.sha256"
done <"$PATCH_LOCK"
(
    cd "$RECEIPT_DIR"
    find . -maxdepth 1 -type f ! -name SHA256SUMS -print0 \
        | sort -z | xargs -0 sha256sum >SHA256SUMS
)

echo "FN01_R6_LEGACY_SOURCE_PREPARE=PASS"
echo "EXECUTE=$EXECUTE"
echo "RECEIPT=$RECEIPT_DIR"
