# Toutiao stable baseline — confirmed-benefit fixes (2026-09-26)

The set of fixes whose benefit is established, to deploy as one known-good stack.
Each removes a class outright or is a deterministic mitigation. The two still-open
items (metasec sixth exit, its interaction with survival) are **not** in the
baseline; they are tracked in README §9/§10 and the #48/#49 board work.

## Deploy stack

| Component | Artifact (sha256) | Fixes | Verified |
|---|---|---|---|
| WebView shim | `libwebview_bionic_shim.so` **85c789f4** | #46 GLES-order (article WebView SIGSEGV) + #49 refuse `libnpth_xasan`/`libnpth_heap_tracker` (musl heap corruption) | GLES verified on board; refuse pending 5×3min |
| Adapter bridge | `liboh_adapter_bridge.so` **d4fae8e5→patched d4fae8e5** (mc46) | #46 MediaCodec: fail `native_setup` like AOSP + register `getOwnCodecInfo` (article-video SIGTRAP) | rebuilt, board pending |
| libnpth | `libnpth.so` **8b8d559c** | #46 neutralize the Bionic thread-list walk (npth-dumper 100% spin) | static+outer-loop live sample |
| Toutiao run.sh | targets `+cjtfccsm +delta` (**22c1d3df**) and/or `LD_PRELOAD libttcrypto` (**33b4ab08**) | #46 TicketGuard HMAC split (BoringSSL/OpenSSL3 pair) | coverage verified; board pending |
| board_setup | raise `vm.max_map_count` before launch (probe noexec/SELinux first) | #46 class-5 in-process-renderer PartitionAlloc ceiling (mitigation) | mitigation, board pending |

Notes:
- The WebView shim `85c789f4` carries **both** #46 GLES-order and #49 refuse; deploy it once and both apply. Its exports and DT_NEEDED equal the GLES-only `ecc7b12c`.
- The bridge and shim are dropped by the WebView packager; overlay them into `webview-t-lib/` by hand and re-check sha256 (memory #27).
- The tt run.sh: apply targets first (cheap); add `LD_PRELOAD libttcrypto` if a second copy of the pair still appears during a video article (README §7).

## Board gate for the baseline

`scripts/assert_heap_corruption_gone.sh` + the per-class assertions. Gate: 5 fresh
starts, each surviving 3 min on a video article, with feed and article body shown.

## Out of baseline (open)

- **metasec sixth exit (#48).** A1/A2 reduce but do not reliably remove it; the real
  cause is a missing `ASensorManager_getDefaultSensor` no-op in the default-namespace
  libandroid (README §9b, `evidence/metasec-sensor-48.txt`). Candidate route C — add
  the 7 sensor no-ops to that libandroid — is the next non-Bionic step; not yet on a board.
- **Bionic (M3/M4)** stays the long-term system fix for the whole "ByteDance native
  assumes Bionic" class (xasan/heap_tracker/metasec working, not just not-crashing).
  Reading feed+articles does not require it.
