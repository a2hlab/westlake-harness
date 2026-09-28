#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 GENERATION_ROOT SOURCE_PAIR_RECEIPT READELF_REAL_FILE" >&2
  exit 64
fi

ROOT=$(cd "$(dirname "$0")/.." && pwd)
GENERATION_ROOT=$1
SOURCE_PAIR_RECEIPT=$2
READELF=$3
READELF_REAL=$(readlink -f "$READELF")
GENERATION_ID=$(basename "$GENERATION_ROOT")
APK=$ROOT/frozen/product_inputs/cardwords-current/canonical/selfcontained_cardwords.apk
CARDWORDS_ROOT=$ROOT/build/generation-private-cardwords/$GENERATION_ID
IDENTITY=$GENERATION_ROOT/meta/unity-identity.json

if [[ -e "$IDENTITY" || -L "$IDENTITY" ]]; then
  echo "UNITY_PRODUCT_SEAL_REJECT refusing identity reuse: $IDENTITY" >&2
  exit 1
fi

failure()
{
  rc=$?
  echo "UNITY_PRODUCT_SEAL_FAIL adapter_generation_pass=true unity_product_generation=false generation=$GENERATION_ID rc=$rc" >&2
  exit "$rc"
}
trap failure ERR

python3 "$ROOT/scripts/extract_cardwords_apk_binary_only.py" \
  --generation-root "$GENERATION_ROOT" \
  --apk "$APK" \
  --source-pair-receipt "$SOURCE_PAIR_RECEIPT" \
  --readelf "$READELF" \
  --output-root "$CARDWORDS_ROOT"

python3 "$ROOT/scripts/verify_cardwords_apk_binary_only_receipt.py" \
  --generation-root "$GENERATION_ROOT" \
  --extraction-root "$CARDWORDS_ROOT" \
  --receipt "$CARDWORDS_ROOT/native-bundle.json" \
  --readelf "$READELF"

python3 "$ROOT/verification/bionic-musl/generation-private-identity/write_identity_receipt.py" \
  --generation-root "$GENERATION_ROOT" \
  --generation-manifest "$GENERATION_ROOT/meta/generation.json" \
  --cardwords-root "$CARDWORDS_ROOT" \
  --cardwords-receipt "$CARDWORDS_ROOT/native-bundle.json" \
  --readelf "$READELF_REAL" \
  --output "$IDENTITY"

trap - ERR
echo "UNITY_PRODUCT_SEAL_PASS adapter_generation_pass=true unity_product_generation=true generation=$GENERATION_ID identity=$IDENTITY"
