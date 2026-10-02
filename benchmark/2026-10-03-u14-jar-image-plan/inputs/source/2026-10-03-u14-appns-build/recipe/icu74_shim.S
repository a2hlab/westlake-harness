/* libicu74compat.so: 7 tail-branch trampolines mapping tttext's ICU-74 dlsym names to libicuuc's _72 entry points.
 * Tail-branch (b) passes all args (x0-x7/v0-v7) and the return through unchanged, so no per-function signature is
 * needed. The _72 targets are UNDEFINED here and resolved from libicuuc.so (DT_NEEDED). This shim exists only so that
 * dlsym(<ICU handle>, "ubrk_open_74") -- which OHOS musl do_dlsym resolves across the handle's dependency tree
 * (find_sym2 use_deps over dso->deps) -- finds the name without rebuilding the 2.3 MB ICU. */
.text
.macro TRAMP new, old
    .globl \new
    .type  \new, %function
\new:
    b \old
    .size \new, .-\new
.endm
    TRAMP ubrk_open_74,            ubrk_open_72
    TRAMP ubrk_close_74,           ubrk_close_72
    TRAMP ubrk_first_74,           ubrk_first_72
    TRAMP ubrk_next_74,            ubrk_next_72
    TRAMP ubrk_setText_74,         ubrk_setText_72
    TRAMP u_charType_74,           u_charType_72
    TRAMP u_hasBinaryProperty_74,  u_hasBinaryProperty_72
