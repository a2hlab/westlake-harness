#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../../../.." && pwd)
REFERENCE="$PROJECT_ROOT/adapter/frozen/references/aosp-libziparchive-error"
WORK="$SCRIPT_DIR/.work/error-code-string-regression"
IMAGE=sha256:76236bc11d9359a260c3e715cfee437bed387f76ff86c9ac086c1a52c3536797
CXX=${CXX:-c++}

case "$WORK/" in
    "$PROJECT_ROOT/"*) ;;
    *) echo "FAIL work root escaped project" >&2; exit 2 ;;
esac
if [ -L "$SCRIPT_DIR/.work" ]; then
    echo "FAIL symlinked work root" >&2
    exit 2
fi
mkdir -p "$WORK/host/tmp" "$WORK/target"
export TMPDIR="$WORK/host/tmp"
export PYTHONDONTWRITEBYTECODE=1

"$CXX" -std=c++17 -Wall -Wextra -Werror \
    -I"$SCRIPT_DIR/include" -I"$REFERENCE" \
    "$REFERENCE/zip_error.cpp" "$SCRIPT_DIR/error_code_string_regression.cpp" \
    -o "$WORK/host/error_code_string_regression"
"$WORK/host/error_code_string_regression"

python3 "$SCRIPT_DIR/verify_error_code_string_ownership.py"

for run_name in a b; do
    docker run --rm --platform linux/amd64 --network none --read-only \
        --cap-drop ALL --security-opt no-new-privileges \
        -e RUN_NAME="$run_name" \
        -v "$PROJECT_ROOT:/project:ro" \
        -v "$WORK/target:/work:rw" \
        "$IMAGE" \
        /project/adapter/framework/appspawn-x/bionic_compat/tests/error_code_string_target_inside.sh
done

sha_a=$(sed -n '1p' "$WORK/target/a/artifact.sha256")
sha_b=$(sed -n '1p' "$WORK/target/b/artifact.sha256")
if [ -z "$sha_a" ] || [ "$sha_a" != "$sha_b" ]; then
    echo "FAIL ErrorCodeString target build is not deterministic" >&2
    exit 1
fi

echo "PASS ErrorCodeString host_semantics=18 target_owner=libziparchive compat_owner=0 deterministic=2 sha256=$sha_a"
