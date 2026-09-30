# N8: remove the root zlib alias, retain the private shell

N7 failed its ZigZag control with `inflateInit2_: symbol not found`. The root `libz.so` shell is a suspect, not a proven cause. This offline candidate removes exactly one payload file from N7: `payload/android/lib64/libz.so`. The 1904-byte `westlake_native/libz.so` and every other declared payload file remain byte-identical. No source was rebuilt and no device was accessed.

The package is `../westlake-generation-n8-private-zlib`, manifest `3dd48299b599c2adebe8cc574649a31d84fabae53b77d5a7df704f4f380b993e`. `prepare.py` records the parent identity and refreshes the native sidecar. It also corrects N7's EGL scanner profile: the reused preparation-loop variable had bound that profile to the private zlib shell instead of `westlake_flutter/libEGL.so`. This is a metadata correction, not another runtime change.

`verify.py` checks all retained hashes, the sole removal, private-shell retention, profile bindings, and rejection of the revoked N7 window grant. Strict native preflight still rejects 185 findings (N1 31, N2 154); none is silently waived. The artifact freeze check reports zero violations; it does not attest source-only freezes. A fresh candidate-specific exception decision and board window are required.

The later 5cd U5/T7d ZigZag baseline is positive, but it is not the same-board N7 A/B and does not prove causality. N8 remains separate from U7: the outer loop selected U5 native for U7 at 04:57. No screenshots or process counts are claimed for this offline work.

Run `python3 benchmark/2026-10-01-n8-native/verify.py` after preparing the package. The package is outside the public repository; scripts, identities and gate evidence are committed here.
