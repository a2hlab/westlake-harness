# r11 minimal follow-up fix SELECTION (observation-gated; source candidates only; no patch/no device)

Prepared offline. Grounded in already-read REA originals + precise sources (libhwui `a11c9154`, bridge
`d4fae8e5`, webview-shim) AND the deployed-binary disassembly in main tree
`static/r10-live-review/checkpoint-02/`. Rule: a fix is selectable ONLY if the r11 receipt positively
establishes the object; otherwise NO change.

## Deployed-binary facts (checkpoint-02; binary-proven, NOT source-inferred)
- The player's `ANativeWindow_lock`/`unlockAndPost` GOT slots bind **libwebview_bionic_shim.so
  `85c789f4`** at offsets `0x5e48` / `0x5ff0` (6 other slots — getFormat/getWidth/getHeight/
  setBuffersGeometry/release/fromSurface — bind libandroid `76512d97`, double-mapped, per-instance
  selected by actual-pointer−symbol-value).
- **Deployed shim `85c789f4` lock@0x5e48 and unlockAndPost@0x5ff0 UNCONDITIONALLY set `errno 19` and
  return `-19`** — proven by checkpoint-02 (private disasm checked against received bytes + original
  LLVM rc0): lock's early branch is **diagnostic only**; **both** normal-return paths store `w9=#19`
  / `w0=#-19` / `ret`; unlock is a flat `__errno_location; w9=#19; w0=#-19; ret`. So the deployed
  shim does **NOT** unwrap and does **NOT** call any OH request/flush — it returns `-19` regardless of
  the window object type. (Matches `drawPicture lock-buffer ret:-19`.)
- **CORRECTION of a prior error:** an earlier draft here said "the deployed shim returns -19 only when
  `oh_anw_get_oh(window)==NULL`." That was the **f12c source** logic wrongly attributed to the deployed
  binary. It is **deleted** — the deployed `85c789f4` is unconditional `-19`, per the binary.

## Source candidates (NOT deployed; NOT verified replacements)
- **`webview_bionic_shim.c` (src sha `f12c5c92`)** has a lock (@3962) whose logic unwraps via
  `oh_anw_get_oh` then runs the OH request/map/flush path, and an unlock (@4040) that flushes. **This
  is SOURCE, not the deployed `85c789f4` implementation** (which is unconditional `-19`). A different
  implementation does **NOT** imply the deployed binary is "older" — the provenance of the deployed
  `85c789f4` build is not established. f12c is a **source candidate only**. `oh_anw_get_oh` is the
  bridge's AdapterAnw→OH resolver (`d4fae8e5@0x125a00`), the same unwrap libhwui's getters use.
- **`libandroid_webview_shim.c` (src sha `c8772d05`)** lock is RAW (no unwrap) in source; the deployed
  libandroid `76512d97` exports a lock at ELF `0x3ee4` (root r10 window-binding), but the GOT does not
  use it (binds the shim). Its raw-vs-unwrap behavior here is **source-derived**, not an independent
  deployed-0x3ee4 disasm.
- **libhwui `a11c9154`** exports fromSurface/getWidth/getFormat (wrapper-aware) but **NO
  lock/unlockAndPost** — not a lock source.

## Selection table (by r11 receipt outcome)
| Receipt outcome | Selection | Required gate before it is ever a candidate replacement |
|---|---|---|
| **object = `AdapterAnw_layout_matches`** (magic+tag+handle gate passes) | the deployed shim lock/unlock are unconditional `-19` and cannot render → a replacement is needed; the **source candidate** with wrapper-aware OH path is `webview_bionic_shim.c` `f12c5c92` lock@3962/unlock@4040 | **ALL of:** (1) independent build via `westlake/tools/build_bionic_shim.sh` (SDK clang aarch64-linux-ohos, `--version-script webview_bionic_shim.map`); (2) symbol gate — the built `.so` actually EXPORTS `ANativeWindow_lock`/`unlockAndPost` (cf. `libandroid_webview_shim.c:246` "bridge never exported" them) and `oh_anw_get_oh` resolves the observed AdapterAnw layout; (3) original-behavior regression — other callers/paths unchanged, `check_frozen` clean; (4) on-device verify. **Only after (1)-(4) is it a candidate replacement — never "verified" from source alone.** |
| **object = unknown / winner = unknown** (r11 run #1: zero samples) | **NO modification permitted** | — |
| object proven RAW OHNativeWindow (r11 magic gate does NOT positively assert raw) | not selectable from this receipt | would separately need deployed-`0x3ee4` disasm + a positive raw-object proof |

## One-line rule
Deployed shim `85c789f4` lock/unlock are **unconditional `-19`** (binary-proven). `f12c` is a **source
candidate only**, requiring independent build + symbol-export + original-behavior-regression + on-device
gates before it may even be called a candidate replacement — **never** "verified replacement" from
source, and "different implementation" is **not** evidence of "older version." Any **unknown** object
(r11 = zero samples) ⇒ **no change**.
