# Double-load of liboh_adapter_bridge.so and liboh_android_runtime.so (offline)

Dispatch (board ACK(80) 14:29:26): identify which namespace/load produced the second copy of each library. Boards untouched.

## Evidence from the probe (child-16749-maps.txt, 61b-cont smoke)

| Library | 1st address | 2nd address |
|---|---|---|
| `liboh_adapter_bridge.so` | `7ef9280000` (r-xp 7ef9338000) | `7f07700000` (r-xp 7f077b8000) |
| `liboh_android_runtime.so` | `7eea600000` (r-xp 7eea66c000) | `7ef9600000` (r-xp 7ef966c000) |

Both libraries are mapped **twice** in the same process, with complete r-x/r--/rw-p segment sets at two different addresses — two independent `dlopen` instances, hence two `OHWindowManagerClient::getInstance()` singletons (function-local static in `oh_window_manager_client.cpp:256`).

## Load sequence from the hilog (wikipedia r1, pid 10025)

```
L18642  [B34.1] JNI_OnLoad: oh_adapter_bridge entered                       ← 1st bridge load
L19452  [B8-NATIVE] native namespace created for runtime CL (search=/system/android/lib64:…)
L18888  [B32-J] J_after_initAdapterLayer                                   ← OHEnvironment.initialize() ran (Java)
L59031  resolve_oh_wm_funcs: get_native_window_fn=0000007EF92DF9E4
         dlerror='Library liboh_android_runtime.so is not already loaded'   ← compat shim's own load attempt (2nd runtime load)
```

### First load — `OHEnvironment.java:22` (`System.loadLibrary("oh_adapter_bridge")`)

- Source: `bms/src/adapter/framework/core/java/OHEnvironment.java:22`
- Triggered by `child_main.cpp:183` (`initAdapterLayer` → `OHEnvironment.initialize()` at line 183 comment "Step 6: Initialize adapter layer (OHEnvironment.initialize)")
- Runs inside the **runtime CL native namespace** created at L19452 (`[B8-NATIVE] native namespace created for runtime CL (search=/system/android/lib64:…)`). This namespace is created by ART's native-loader for the app's PathClassLoader and searches `/system/android/lib64:/system/lib64/platformsdk:/system/lib64/chipset-sdk:/system/lib64/chipset-sdk-sp`.
- Maps address: `7ef9280000` (bridge), `7eea600000` (runtime).
- This is the copy whose `JNI_OnLoad` fires at L18642.

### Second load — `child_main.cpp:224-226` (`dlopen("liboh_adapter_bridge.so", RTLD_NOW)`)

- Source: `bms/src/adapter/framework/appspawn-x/src/child_main.cpp:224-226`
- The `INPUT-RT-CL-CHILD` block (lines 196-230) first tries `dlopen(..., RTLD_NOLOAD | RTLD_NOW)`; if that returns null (the bridge is not already loaded in the **process default namespace**), it falls back to `dlopen(..., RTLD_NOW)` — loading the same file **again**, but this time into the process default namespace (the native-linker's own namespace, not the runtime CL namespace).
- Maps address: `7f07700000` (bridge), and `7ef9600000` for the runtime library loaded by `resolve_oh_wm_funcs` (compat shim at `android_graphics_compat_shim.cpp`) at L59031 (`dlerror='Library liboh_android_runtime.so is not already loaded'` — the compat shim's own `dlopen` attempt in the default namespace, loading runtime a second time).
- This is the copy whose `OHWindowManagerClient::getInstance()` has an **empty `sessions_` map** (its singleton was just created in the second bridge copy; createSession calls go to the first bridge copy in the runtime CL namespace).

### Why `unknown sessionId` happens

`createSession` (line 58522 in r1) goes through the **runtime CL namespace bridge** (`7ef9280000`) — that copy's `OHWindowManagerClient` singleton registers session 352. `getOhNativeWindow` (line 59033) goes through the **default-namespace bridge** (`7f07700000`) — that copy's singleton has an empty `sessions_` map, so `sessions_.find(352)` misses and it logs `unknown sessionId=352`. The compat shim's last-session fallback (`oh_wm_set_last_session_local` IPC) is called on the same second bridge copy, but that copy's WMClient has no session entries either.

## Call-site table

| Load # | Namespace | Trigger | Source file:line | Maps address |
|---|---|---|---|---|
| bridge 1st | runtime CL native namespace | `System.loadLibrary("oh_adapter_bridge")` from `OHEnvironment.initialize()` | `core/java/OHEnvironment.java:22` (Java) → `appspawn-x/src/child_main.cpp:183` (`initAdapterLayer`) | `7ef9280000` |
| runtime 1st | runtime CL native namespace | same as above (bridge's DT_NEEDED) | — | `7eea600000` |
| bridge 2nd | process default namespace | `dlopen("liboh_adapter_bridge.so", RTLD_NOW)` after `RTLD_NOLOAD` returned null | `appspawn-x/src/child_main.cpp:224-226` (`INPUT-RT-CL-CHILD` block) | `7f07700000` |
| runtime 2nd | process default namespace | compat shim's own `dlopen("liboh_android_runtime.so")` | `android-runtime/src/android_graphics_compat_shim.cpp` (in `resolve_oh_wm_funcs`, ~L92 area) | `7ef9600000` |

## Fix direction (for cx-t0's N10b/N11 window)

The `child_main.cpp:224-226` `INPUT-RT-CL-CHILD` dlopen must use the **already-loaded bridge in the runtime CL namespace** instead of loading a new copy into the default namespace. Two options (cx-t0 picks):

1. **Namespace-link the default namespace to the runtime CL namespace** for these two libraries (make them shared between namespaces, so `dlopen` in the default namespace returns the existing handle).
2. **Skip the `INPUT-RT-CL-CHILD` dlopen entirely** when the bridge is already loaded in the runtime CL namespace (detect via `dlopen(..., RTLD_NOLOAD)` succeeding, or by querying the runtime CL namespace handle through the Java side).

Acceptance per ACK(80) 14:29:45: probe child maps shows bridge/runtime each with exactly **1 load instance** (counted per master c2508ebdd), and no `unknown sessionId` in wikipedia/fd-noice hilog across 5 rounds.

The full hilog stays in the run directory ($WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-flaky-repeat/61b/r1/...); `hilog-excerpt.txt` here keeps the load-sequence lines with their original line numbers (grep -n of B8-NATIVE, INPUT-RT-CL-CHILD, JNI_OnLoad, createSession, unknown sessionId, not already loaded, the two library names).
