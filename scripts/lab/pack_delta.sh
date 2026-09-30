#!/bin/bash
# Pack what changed after a pack_airdrop.sh folder was sent: the given paths (relative to the workspaces dir)
# plus the current OLP boards, into a small folder with SHA256SUMS and unpack_delta.sh (env.md §5).
# Code needs no delta: it is pushed to a2hlab and unpack_delta.sh fast-forwards the checkouts.
#
#   pack_delta.sh <out dir> <path relative to workspaces>...
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1
OUT=${1:?usage: pack_delta.sh <out dir> <path>...}; shift
PACK="python3 $(dirname "${BASH_SOURCE[0]}")/pack_lab_archive.py"; H=$WORKSPACES/westlake-harness
mkdir -p "$OUT"; rm -f "$OUT"/*.part* "$OUT"/*.files "$OUT"/SHA256SUMS
if [ $# -gt 0 ]; then
  args=(); for p in "$@"; do args+=(--path "$WORKSPACES/$p"); done
  $PACK "$OUT/delta.tar.zst" --root "$WORKSPACES" "${args[@]}"
  split -b 4000m -d -a 2 "$OUT/delta.tar.zst" "$OUT/delta.tar.zst.part"; rm -f "$OUT/delta.tar.zst"
fi
$PACK "$OUT/octos-state.tar.zst" --root "$WORKSPACES" --path "$H/.octos/boards" --path "$H/.octos/OUTER_LOOP_REVIEW.md" \
  --path "$H/.octos/EVOLUTION.md" --path "$H/.octos/archive"
split -b 4000m -d -a 2 "$OUT/octos-state.tar.zst" "$OUT/octos-state.tar.zst.part"; rm -f "$OUT/octos-state.tar.zst"
cp "$(dirname "${BASH_SOURCE[0]}")/unpack_delta.sh" "$OUT/"
(cd "$OUT" && find . -type f ! -name SHA256SUMS ! -name .DS_Store | sort | xargs shasum -a 256 > SHA256SUMS)
du -sh "$OUT"; echo ALL-DONE
