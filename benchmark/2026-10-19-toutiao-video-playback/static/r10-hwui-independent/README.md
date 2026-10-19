# Exact HWUI window functions: independent static evidence

A wrapper-producing function was previously conflated with an OH raw-window consumer. This local LLVM inspection pins the archived runtime HWUI to SHA256 `a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2` and records actual commands and rc0. The binary provenance is in `benchmark/2026-10-12-exact-realization/source-fingerprint.json`.

At ELF 0x807238, fromSurface preserves/acquires an existing wrapper or wraps a raw window; getWidth at0x807518 and getFormat at0x8075a8 first call oh_anw_get_oh. This is an exact binary candidate, not proof of the live inner dlsym winner. The observed player imports bind to libandroid765, whose bridge_symbol dependency lookup remains to be observed during the actual call. A later read of an old object address cannot prove the original object's type or corruption.

Only the local workspace prefix is normalized in public commands/output; raw and public SHA256 are recorded separately. No build, device access or runtime behavior change was performed for this inspection.
