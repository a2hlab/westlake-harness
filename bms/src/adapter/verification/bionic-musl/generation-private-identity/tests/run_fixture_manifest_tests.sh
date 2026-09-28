#!/usr/bin/env bash
set -euo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd -P)
ROOT=$(cd "$HERE/../../.." && pwd -P)
VERIFY=$ROOT/scripts/verify_unity_fixture_identity.py
WORK=$(mktemp -d "${TMPDIR:-/tmp}/unity-fixture-identity.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
GEN=$WORK/generation-r1
CARD=$WORK/cardwords
mkdir -p "$GEN/meta" "$GEN/payload/adapter" "$GEN/payload/aosp" \
    "$GEN/payload/base" "$CARD/lib/arm64-v8a" "$WORK/outside"

for path in \
    "$GEN/payload/adapter/libapp_native_loader.so" \
    "$GEN/payload/aosp/libnativeloader.so" \
    "$GEN/payload/aosp/libnativehelper.so" \
    "$GEN/payload/base/ld-musl-aarch64.so.1" \
    "$CARD/lib/arm64-v8a/libmain.so" \
    "$CARD/lib/arm64-v8a/libunity.so" \
    "$CARD/lib/arm64-v8a/libil2cpp.so" \
    "$CARD/lib/arm64-v8a/lib_burst_generated.so"
do
    printf 'fixture:%s\n' "$(basename "$path")" >"$path"
done

python3 - "$GEN" "$CARD" <<'PY'
import json, sys
from pathlib import Path
gen, card = map(Path, sys.argv[1:])
items = []
for root, base, rels in (
    ("generation", gen / "payload", [
        "adapter/libapp_native_loader.so", "aosp/libnativeloader.so",
        "aosp/libnativehelper.so", "base/ld-musl-aarch64.so.1"]),
    ("cardwords", card, [
        "lib/arm64-v8a/libmain.so", "lib/arm64-v8a/libunity.so",
        "lib/arm64-v8a/libil2cpp.so",
        "lib/arm64-v8a/lib_burst_generated.so"]),
):
    for index, rel in enumerate(rels):
        items.append({"root": root, "path": rel,
                      "sha256": f"{len(items)+1:064x}",
                      "build_id": f"{len(items)+1:040x}"})
receipt = {
    "schema": "westlake.unity.generation_private_identity.v1",
    "status": "identity_pass", "generation_id": gen.name,
    "device_verified": False, "engine_started": False,
    "roots": {"generation": str(gen), "cardwords": str(card)},
    "artifacts": items,
}
(gen / "meta/unity-identity.json").write_text(json.dumps(receipt))
PY

python3 - "$GEN" "$CARD" "$WORK/positive.tsv" <<'PY'
import json, sys
from pathlib import Path
gen, card, out = map(Path, sys.argv[1:])
r = json.loads((gen / "meta/unity-identity.json").read_text())
by_path = {}
for item in r["artifacts"]:
    root = gen / "payload" if item["root"] == "generation" else card
    by_path[str(root / item["path"])] = item
roles = {
    "main": card / "lib/arm64-v8a/libmain.so",
    "unity": card / "lib/arm64-v8a/libunity.so",
    "il2cpp": card / "lib/arm64-v8a/libil2cpp.so",
    "app_native_loader": gen / "payload/adapter/libapp_native_loader.so",
    "native_loader": gen / "payload/aosp/libnativeloader.so",
    "native_helper": gen / "payload/aosp/libnativehelper.so",
    "musl_loader": gen / "payload/base/ld-musl-aarch64.so.1",
    "dlns_provider": gen / "payload/base/ld-musl-aarch64.so.1",
}
with out.open("w") as stream:
    for role, path in roles.items():
        item = by_path[str(path)]
        stream.write(f"{role}\t{path}\t{item['sha256']}\t{item['build_id']}\n")
PY

run_reject()
{
    name=$1
    manifest=$2
    marker=$3
    if python3 "$VERIFY" --identity-receipt "$GEN/meta/unity-identity.json" \
        --fixture-manifest "$manifest" >"$WORK/$name.out" 2>"$WORK/$name.err"
    then
        echo "unexpected acceptance: $name" >&2
        exit 1
    fi
    grep -F "$marker" "$WORK/$name.err" >/dev/null
    echo "PASS $name"
}

python3 "$VERIFY" --identity-receipt "$GEN/meta/unity-identity.json" \
    --fixture-manifest "$WORK/positive.tsv" | grep -q '^UNITY_FIXTURE_IDENTITY_PASS '
echo PASS positive_manifest

cp "$GEN/payload/aosp/libnativeloader.so" "$WORK/outside/libnativeloader.so"
sed "s#$GEN/payload/aosp/libnativeloader.so#$WORK/outside/libnativeloader.so#" \
    "$WORK/positive.tsv" >"$WORK/competing.tsv"
run_reject competing_path "$WORK/competing.tsv" GENERATION_PATH_OUTSIDE_PRIVATE_ROOT

awk -F '\t' 'BEGIN{OFS="\t"} $1=="native_loader"{$3="0"$3} {print}' \
    "$WORK/positive.tsv" >"$WORK/wrong-sha.tsv"
run_reject wrong_sha "$WORK/wrong-sha.tsv" GENERATION_PATH_OUTSIDE_PRIVATE_ROOT

awk -F '\t' 'BEGIN{OFS="\t"} $1=="native_loader"{$4="0"$4} {print}' \
    "$WORK/positive.tsv" >"$WORK/wrong-buildid.tsv"
run_reject wrong_buildid "$WORK/wrong-buildid.tsv" GENERATION_PATH_OUTSIDE_PRIVATE_ROOT

grep -v '^il2cpp' "$WORK/positive.tsv" >"$WORK/missing-role.tsv"
run_reject missing_role "$WORK/missing-role.tsv" 'fixture manifest roles incomplete'

awk -F '\t' 'BEGIN{OFS="\t"}
    $1=="app_native_loader"{saved=$0; next}
    $1=="native_loader"{print "app_native_loader",$2,$3,$4; print}
    $1!="native_loader"{print}' "$WORK/positive.tsv" >"$WORK/duplicate-path.tsv"
run_reject duplicate_path "$WORK/duplicate-path.tsv" 'one identity artifact fills multiple roles'

echo UNITY_FIXTURE_IDENTITY_TEST_PASS checks=6
