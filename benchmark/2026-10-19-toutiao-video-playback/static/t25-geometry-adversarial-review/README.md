# T25 geometry fix — adversarial review (principles; spec not yet generated)

Independent adversarial review by cc-video. **No REA, no device, no build.** Read-only on Codex's delivered
geometry evidence (`~/.local/share/westlake/t23-codex-rea/geometry/`) — the T25 tree
`westlake-harness-t25-geometry` has **no geometry spec yet**, so this reviews the **proposed principles**, not a
written contract. Proposed approach under review: *reuse the trusted T20 owner-unwrap; on the same-instance
HandleOpt call `opcode 0 (w/h)` first and, only on success, `opcode 3 (format)`; preserve the real rc;
foreign/null reject gate; do not regress the existing T23 four EGL + CPU behaviors.*

## Grounding (from Codex pseudocode — cited, not re-run)
- `NativeWindowHandleOpt` (libsurface 8f, 0x68c10): initial return `0x2625de8` = **40001000**; it becomes `0`
  **only** when `window!=0 && *(window+0x18)!=0 && *(int*)(window+0x10)==0x57494e44 ('WIND')`, then dispatches
  the opcode (SET_BUFFER_GEOMETRY = opcode 0). → **40001000 is an object-validity gate (null / empty inner
  surface / magic≠WIND), independent of the w/h/format values.** Confirmed.
- `ANativeWindow_setBuffersGeometry` (libandroid 765, 0x3d84): calls `provider(window, 0, w, h)` with the window
  **passed UNCHANGED (no unwrap)**; only if `format>0 && opcode0 rc==0` does it map format (fmt2→0xb …) and call
  `provider(window, 3, mappedFmt)`; on opcode0 failure it returns that rc immediately. So the failing path never
  reaches the format branch (matches the log: all 40001000 are at opcode 0).
- Shim `a9ab` dynsym exports **only** `ANativeWindow_lock`/`unlockAndPost` — **no** setBuffersGeometry. The
  geometry impl is in libandroid 765, **not** the shim.
- Log (Codex independent count): 120× (1080×1920, fmt2, window `0x7faf173a60`) + 1× (576×1024, fmt842094169,
  window `0x7fb2b9c2a0`), all ret 40001000. The two windows are **distinct pointers** from the T20-unwrapped OH
  window `0x7fae81ad30`. So the **narrowest candidate** — an Android wrapper handed to a provider that expects a
  WIND OH window — is **consistent** with evidence, but **not proven root** (geometry's actual resolver winner
  was never captured).

## Verdict on the approach
Structurally **sound and evidence-aligned**: opcode0→opcode3 matches the 765 shape; HandleOpt confirms the
failure is object-validity, so unwrapping the Android wrapper to the OH window (which carries the WIND magic)
before the call is the right lever, and keeping EGL/CPU untouched is correct. **But** three guardrails must be
answered **before** this is implemented/deployed — each maps to a real gap in the delivered evidence.

## 3 BLOCKING questions (must resolve before build/deploy)
1. **Winner-instance guard (mis-deployment).** Codex states geometry's **actual resolver winner is unknown** —
   only the lock/post provider base (`7faee40000`) is logged; the geometry downstream HandleOpt slot was **not
   captured**, so the lock binding **cannot be inherited**. T18 proved the *same SHA* can load as **2 instances**
   (two namespaces). **Q: how does the fix prove the geometry provider winner is the *same instance* as the T20
   unwrap owner, at run time, before binding — so it cannot silently bind a different libsurface instance's
   HandleOpt?** Without a logged winner==owner base/dladdr check that *refuses on mismatch*, a wrong-instance
   mis-deployment is not blocked (an OH window minted by instance X can fail instance Y's gate, or pass magic but
   dispatch into a foreign opcode table).
2. **Unwrapped-window lifetime + format-ring key (UAF / wrong-key).** 765 makes **two sequential** provider calls
   on the window with **no lock held across them**, and stores the requested format in a 64-slot ring keyed by
   the **raw window ptr**. **Q: across the opcode0→opcode3 pair, does the fix hold a reference on the unwrapped
   OH window for the whole pair (so a concurrent release can't free it between calls), and is the format ring
   keyed *consistently* (wrapper vs OH window) so a later lookup isn't a wrong-key / stale read?** This must not
   regress the T23 EGL/CPU wrapper lifecycle.
3. **Preserve 40001000 — do NOT swallow.** Codex warns some legacy shims "**ignore the OH error and still return
   0**". **Q: on opcode0 failure does the fix return the *real* rc (40001000), never a forged 0 / format-ring
   success — and does it run the format opcode3 *only* when opcode0 rc==0?** If a mis-unwrap is masked as success,
   the surface stays mis-bound, the video stays black, **and** the 40001000 diagnostic signal is destroyed. The
   foreign/null reject gate must refuse at the **shim boundary before** the provider call (stable rc), while
   **passing through** inputs that are already valid OH windows (no double-unwrap).

## Non-blocking notes
- The fix is a **new, unfrozen** geometry-adapter unit (don't lift whole legacy `android_graphics_compat_shim.cpp`
  / `webview_bionic_shim.c:3842` — they carry the "return 0 on OH error" and re-dlopen behaviors Codex flagged).
- `40001000` being object-validity means **do not** "fix" it by changing requested w/h/format — that would be
  chasing the wrong variable (the earlier geometry-parameter framing is retracted in the T23 readout).
- Even if geometry passes, **video-visible is not implied**: the draw-time sampling of the R23 EGLImage +
  non-empty producer content remain separate open questions. Don't let a geometry pass be read as a playback pass.

## 2026-10-20 RE-REVIEW against the actual spec + blueprint (concrete seams)
Read the real files: `westlake-harness-t25-geometry/specs/toutiao-video-playback/t25-geometry-unwrapping.spec.md`
+ `benchmark/2026-10-20-t25-geometry/BLUEPRINT.md` (lint 78%). Correcting my principle-only review:
- **Q3 (no-swallow) — RESOLVED by the spec.** It mandates "返回第一个实际失败，不吞错或用成功覆盖失败", explicit
  uncalled statuses (not fabricated rc0), reject null/foreign **before any OH call**, and "do not copy the
  [donor's] unconditional return0". Scenarios `geometry失败不执行format` / `format失败与不设置format` pin it.
- **Q2 (format-ring key) — MOOT.** The new TU calls `HandleOpt(oh,0,w,h)` then `HandleOpt(oh,3,mapped)`
  **directly**, bypassing libandroid765's `g_requested_formats` ring entirely — no wrong-key/stale-read path.
  Format map 1/2/3/4/YV12→12/11/13/3/11 **matches the 765 switch exactly** (case2→0xb, YV12=0x32315659=842094169
  →0xb). Lifetime narrows to B3 below.
- **Q1 (winner guard) — PARTIALLY in-spec, sharpened to B1.** Spec requires `actual_winner` bound from the
  geometry chain, refuse foreign/mismatch, "CPU pair绑定或同名/同SHA多映射不能替代", no new cross-ns dlopen. Good —
  but the *mechanism* is the real blocker.

### REAL blockers (concrete code seams — for Codex/base5, who are answering)
- **B1 — same-instance HandleOpt must be *provable* from `owner.unwrap`, not a global dlsym (TOP).**
  `binding.resolve_and_admit` must pick HandleOpt from the **same** provider instance that minted `borrowed_oh`,
  but `owner.unwrap` returns only the OH pointer, and the geometry winner was **never logged** (T18: same SHA = 2
  instances). `borrowed_oh` is a heap object — it does not `dladdr` to libsurface. **Seam question: does T20
  `entry.h` expose the owning provider base/handle for `borrowed_oh`, OR does the OH window carry a provider
  back-pointer (at `window+N`) that `resolve_and_admit` can read → `dladdr` → bind HandleOpt in that exact base?**
  If neither, same-instance HandleOpt is unprovable and the TU must resolve HandleOpt independently (dlsym/its own
  handle) = exactly the wrong-instance bind the spec forbids. This is the gating design fact.
- **B2 — runtime *routing* to the new entry is unspecified.** Exporting `ANativeWindow_setBuffersGeometry` from
  the shim does not make the player call it instead of **libandroid765's** same-named export (765 is where the
  logged 40001000 came from). The spec's human scenario *requires* runtime proof "the player's actual geometry
  call entered this new entry", but **no routing mechanism** (symbol interposition / DT_NEEDED order / namespace
  precedence) is defined. Without one, the adapter is dead code and geometry still routes to 765. **Seam: define
  and prove the bind-precedence that makes the player resolve the shim entry.**
- **B3 — cross-API same-window serialization (narrow).** Borrow-no-ref relies on T20's "external serialization".
  `geometry.apply` does both HandleOpt calls in one TU call (good — no release *between* opcode0/opcode3 from a
  single caller), but geometry (UI thread) and the existing `lock`/`unlockAndPost` (render thread) run on the
  **same window from different threads**. **Seam: does the T20 owner serialization contract cover *cross-API*
  same-window concurrency, or only same-API?** If only same-API, a concurrent lock/post could invalidate
  `borrowed_oh` under the adapter. Must be stated, not assumed.

### Standing caveats (unchanged, must survive to sign-off)
- A geometry pass **moves one wall only**; video-visible needs the R23 EGLImage draw-time *sampling* + non-empty
  producer content — spec's final human scenario correctly keeps this separate (two full video cycles; static/host
  pass ≠ video pass). Also: **R23 "import non-null image" ≠ the whole import path proven** — it is API-level
  create success, not end-to-end import correctness.

## 2026-10-20 — Codex seam response resolves B1/B3; ring corrected; B2 statically resolved
Codex appended "Adversarial review response" to the same BLUEPRINT. Updating:
- **B1 (same-instance) — RESOLVED, implementable.** Seam: open exact owner `RTLD_NOLOAD`; require get/acquire/
  release `0x125dc0/0x125dfc/0x125e4c`; validate ELF PT_LOAD coverage; read owner Reference/Unreference slots
  `0x1740a0/0x173fc8`, require their values == owner-handle dep-scope `dlsym` resolutions **sharing one libsurface
  base**; resolve HandleOpt through that same handle, require `dladdr` base == that base **and** offset ==
  `0x68c10` (exact 8f). CPU-pair log alone cannot satisfy it. Proves the *candidate's* HandleOpt instance.
- **B3 (lifetime) — RESOLVED.** dca owner disasm proves acquire atomically `+1` at `0x125e28–38`, release `-1`
  at `0x125e80–9c` + destroy. Hold **one extra owner ref before unwrap, across both opcodes, balance once per
  exit**; caller must already own a valid ANativeWindow ref (T20 requires). A stale ptr can't be made safe.
- **Ring — I was WRONG to call it MOOT.** exact765 writes the requested format under the **original wrapper key
  before HandleOpt, even on failure** (`libandroid_webview_core_shim.c` writer@527, reader@547, legacy lock@745
  → YV12 scratch). T20 lock reads format from the returned OH buffer, **not** this private 765 ring. So: invent
  **no** new T25 ring; within a player proven to use T20 lock/unlock the legacy ring is **out of the data path**;
  **mixed 765-lock routing is a regression risk → reject candidate admission until explicitly handled**; never
  call old geometry just to mutate its ring (unintended provider calls).
- **Raw-OH pass-through — out of scope** (no provenance registry for raw OH ptrs; accept trusted player/bridge
  wrappers only, foreign reject before OH). My earlier "pass through already-valid OH windows" note is withdrawn.

### B2 routing — STATIC ADMISSION SUPPORT (runtime geometry entry/GOT pending; human gate retained)
The static symbol chain **supports the routing prediction**, but does **not** prove it: the dynamic geometry
entry / GOT was **not captured**, so this is **static admission support, runtime pending** — keep the human gate.
Concrete slot evidence (binutils `llvm-objdump -T/-p`, no REA; source artifacts cited below):
- Player `libttmplayer.so`
  (`toutiao-video-r2-gate-inputs/apk-lib/libttmplayer.so`): `ANativeWindow_setBuffersGeometry` /
  `ANativeWindow_lock` / `ANativeWindow_unlockAndPost` all `*UND*` (**unversioned**); `NEEDED libandroid.so`;
  does **NOT** `NEEDED` the shim.
- `libandroid-765.so` (`t23-codex-rea-package/packet-01/inputs/libandroid-765.so`; SONAME `libandroid.so`, =
  the player's NEEDED) exports **all three** (unversioned): `setBuffersGeometry@0x3d84`, `lock@0x3ee4`,
  `unlockAndPost@0x42e4`.
- Current shim (`t23-candidate-inputs/libwebview_bionic_shim.so`; SONAME `libwebview_bionic_shim.so`, NEEDED
  only `libc.so`) exports **only** `lock@0x6a00` / `unlockAndPost@0x6a14` (**version `LIBC`**) — **no**
  setBuffersGeometry.
- **Observed (52.9 MB log):** the player's lock/unlockAndPost run through the **shim** (`[WL-R20-*]`), even though
  the player NEEDs `libandroid.so` and not the shim → the shim appears to sit in a **global/preload group that
  shadows libandroid for the symbols it exports**; setBuffersGeometry (not exported by the shim) falls through to
  libandroid-765 — consistent with the 40001000 coming from 765 while lock comes from the shim.
- **Prediction (not proof):** adding `setBuffersGeometry` to the **same shim**, exported the **same default-global
  way as lock**, should inherit the same precedence and shadow libandroid-765's geometry — because lock and
  geometry are both UND in the same player, unversioned, resolved through the same scope. This is a **supported
  static admission**, **not** an "inevitable / already-proven" routing: the actual dynamic geometry entry/GOT/
  winner is uncaptured, so **the on-board human gate stays required**.
- **Preconditions (concrete):** (1) export geometry as a **default global** symbol like lock (not hidden /
  version-incompatible), else no shadow; (2) mixed-765-lock routing must stay excluded — cx now limits this with
  a **3-slot actual gate** and tests on **real dispatch**; (3) the spec's runtime proof that the player's call
  entered the new entry remains the closing evidence.

**Net:** B1/B3 resolved by Codex seams; **B2 has static admission support, runtime pending** (human gate kept).
Remaining are the spec's own standing gates — on-board winner/route evidence + two-cycle video acceptance +
explicit mixed-765 rejection (cx 3-slot gate). No geometry-only pass signs video.

## Scope
Read-only on the delivered spec + blueprint + Codex geometry evidence/pseudocode + binutils (`llvm-objdump`) on
delivered artifacts. No REA (by CC), no device, no build, no push. Re-review the implementation + receipts when
the T25 TU and host checker are produced.
