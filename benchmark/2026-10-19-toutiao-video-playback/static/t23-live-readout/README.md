# T23 live read-out — R23 EGL-import passes on the prefix, video still black. NOT a pass.

Read-only forensic on the **authoritative fixed-prefix** child-stderr capture. CC does **zero** device ops and
**no REA** (tool-safety constraint — REA is Codex/octoscode only). **HDC executor is root** (not cx). Analysis =
delivered logs + audited candidate source + Codex REA summary + root's screenshot reads. **Not a playback pass.**

Authoritative evidence (SHA-pinned, covers center-click + black-video phase):
`…/t23-5cd-window-01/candidate-prefix-file-02/selected.raw` — **52,899,334 B**, sha256
`03f0adb2799f511d41d5178bbdb7ad83b2cf3cfd3e1c74c958361a6761d3fa56`, `result.json`
`status=FIXED_PREFIX_COMPLETE`, boot `af001b38…`, pid 7655. Caveat: `immutability_not_proven:true` — stderr is a
live-growing file; this is a consistent 52.9 MB **selected prefix**, not proof of the final total.
Candidate source (audited, MAIN): `benchmark/2026-10-20-t23-egl-import/` (a9abaf09 / 77792).

## Corrections to the earlier quick-r2 draft (retracted)
The first draft read only the quick-r2 probe and inferred "not entered render / early net phase / render stack
just mapped not driven." **Retracted — it contradicts the full prefix, which contains real R23 events.** (a) the
quick probe's `elapsed 2.18 s` is its *collection* time, **not** 2.18 s of log *coverage*; (b)
`66352:191839:8620433` in the quick dump is the stderr file's **dev:inode:size**, not "unlabeled counters"; (c)
one must **not** conclude "R23 not called" from a 64 KiB tail with no R23 marker. The hilog `-31` note stands:
`Mutlti commands can't be used in combination [CODE: -31]` is a **real tool error** — that hilog holds zero log
lines (its rc=0 is only the wrapper's exit).

## What the 52.9 MB selected prefix shows (cited markers)
- **No fatal within this selected prefix**: `FATAL`=0, `SIGABRT`=0, `Fatal signal`=0,
  `AutoBackendTextureRelease`=0, `Invalid GrBackendTexture`=0 — **scoped to the 52.9 MB prefix only** (not an
  absolute "no fatal of any kind"). The T21 skia import-crash is **absent here**, in a capture that reaches the
  black phase.
- **R23 bound, and the runtime bind matches the T23 static offsets exactly**:
  `[WL-R23-BIND] convert_slot=0x7fabdc1850 convert=0x7faeea4be0 provider_base=0x7faee40000` →
  `0x7fabdc1850 = hwui_base 0x7fab580000 + 0x841850` and `0x7faeea4be0 = provider_base 0x7faee40000 + 0x64be0`
  — the live `dladdr`/base match resolves the hwui GOT-0x841850 target to **libsurface+0x64be0**, exactly as the
  static readout predicted (now run on-board, agrees). EGL impls: `egl_index=0`=libGLES_mali,
  `egl_index=1`=libEGL.so; fence ext `eglDupNativeFenceFDANDROID` resolved into Mali.
- **R23 EGL import succeeds**: 27 `[WL-R23-EGL]` **events** = **12 client + 12 image + 3 destroy** (peer
  independent prefix count) — i.e. **12 imports**, each `client native=…` → non-null
  `image display=0x7ef6b36c20 image=… implementation=0` (Mali), **zero** `create failed`, **zero** `refused`; 3
  `destroy … result=1`. (**27 events, NOT 27 imports.**)
- **Producer signals frames**: `[WESTLAKE-SURFACETEXTURE] frame-available … count=5640` (counter climbs by 120
  per tick). This proves **frame-available *notifications* only** — it does **NOT** prove decoded pixel content,
  and it does **NOT** by itself rule out a decode stall.
- **GL swaps**: `[WESTLAKE-SWAP] #8040 … rc=1` (eglSwapBuffers returns success 8000+× on surface 0x7ef6b35300).
  Producer path resolves too (`[WL-R20-BIND] NativeWindowRequestBuffer/FlushBuffer` → libsurface).
- **A standing logged anomaly (gatekeeper reject, not a geometry-parameter problem)**: `setBuffersGeometry …
  ret:40001000` (120× 1080×1920, 1× 576×1024). Codex geometry static (exact `libsurface` 8f `HandleOpt`): this
  `40001000` is a **door-step reject** — **window empty / inner surface empty / magic ≠ WIND** — rejected at the
  gate before opcode dispatch; a *legitimate* window that merely misses the opcode still returns **rc0**. So the
  reject is about the **window/surface object presented**, not the requested w/h/format. It is **not** in the
  shim: the exact T23 shim `a9ab` exports only `ANativeWindow_lock`/`unlockAndPost`, **no `setBuffersGeometry`**
  — do **not** attribute it to the shim. (Reusable: `t21-geometry-peer/geometry-765-rea.json` + `provider-0.so`.)

## The black-despite-frames picture — no fatal, a standing gatekeeper reject; two consume paths (Codex REA)
Screenshots (root): `cycle-observation-01` 0/5/10/20 s are **SHA-identical (490f60)** = a static cover frame;
after center-click, `cycle-observation-02` shows the **video region black while the progress bar advances**.
Frames are signalled and import/swap return success, yet nothing decoded is visible. Within the prefix there is
**no fatal/crash**, but there **is** the standing `setBuffersGeometry ret:40001000` gatekeeper anomaly — so this
is **not** "no logged anomaly."

Codex REA (static, read-only — `~/.local/share/westlake/t23-codex-rea/SUMMARY.zh-CN.md` + `focused-summary.json`;
`libnative_image.so` sha `74b6ea0d…`, 98160 B; REA 6.5.0 + Ghidra 12.1.4; ELF-vaddr +0x100000 = Ghidra addr,
**not** a runtime address) distinguishes **two consumer paths** that must not be conflated:
- **Path A — `OH_NativeImage_AcquireLatestNativeWindowBuffer`** (ELF 0x12d20 → `AcquireNativeWindowBuffer`
  0x15610, latest=true): acquire latest buffer, update info + transform matrix, `SyncFence::Dup` acquire fence,
  create/ref the wrapper, return. **Body does NOT call `UpdateEGLImageAndTexture`; no GL bind.** Codex: **the
  exact hwui `ASurfaceTexture_dequeueBuffer` imports via Path A.**
- **Path B — `OH_NativeImage_UpdateSurfaceImage`** (0x127dc → 0x14104): lock → ValidateEglState → acquire →
  **`UpdateEGLImageAndTexture`** (0x144d8; verified body **0x1144d8–0x11491b**, ELF symbol size **1092** — the
  pseudocode tail spuriously runs past a `__ubsan` abort into `AttachContext`; **do not cite that tail**) →
  `glBindTexture`+`glEGLImageTargetTexture2DOES` (with `glGetError`) → type=0x3144 sync + `glFlush`;
  `UpdateSurfaceInfo` (0x13f40) releases the old buffer and **waits the new acquire fence (timeout=-1)**.

Consequence (corrected): my earlier draft treated "`tex=0`/detached + no `glEGLImageTargetTexture2DOES` /
`UpdateSurfaceImage` marker" as the defect. **Retracted.** The hwui consumer is **Path A**, which by design does
**not** GL-bind, so those markers are legitimately absent — their absence is **not** a broken-chain proof (Codex
states this). `tex=0` ×9 + no Path-B marker is **consistent with Path A**, not evidence of failure.
- **Settled**: import is not the *crash* wall; R23 builds a non-null EGLImage (12 imports — note a non-null
  `eglCreateImage`-equivalent is **API-level create success, NOT the whole import path proven settled**); frames
  are signalled; GL swaps return success; no fatal in the prefix. Static does **not** attribute the black.
- **Open**: with no fatal but a standing gatekeeper reject, black is **unattributed**. Candidates, none proven:
  (1) the `setBuffersGeometry ret:40001000` reject is about the **presented window/surface object** (empty /
  magic ≠ WIND) — which window object is passed, and from which provider? (2) whether the R23-created EGLImage is
  actually bound into the drawn layer's GL texture and **sampled** (HWUI draw-time), vs created-but-not-drawn;
  (3) whether the acquired producer buffers carry **non-empty decoded pixels** (frame-available proves
  signalling, not content). Codex is checking the actual window-object binding.

## Status of each claim (sign-off discipline)
- **R23 EGL import**: PASS at API level (bind + 12 non-null images, no skia fatal in prefix). T21 import-crash
  absent here. **A non-null image = API-level create success, NOT the whole import path proven settled**
  end-to-end (draw-time sampling of that image is a separate, still-open question).
- **Video playback**: NOT a pass — video region black; not localized to a single cause.
- **Audio**: **user-confirmed present in this window** (operator heard sound). What is **unproven** is audio
  continuity **across clips / across the two controlled observation cycles** (a volume mis-touch may have
  switched clips). Do **not** write "audio UNPROVEN" flatly.
- **Continuous playback / pause-seek**: UNPROVEN.
- **Prefix immutability**: not proven (`immutability_not_proven:true`).
- **Android reference** (video_plan assist lane): **baseline** = Android 16 / API 36, same Toutiao **13.9.0
  target30**, APK `a1112a0c` **byte-identical to OH**, with the main process *not running* (identity baseline
  only). Distinct from that baseline, a **subsequent actual Android run has since completed** — treat the two
  separately (baseline identity ≠ the later run's behavior). Either way, an Android-reference success would
  **not** constitute an OH pass. CC does **not** repeat ADB; focus stays on the OH geometry reject + frame
  content / consume path.

## Next minimal action (CC static, read-only)
1. **Bind the actual geometry provider + the source of the passed-in window object**, reusing
   `t21-geometry-peer/geometry-765-rea.json` + `provider-0.so`: `40001000` is a `HandleOpt` **gatekeeper reject**
   (window/inner-surface empty or magic ≠ WIND), **not** a geometry-parameter problem and **not** in the shim —
   so the question is *which* window object reaches `setBuffersGeometry` and whether it is a valid WIND OH
   surface. **Do not declare first-cause from the non-zero return.** (Codex is verifying the actual binding.)
2. Do **not** chase "UpdateSurfaceImage / glEGLImageTargetTexture2DOES missing" — Path A is by design.
3. The remaining draw-time question (R23 EGLImage actually sampled; producer buffer non-empty) needs a targeted
   probe or the real log's first anomaly, not absence-of-marker reasoning.

## Scope
Read-only on SHA-pinned saved evidence + audited source + Codex REA summary + root screenshot reads. No board,
no build, no REA (by CC), no new code, no push. Runtime GL/Vk backend and the fence flag remain UNKNOWN by design.
