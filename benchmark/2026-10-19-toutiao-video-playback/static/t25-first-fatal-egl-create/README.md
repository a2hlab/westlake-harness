# T25 first-fatal — geometry adapter runs rc0, then R23 eglCreateImageKHR → NULL (576×1024). NOT a pass.

Read-only on a SHA-pinned log. No REA (by CC), no board, no build, no push. HDC = root (rolled back).
Evidence: `…/t25-5cd-window-01/candidate-log-7777/selected.raw` — 12,642,788 B, sha256
`f1e4330f1b75c1e8d5413cce28e14c1e8f12dee09c2d7633deb3002f8b56ac31`, 80,451 lines.
Codex public: `~/.local/share/westlake/t25-egl-contract/public/results.json`
(status `STATIC_CONTRACT_COMPATIBLE_DRIVER_FAILURE_REASON_UNKNOWN`).

## What the log shows (cited)
- Geometry adapter ran: `L80056 [WL-R25-BIND] HandleOpt=0x7fa6a28c10` (= surface `0x7fa69c0000` + `0x68c10`);
  `L80057/159/247/261 [WL-R25-GEOMETRY] wh=576x1024 fmt=842094169(YV12) … result=0` ×4 — the geometry+format
  **API calls returned rc0** and the 40001000 gatekeeper is gone.
- T20 `lock`/`unlockAndPost` ran 3× with **rc0** — **API success only; pixels not proven.**
- First fatal: `L80180 [WL-R23-EGL] client … window_buffer=0x7d3881ae00`; `L80181 create failed … selected=0`
  (eglCreateImageKHR returned **NULL** on the display-matched Mali impl); `L80183 FATAL skia
  AutoBackendTextureRelease Invalid GrBackendTexture Width==576 height==1024 protected==0` → SIGABRT.

## EGL import params — three fields match; the NULL reason is UNKNOWN
Codex exact REA: HWUI a11c `MakeGLBackendTexture` (0x5dc1bc) and OH's `native_image CreateEGLImage` (0x14ddc)
agree on `context=0`, `target` (0x3140→0x34e1) and `attrs=[0x30d2,1,0x3038]`, and R23's translation matches all
three. **This rules out those three surface differences only; it does not establish why create returned NULL.**
No `eglGetError` code is in the log (HWUI's `eglGetError`@0x5dc318→`SkDebugf` routes to a sink not captured here;
searched same-thread L80160–90 and whole-file).
- Provider base: the only `[WL-R23-BIND] extension=` line is the fence (same base `0x7fa11c0000`); create/destroy
  have no fallback line, so they resolved by direct `dlsym` on that Mali base. `selected=0` is the display-matched
  impl — a working design uses only the display's impl, so the single attempt is **expected, not a divergence**.
  The exact create address is not independently logged.
- The buffer: the request is **YV12 mapped to OH 11**; the **actual OH buffer descriptor (format/stride/usage) is
  UNKNOWN — not logged.** Do not assume the buffer is YV12-laid-out or RGB-tagged.

## Two distinct findings (do not conflate)
1. **Layout-contract gap — STATICALLY CONFIRMED** (Codex REA, 3 functions; separate from the EGL NULL). The player
   writes `expectedFormat = YV12` to `this+0x1d8` (`0x1f86b8`) and requests geometry YV12 (`0x1f8990`); the
   `drawPicture` geometry-success branch (`0x1f9fd8`) only clears/resets and **does not update `expectedFormat`**;
   the successful `R14` returned-format set **excludes YV12**. So **while the player stays in YV12 mode**, returned
   ≠ expected and it re-enters the "changed → clear → `unlockAndPost` → geometry" branch (`0x1f977c`; this
   window's 3 entries match). **Under that clear condition** the written pixels are **blank, not decoded video** —
   this is the changed/clear path, not an unconditional claim about every frame.
2. **EGL create NULL — OPEN.** eglCreateImageKHR returned NULL for the 576×1024 buffer; the buffer descriptor and
   the exact EGL error are uncaptured. Whether this is tied to the YV12/OH11 request or an independent import
   limit is **undecided**.

## Next (CC read-only)
- T26 (cx, new unit): hand the player a **YV12 scratch buffer** (meeting its YV12 expectation) and **convert
  YV12→real RGBX on `unlock`** for the surface — not "make the window return a format R14 reports". I will
  adversarially review its spec (lifetime, odd/even dims·stride·color, references, preserved RGB behavior) **once
  delivered** — not before the draft is consistent.
- Do **not** change EGL target/context/attrs (they match OH's own path). Do **not** read geometry/lock rc0 as
  playback.

## Scope
Read-only on the SHA-pinned log + Codex-delivered REA/source. No REA by CC, no board/build/push. The EGL-NULL
cause and the OH buffer descriptor are **UNKNOWN**; this is the new first-fatal, not the random exit.
