# whitewin-diff v2: white-round dual-surface fate + source paths + fix draft (offline)

Dispatch (board ACK(97) 14:21:29): whitewin-diff v2. Boards untouched. Scripts use lab_paths/$HOME only.

## (a) White-round dual-surface fate

In white rounds the Activity creates **two** window surfaces (two `BBQ.create VRI[...]` calls ~50 ms apart, second ~0.5 s later). Each is a separate `OH_GfxShim::BBQ` object, each tries `getOhNativeWindow(sessionId)` for its own session. Example — wikipedia r2 (white):

```
L59305  getOhNativeWindow: SET_BUFFER_GEOMETRY 1200x1920 rc=0  sessionId=371   (2nd surface, Activity)
L59308  getOhNativeWindow: sessionId=371 -> AOSP-compat ANativeWindow=0000007F0FF08050  ✓ resolved
L66120  BBQ.create name=VRI[InitialOnboardingActivity]                          (1st surface, icon/onboarding)
L66124  getOhNativeWindow: unknown sessionId=370                                (1st surface looks up icon session 370)
L66125  BBQ.update: getOhNativeWindow(sessionId=370) returned null              ✗ icon window NOT resolvable
L66128  BBQ.getSurface: ohNativeWindow null (sessionId=370 not attached or BBQ.update not yet called) — empty Surface
L66376  BBQ.create name=VRI[DefaultIcon]                                       (2nd surface, the one that matters)
L66378  getOhNativeWindow: unknown sessionId=371                                (already consumed by 1st query? sessions_ miss)
L66379  [BBQ.update-stamp] SET_BUFFER_GEOMETRY shim=… oh=… rc=0                (last-session fallback fires)
L66380  BBQ.update: sessionId=371 → OHNativeWindow=0000007F0FF08050            ✓ rescued (last session)
L71578  getOhNativeWindow: unknown sessionId=371                                (re-lookup still fails — once-only)
L71579  [BBQ.update-stamp] SET_BUFFER_GEOMETRY … rc=0                          (fallback fires again)
L71580  BBQ.update: sessionId=371 → OHNativeWindow=0000007F0FF08050            ✓ rescued again
```

**Fate of the two surfaces in white rounds:**
- **1st surface (icon/onboarding, session 370):** `BBQ.create` fires, `getOhNativeWindow(370)` returns null (`unknown sessionId=370` — the once-only lookup already consumed that session's first resolution when the Activity's *second* surface queried its own session first, or the icon session was never rescued because the last-session fallback targets only the Activity). Its `BBQ.getSurface` returns **empty Surface** — nothing renders on it.
- **2nd surface (Activity/DefaultIcon, session 371):** the last-session fallback fires (`[BBQ.update-stamp] SET_BUFFER_GEOMETRY … rc=0`), `BBQ.update` resolves to a non-null `OHNativeWindow=0x…`. It gets an EGL surface (`eglCreateWindowSurface` succeeds — the same ANativeWindow shim is handed to hwui). But the visible foreground slot belongs to the **1st surface (icon)** which has no content, so the screen stays white. The Activity's frames go to the 2nd surface which is off-screen.

The critical difference from lit rounds: in lit rounds (e.g. wikipedia r1/r2b/r3), only **one** `getOhNativeWindow` query happens per session (icon ~0.6 s before Activity), and the Activity's surface goes to the foreground slot. In white rounds, two queries to the Activity session happen (~50 ms then ~0.5 s), indicating the Activity **created two window surfaces**; only the last one is rescued by the fallback, and the foreground slot is occupied by the first (empty) one.

## (b) Source paths

Search order 本机 → a2hlab → hw248. All three files found on 本机 (westlake-harness-bms-deploy, commit `a11565443`):

| File | Path | Commit | Role |
|---|---|---|---|
| `oh_window_manager_client.cpp` | `bms/src/adapter/framework/window/jni/oh_window_manager_client.cpp` | `a11565443` | `OHWindowManagerClient::getOhNativeWindow(sessionId)` — the once-only lookup (`unknown sessionId=N` at line 1449, `sessions_.find()` miss) |
| `oh_window_manager_client.h` | `bms/src/adapter/framework/window/jni/oh_window_manager_client.h` | `a11565443` | `sessions_` map declaration |
| `android_graphics_compat_shim.cpp` | `bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp` | (same tree) | compat shim's last-session fallback (`oh_wm_set_last_session_local` IPC at line 92) |

Not found on a2hlab or hw248 in a separate tree (same file is the one on 本机; hw248 has only build outputs of it, not a separate source copy).

## (c) Minimal fix draft

The root problem: `getOhNativeWindow(sessionId)` is a once-only lookup — after the first successful resolution the entry in `sessions_` is kept (the code at 1450-1452 returns the cached `it->second.ohNativeWindow`), so re-lookup should succeed. But `unknown sessionId` means `sessions_.find()` **misses** — the entry is not there. The icon session (370 in r2) was never inserted into `sessions_` at all (its `createSession` may have failed silently, or it was created on a different WMClient instance/copy of the bridge — consistent with the two-copies-of-the-bridge finding in 08:10:56). The Activity session's second surface (DefaultIcon, also session 371) hits `unknown sessionId=371` on its first query because session 371's `sessions_` entry was created and consumed by the first surface's query, and the second surface uses a different `OHWindowManagerClient::getInstance()` (second bridge copy) with an empty `sessions_` map.

**Minimal fix (single-site):** in `OHWindowManagerClient::getOhNativeWindow`, when `sessions_.find()` misses, do not return null immediately; instead fall back to the `set_last_session_local` session (the Activity), resolve it, and log a one-line activation marker. This makes the lookup tolerant of duplicate bridge copies / per-copy session maps.

```cpp
// oh_window_manager_client.cpp, in OHWindowManagerClient::getOhNativeWindow
auto it = sessions_.find(sessionId);
if (it == sessions_.end()) {
    int32_t lastSession = getLastSessionLocal();
    if (lastSession > 0) {
        auto lit = sessions_.find(lastSession);
        if (lit != sessions_.end()) {
            LOGI("getOhNativeWindow: sessionId=%d not found, falling back to last session=%d",
                 sessionId, lastSession);
            it = lit;
        }
    }
    if (it == sessions_.end()) {
        LOGE("getOhNativeWindow: unknown sessionId=%d", sessionId);
        return nullptr;
    }
}
```

**Activation log line (one line, grep-able):**
```
getOhNativeWindow: sessionId=370 not found, falling back to last session=371
```
When this line appears in a lit round, the fallback rescued a session whose own entry was missing — proving the fix works. In current U8 logs this line does not exist (fix not yet applied).

**Landing paths** — see `landing-paths.txt`.
