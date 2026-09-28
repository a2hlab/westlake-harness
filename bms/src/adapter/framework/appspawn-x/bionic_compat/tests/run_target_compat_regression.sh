#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../../../.." && pwd)
WORK="$SCRIPT_DIR/.work/target-compat-regression"
IMAGE=sha256:76236bc11d9359a260c3e715cfee437bed387f76ff86c9ac086c1a52c3536797

case "$WORK/" in
    "$PROJECT_ROOT/"*) ;;
    *) echo "FAIL work root escaped project" >&2; exit 2 ;;
esac
if [ -L "$SCRIPT_DIR/.work" ]; then
    echo "FAIL symlinked work root" >&2
    exit 2
fi
mkdir -p "$WORK"

for run_name in a b; do
    docker run --rm --platform linux/amd64 --network none --read-only \
        --cap-drop ALL --security-opt no-new-privileges \
        -e RUN_NAME="$run_name" \
        -v "$PROJECT_ROOT:/project:ro" \
        -v "$WORK:/work:rw" \
        "$IMAGE" \
        /project/adapter/framework/appspawn-x/bionic_compat/tests/target_compile_inside.sh
done

sha_a=$(sed -n '1p' "$WORK/a/artifact.sha256")
sha_b=$(sed -n '1p' "$WORK/b/artifact.sha256")
if [ -z "$sha_a" ] || [ "$sha_a" != "$sha_b" ]; then
    echo "FAIL target compatibility build is not deterministic" >&2
    exit 1
fi

echo "PASS target_compat_aarch64 deterministic=2 sha256=$sha_a"

