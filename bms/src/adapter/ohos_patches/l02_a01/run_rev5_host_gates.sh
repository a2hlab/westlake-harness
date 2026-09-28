#!/usr/bin/env bash
set -euo pipefail

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$here/test_rev5_static_oracle.py"

if [[ -n "${OH_ROOT:-}" ]]; then
    preimage_root="$OH_ROOT"
else
    preimage_root="$here/../../out/rev5-oh-work-20260724/pre"
fi
[[ "$preimage_root" == /* && -d "$preimage_root" ]] || {
    echo "ERROR: exact OH preimage root unavailable; set OH_ROOT" >&2
    exit 2
}

tail -n +2 "$here/OH610_GAME_MIN_REV5_PREIMAGES.tsv" |
    (cd "$preimage_root" && sha256sum -c -) >/dev/null
patch --dry-run --batch --forward -p1 \
    -d "$preimage_root" \
    < "$here/oh610_game_min_rev5.patch" >/dev/null

echo "L02.A01 rev5 host gates PASS"
