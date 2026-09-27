# 2026-09-27 batch dlopen-refuse of byte-security libs (#48 A.22 discriminator)
Tests whether the residual whole-heap smash comes from active byte-security libs writing Bionic-layout
metadata. Batch-refuse the safe-to-refuse (needed_by=0, dlopen-only) active security libs via the
webview shim's dlopen boundary; EXCLUDE feed-essential libttcrypto (TLS, 15 dependents) + libsscronet
(network, r1). Non-destructive A/B (control vs batch, same shim code, differ only in the refuse array).

| Path | What |
|------|------|
| DT_NEEDED-reverse.txt | APK-wide reverse DT_NEEDED (138 libs) — the classification evidence |
| src/insert12_refuse_patch.py | appends the 12-lib security batch to g_refused_libraries[] |
| NOTES.md | classification (safe/exclude + tiers), product shas, build recipe, deploy A/B |

Products (VM ~/a2hlab/ws/out-refusebatch48/): batch libwebview_bionic_shim.so sha 679623bacf9cb77a
(delivery-3 + 12); control (=delivery 85c789f4) for the paired A/B. Source = westlake-wv46 (unmodified
build reproduces 85c789f4 byte-for-byte → batch differs from delivery by exactly the 12 refuse entries).
