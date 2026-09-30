#!/bin/bash
# ============================================================================
# DEPRECATED (2026-05-12 G2.14bf sedimentation) — DO NOT USE.
# ============================================================================
#
# This was the "Round 9" experimental hwui compile script (partial 28-file
# source list — only a slice of renderthread/ + utils/ + pipeline/skia/
# + a few top-level .cpp). It was retained alongside compile_libhwui.sh
# during the iterative scratch-compile era; never produced a complete
# libhwui.so on its own.
#
# Per project rule "每个 .so 永远只有一个 compile sh" (see user memory
# feedback_one_so_one_compile_sh.md, 2026-05-12), libhwui.so has exactly
# one authoritative entry: compile_libhwui.sh, whose phase 1 compiles the
# full 88-file PHASE1+PHASE2 source list.
#
# Why DEPRECATE (not forward): forwarding to `compile_libhwui.sh --phase=1`
# would silently change semantics — callers who expected the 28-file
# partial build would suddenly get the full 88-file build with no warning.
# Hard-stop here forces an explicit migration.
# ============================================================================

cat <<'EOF' >&2
ERROR: compile_libhwui_v9.sh is DEPRECATED (G2.14bf, 2026-05-12).

This was the Round 9 partial experimental compile (28 .cpp files); its
source list never produced a working libhwui.so on its own. The
authoritative entry is now:

    bash build/compile_libhwui.sh                # full clean rebuild (recommended)
    bash build/compile_libhwui.sh --phase=1      # compile hwui sources + JNI only
    bash build/compile_libhwui.sh --phase=2      # phase 1 + 2 (shim .o + shim .so)

See compile_libhwui.sh header [C-6] for the script-consolidation history
and Annex A for the original v9-era line-by-line audit. The "one .so =
one compile sh" rule is documented in user memory
feedback_one_so_one_compile_sh.md.
EOF
exit 1
