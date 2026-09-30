#!/bin/bash
# apply_all.sh — Apply all ninja phony patches after `gn gen` regenerates
# the toolchain.ninja and obj/.../*.ninja tree, but BEFORE `ninja` build.
#
# Background:
#   This project does not need libarkruntime.so / libani_helpers.z.so /
#   real irtoc-compiled .o files at runtime (confirmed by user 2026-04-11).
#   irtoc segfaults when invoked, so the corresponding build edges have to
#   be rewritten to phony / `touch ${out}` so ninja can complete the graph.
#
# Each sub-script is dynamic and idempotent: it greps the current ninja
# tree for the relevant target, and patches the matching line. Re-running
# the same script is a no-op (or equivalently produces the same edit).
#
# Exit codes:
#   0 — all 3 patches applied (or already in place)
#   non-zero — at least one patch failed; check stderr for the offender
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo '[ninja_patches] === post-gn-gen apply ==='
echo '[ninja_patches] OH_PRODUCT_NAME='${OH_PRODUCT_NAME:-rk3568}
echo
echo '[ninja_patches] [1/3] irtoc rule -> touch ${out}'
bash "$SCRIPT_DIR/patch_irtoc.sh"
echo
echo '[ninja_patches] [2/3] libarkruntime.so solink -> phony'
bash "$SCRIPT_DIR/patch_arkruntime.sh"
echo
echo '[ninja_patches] [3/3] libani_helpers.z.so solink -> phony'
bash "$SCRIPT_DIR/patch_ani_helpers.sh"
echo
echo '[ninja_patches] === all patches applied ==='
