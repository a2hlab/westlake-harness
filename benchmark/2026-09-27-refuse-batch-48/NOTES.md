# batch dlopen-refuse of active byte-security libs (#48 A.22 discriminator)
date: 2026-09-27

## Goal
Test whether the residual whole-heap smash (~15-20% with SLACK=64 pad, or on the base delivery) comes
from active BYTE-SECURITY libs writing Bionic-layout metadata. Batch-refuse the safe-to-refuse active
security libs via the webview shim's dlopen boundary; A/B feed + crash rate. Non-destructive
(snapshot delivery → deploy batch → A/B → restore). Cheaper than the hanbin week-level investment.

## Classification (basis: APK-wide reverse DT_NEEDED, 138 arm64 libs / 813 NEEDED edges — DT_NEEDED-reverse.txt)
A lib is safe to refuse (from a linkage standpoint) iff NOTHING DT_NEEDEDs it (needed_by=0) → it is
dlopen-only. Feed-essentiality is a separate runtime question, judged below.

**EXCLUDE — feed-essential (DT_NEEDED by many; refusing breaks the dependents):**
- `libttcrypto.so` — **needed_by=15** (ttboringssl/sscronet/lynxsecurity/ropaencrypt/vcn*/ttmverify*/…):
  HTTPS/TLS core. Refusing it cascades into TLS + network → breaks the feed. EXCLUDED.
- `libsscronet.so` — **needed_by=4** (bdvideouploader/ttmverify/vcnverify/xbnlog) + it IS the network
  engine (r1 confirmed feed-essential: a guard on it blanked the feed). EXCLUDED.

**REFUSE — all needed_by=0 (dlopen-only, verified), sscronet/ttcrypto neither DT_NEEDEDs any of them:**
- HIGH-confidence safe (monitoring / RASP / heap-tracking group; consent-gated; prior evidence: feed
  works without them; metasec/monitorcollector already neutered, npth already hollow):
  `libjato.so`, `libmetasec_ml.so`, `libmonitorcollector-lib.so`, `libgodzilla-lib.so`,
  `libgodzilla-memsponge.so`, `libgodzilla-sysopt.so`, `libsysoptimizer.so`.
- MEDIUM-risk (the A.22 crypto/UI-security TARGET; needed_by=0 so NO linkage break, but MIGHT be
  feed-functional for request-signing / Lynx-card rendering — the A/B feed-check reveals it):
  `libEncryptor.so`, `libencrypt.so`, `libgecko_encrypt.so`, `libropaencrypt.so`, `liblynxsecurity.so`.

## Product (mechanism: extend the shim's compile-time g_refused_libraries[]; dlopen() returns NULL for a refused basename)
The webview shim already dlopen-refuses 3 (libakamaibmp + libnpth_xasan + libnpth_heap_tracker) = the
delivery state 85c789f4. Batch = delivery-3 + the 12 above (append, comments preserved).
- **batch shim: `libwebview_bionic_shim.so` sha256 `679623bacf9cb77acdae35f8b1f05c6d5e97425132b5f0fb54acb9439896703a`**
  (52264 B; refuse list = exactly 15; sscronet/ttcrypto NOT in it; dlopen@@LIBC exported).
- **control (= delivery 85c789f4): `control-libwebview_bionic_shim.so` sha256 `85c789f48b2bc0c3…`** —
  built from the SAME source with the delivery-3 list, byte-for-byte reproduces the deployed shim.
- Both VM: `~/a2hlab/ws/out-refusebatch48/`. Source = westlake-wv46 (the EXACT delivery-shim source;
  unmodified build reproduces 85c789f4 byte-for-byte, proving the batch differs from delivery by
  EXACTLY the 12 appended refuse entries and nothing else).

## Build recipe (build_webview_shims.sh, second/deployed path)
SDK clang --target=aarch64-linux-ohos -fPIC -O2 -Werror -c webview_bionic_shim.c ; -c webview_setjmp_arm64.S ;
link: -fuse-ld=lld -nostdlib -shared -Wl,-z,defs -Wl,--build-id=sha1 -Wl,-soname,libwebview_bionic_shim.so
-Wl,--version-script=webview_bionic_shim.map crtbegin.o *.o -Wl,--as-needed -ldl -lc builtins.a crtend.o.
Refuse-list edit = src/insert12_refuse_patch.py (append 12 before the g_refused_libraries[] close).

## Deploy (claude-2) — non-destructive, recoverable, clean paired A/B
Snapshot the delivery state first. For the cleanest discriminator, run the PAIRED A/B with SAME shim
code differing ONLY in the refuse array:
- control arm = control-libwebview_bionic_shim.so (85c789f4, delivery-equivalent) — re-measure baseline crash rate.
- batch arm   = libwebview_bionic_shim.so (679623ba, +12 security libs).
Deploy each to /data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so (verify sha), ~15 warm rounds each.
Measure: (1) FEED still renders (if a MEDIUM-risk lib is feed-essential the feed breaks → back off that lib);
(2) crash rate. If batch << control → the byte-security libs were writing the residual smash (→ then
bisect which of the 12; the MEDIUM-risk crypto set is the prime suspect). If batch ≈ control → the
residual is NOT these libs (→ wild-pointer write elsewhere; fall back to SLACK-pad + fresh self-heal).
Restore the delivery shim after. This is the go/no-go before the hanbin week-level investment.
