# Westlake → route-A surface copy-patch (window-session→OH-NativeWindow binding + EGL surface lifecycle)

**Mode:** READ-ONLY cross-codebase diff. Nothing was modified. This is a patch-spec for cx-t0 to fold into N1.
**Date:** 2026-09-30
**Bug under repair (route-A):** RenderThread calls `eglCreateWindowSurface` on the SAME OH NativeWindow twice → #2 returns NULL (EGL_BAD_ALLOC: one OH NativeWindow holds one window surface) → `mEglSurface == EGL_NO_SURFACE` → skia `drawRenderNode called on a context with no surface!` → hwui_abort → exit134. Trigger: multi-activity apps create 2 sessions (203→204); the 2nd session's render path resolves to a window already bound by session 203.

## Source-of-truth files
| tag | path | role |
|---|---|---|
| **W-owmc** | `/Users/zhaoyue/orca/westlake/westlake-noice-ohos/bridge-src/oh_window_manager_client.cpp` | Westlake (correct) session→window binding |
| **W-hwui** | `/Users/zhaoyue/orca/westlake/westlake-deploy-ohos/v3-hbc/patches/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp` | Westlake (correct) hwui EGL hijack, **G3.2 bounded retry** |
| **W-hwui2** | `/Users/zhaoyue/orca/westlake/westlake-noice-ohos/bridge-src/hwui_oh_abi_patch.cpp` | Westlake sibling hijack (SET_FORMAT/USAGE re-assert + attempt<3 retry) |
| **A-owmc** | `/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/framework/window/jni/oh_window_manager_client.cpp` | route-A / 32df base session→window binding |
| **A-hwui** | `/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp` | route-A hwui EGL hijack (colorspace-strip retry + eglDestroySurface hijack) |
| **A-shim** | `/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp` | route-A SC→session→window resolver (BBQ.update / sc_to_oh_native_window) |
| **A-java** | `/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/adapter/framework/window/java/WindowSessionAdapter.java` | route-A Java 2nd-window guard (`mSurfaceControlMap`) |

> The two benchmark variants named in the brief (`.../2026-09-29-unlocked-generation/source/window-restore/…` and `…/window-cohort/…`) **do not exist** on disk (searched all of `benchmark/`); A-owmc above is the live 32df-base target.

---

## Mechanism A — session → OH-NativeWindow binding (`oh_window_manager_client.cpp`)

### A.1 Westlake (correct) — how it avoids handing one NativeWindow to two sessions

1. **One distinct RSSurfaceNode per `createSession()` call**, stored in `sessions_` keyed by sessionId, so every session owns its own producer surface → its own OH NativeWindow.
   - W-owmc:347-350 `RSSurfaceNode::Create(nodeCfg, APP_WINDOW_NODE, isWindow=true)` (called once per invocation).
   - W-owmc:522-548 `sessions_[sessionId] = entry;` with `entry.surfaceNode = surfaceNode`.
2. **Multi-activity / dialog root fix — a 2nd MAIN-typed window is re-routed as a SUB_WINDOW of the foreground main**, so A→B (and translucent dialogs) each keep their own distinct window and no 2nd independent main session is ever spawned that could collide:
   - W-owmc:52 `static std::atomic<int32_t> g_fgMainSession{-1};`
   - W-owmc:247-277 **"2026-06-05 ROBUST: pick the most-recent existing MAIN window as the parent … Fall back to the highest-sessionId main if the tracked fg session is gone"** (`g_fgMainSession.load()` then scan `sessions_`).
   - W-owmc:278-283 `asSubWindow → ohType = WINDOW_TYPE_APP_SUB_WINDOW` + `SetParentId(subParentWinId)` (W-owmc:371-373).
   - W-owmc:550 `if (!asSubWindow) g_fgMainSession.store(sessionId);` and W-owmc:786 `showWindow` re-stamps fg on the main window.
3. **`getOhNativeWindow` NEVER reuses a foreign window**: unknown session → `nullptr`, full stop.
   - W-owmc:994-1000 `if (it == sessions_.end()) { LOGE("getOhNativeWindow: unknown sessionId=%d"); return nullptr; }`
4. **The exported C wrapper is a pure pass-through — no process-global fallback**:
   - W-owmc:824-827 `void* oh_wm_get_native_window(int32_t sessionId){ return getInstance().getOhNativeWindow(sessionId); }` (no `last_session` / env fallback).

### A.2 route-A (target) — what it does differently

1. **Same distinct-RSSurfaceNode-per-session invariant is present** (32df matches Westlake here):
   - A-owmc:458-461 `RSSurfaceNode::Create(... APP_WINDOW_NODE, isWindow=true)` per call; A-owmc:604-634 `sessions_[sessionId] = entry`.
   - A-owmc:1444-1451 `getOhNativeWindow` unknown → `LOGE("unknown sessionId=%d"); return nullptr;` (matches W-owmc:994-1000).
   - A-owmc:1452-1453 caches `it->second.ohNativeWindow` so repeat calls on the SAME session return the SAME pointer (correct).
   - A-shim:174-193 `sc_to_oh_native_window`: unknown session → `return 0`. **The old `lastSessionId` reuse fallback is already gutted** (`lastSessionId` is a dead `=0` vestige at A-shim:177). This is the 32df "graphics-session-sync" fix: the 2nd session no longer silently borrows session 203's window at the shim.
2. **GAP 1 — the exported wrapper still has a process-global env fallback Westlake does not have:**
   - A-owmc:86-126 introduces `WESTLAKE_WINDOW_SESSION_ID_V1` / `WESTLAKE_NATIVE_WINDOW_PTR_V1` env stamp (`publishProcessWindowTarget` / `readProcessWindowTarget`), stamped eagerly at A-owmc:657-664.
   - A-owmc:1015-1019 `oh_wm_get_native_window` = `local != nullptr ? local : readProcessWindowTarget(sessionId);` — an env-global window handout. It is session-guarded (A-owmc:117 `if (readProcessWindowSession() != sessionId) return nullptr;`), so it does **not** currently mis-serve 204, but it is a residual reuse surface that has no Westlake counterpart.
3. **GAP 2 — no `g_fgMainSession` / no most-recent-MAIN SUB_WINDOW routing.** route-A `createSession` (A-owmc:357-664) builds every window as an independent APP_MAIN_WINDOW; there is no fg tracking and no dialog/2nd-activity re-parenting. `grep g_fgMainSession A-owmc` = 0 hits.
4. **route-A's actual 2nd-window guard lives on the Java side, by a different mechanism** — a per-session **persistent SurfaceControl** so ViewRootImpl sees `isSameSurfaceControl()==true` → `BBQ.update()` instead of destroy+recreate → **"the hwui RenderThread keeps one EGLSurface and does NOT re-run eglCreateWindowSurface on an already-bound window (the same-process SecondActivity 2nd-window abort)"**:
   - A-java:107-115 `Map<Integer, SurfaceControl> mSurfaceControlMap` (verbatim rationale in that comment block).
   - A-shim:501-503 `BBQ.update`: on a real session change it drops the cached window (`if (b->sessionId != sessionId) b->ohNativeWindow = nullptr;`) and re-resolves; A-shim:516-536 routes SurfaceView BBQs to a dedicated child node (`oh_rs_get_child_surface_window`) so a SurfaceView never shares the main producer.

### A.3 Copy-patch (A)

- **A-PATCH-1 (safe, verbatim-shaped): drop the env fallback in the exported wrapper.** Change A-owmc:1015-1019 to match W-owmc:824-827 — return only `getInstance().getOhNativeWindow(sessionId)`, deleting the `: readProcessWindowTarget(sessionId)` tail (and, if it becomes unused, the `publishProcessWindowTarget` call at A-owmc:657-664). Rationale/source-of-truth citation for cx-t0: **W-owmc:824-827 "pure pass-through, no last-session/env fallback."** This removes the only path by which one process-global pointer could be handed for a session other than the one that created it.
- **A-PATCH-2 (NEEDS-ADAPTATION — do NOT port verbatim): the `g_fgMainSession` + most-recent-MAIN SUB_WINDOW routing.** Westlake's C++ re-parenting (W-owmc:52 / 247-283 / 550 / 786, marker **"2026-06-05 ROBUST"**) is its structural answer to "no 2nd independent main window." route-A already answers the same failure at a different layer (A-java:107-115 persistent-SC + A-shim:501-503 re-resolve), and its render surface is a self-drawing child + XCOM hardware layer (A-owmc:1284-1411, 1470-1500), not a legacy WMS sub-window. Porting Westlake's sub-window path on top risks double-owning the surface. **Recommendation: keep route-A's Java persistent-SC as the primary A-fix; verify (not copy) that it is wired for every non-VISIBLE→VISIBLE edge (A-java:117-128 `mLastViewVis`).**

---

## Mechanism B — `eglCreateWindowSurface` lifecycle / retry (hwui hijack)

### B.1 Westlake (correct)

- **W-hwui (deploy, the proven G3.2):** unwrap ANW shim → real create → on `EGL_NO_SURFACE`, **bounded readiness retry**:
  - W-hwui:716-741 hijack + real create; W-hwui:754-765 **`[G3.2-EGL-RETRY 2026-06-01]` `for (int r=0; r<50 && surface==EGL_NO_SURFACE; r++){ usleep(20*1000); surface = real_create(...); }`** (1 s budget; the producer/RS surface is "not reliably ready at first bind").
  - Westlake has **no** `eglDestroySurface` hijack and never destroys-then-recreates on the same window — the readiness race is solved by waiting, not by re-allocating.
- **W-hwui2 (sibling):** before/within retry it **re-asserts SET_FORMAT(12=RGBA_8888)+SET_USAGE(HW_RENDER)** on the OH NativeWindow (W-hwui2:761-770), then a bounded `attempt<3` retry that re-applies format/usage each round (W-hwui2:775-787). Rationale: a fresh 2nd/new surface hits create with format UNSET → EGL_NO_SURFACE.

### B.2 route-A (target)

- A-hwui:737-812 hijack + real create (A-hwui:771-772). On `EGL_NO_SURFACE` it does a **single colorspace-strip retry** (`#r17h`, 2026-09-30): if `attrib_list != nullptr`, strip `EGL_GL_COLORSPACE_KHR`/HDR-metadata attrs and retry once (A-hwui:774-801). **There is no bounded readiness (usleep) retry loop.**
- route-A **adds** an `eglDestroySurface` hijack + surface-owner map that Westlake lacks: A-hwui:668/674/676-678 (`g_egl_surface_owner`), inserted at A-hwui:802-806, erased at A-hwui:814-824. It does **not** eglDestroySurface-before-recreate on the same window.
- route-A does **not** re-assert SET_FORMAT/SET_USAGE inside the hijack (it applies `SET_BUFFER_GEOMETRY` earlier in `getOhNativeWindow`, A-owmc:1559-1563; format for the hwui window relies on the OH default).

### B.3 Copy-patch (B)

- **B-PATCH-1 (primary, directly copyable): add Westlake's G3.2 bounded retry AFTER route-A's colorspace-strip attempt.** In A-hwui, after the colorspace-strip block (A-hwui:801) and before the owner-map insert (A-hwui:802), when `surface == EGL_NO_SURFACE`, insert the loop from **W-hwui:754-765 `[G3.2-EGL-RETRY 2026-06-01]`**: `for (int r=0; r<50 && surface==EGL_NO_SURFACE; r++){ usleep(20*1000); surface = g_real_eglCreateWindowSurface_fn(dpy, config, actualWindow, <last-good attribs>); }`. Needs `#include <unistd.h>` (already present in W-hwui:72). This converts the readiness-race abort (surface not ready at first bind for a 2nd-activity window) into a reliable success, which is exactly the residual failure the colorspace-strip does not cover.
- **B-PATCH-2 (optional, from W-hwui2): re-assert SET_FORMAT(12)+SET_USAGE on `actualWindow` before the real create and on each retry round** (source: W-hwui2:761-770 / 780-785). Guards a freshly-handed 2nd/new window whose format is UNSET. Adapt to route-A by resolving `OH_NativeWindow_NativeWindowHandleOpt` (already forward-declared A-owmc:69) or its dlsym'd equivalent inside the hijack.
- **Keep route-A's `eglDestroySurface` hijack + owner map (A-hwui:668-824) as-is** — it is a route-A improvement with no Westlake source to copy from; do not delete it.

---

## Headline for cx-t0 (fold into N1)

**N1 = two moves.** (B, primary) Port Westlake's **G3.2 bounded `eglCreateWindowSurface` retry (50×20 ms, `[G3.2-EGL-RETRY 2026-06-01]`, W-hwui:754-765)** into route-A's hijack, chained AFTER the existing `#r17h` colorspace-strip attempt (A-hwui:774-801) — this closes the readiness-race half of the double-bind exit134. (A, secondary) Delete the `readProcessWindowTarget` env fallback from `oh_wm_get_native_window` (A-owmc:1015-1019) so route-A exactly matches Westlake's pure pass-through (W-owmc:824-827) and can never hand a foreign session's window. Optionally add the SET_FORMAT/USAGE re-assert (W-hwui2:761-770). **Do NOT port `g_fgMainSession`/SUB_WINDOW routing** — route-A already guards the 2nd window via Java `mSurfaceControlMap` (A-java:107-115).

## Can't-copy / needs-adaptation
1. **`g_fgMainSession` + most-recent-MAIN SUB_WINDOW re-parenting** (W-owmc:52/247-283/550/786): Westlake legacy-WMS sub-window model vs route-A self-drawing-child + XCOM (A-owmc:1284-1411) and Java persistent-SC (A-java:107-115). Different architecture — verify route-A's Java guard, don't copy the C++ routing.
2. **`eglDestroySurface` hijack / surface-owner map**: exists only in route-A (A-hwui:668-824); nothing to copy from Westlake — keep it.
3. **Eager `getOhNativeWindow` + env publish at createSession** (A-owmc:657-664) has no Westlake equivalent (Westlake resolves lazily on BBQ demand). If A-PATCH-1 removes the env fallback, the eager publish becomes dead and may be dropped, but it is harmless to leave.
4. **Colorspace-strip retry (`#r17h`, A-hwui:774-801)** has no Westlake equivalent (Westlake's own surface adapter passes `nullptr` attribs — A-hwui:766-767 cites `oh_egl_surface_adapter.cpp:237`); keep it and chain G3.2 after it, not instead of it.
