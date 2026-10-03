# M2 A0 probe, runtime-side entry: load the probe through the runtime's own `libwestlake_html_compat.so` load point (the honest place NWeb loads from). Plan for outer approval — no build, no board yet

#90, offline plan. Windows 1–3 (`2026-10-03-m2-a0-probe`) established: F0 (no app data dirs, fixed), then F1 twice —
an app-code `dlopen` cannot reach the OH platformsdk namespace, because our app native loader (ANL) gives each app its
own sealed linker namespace (`caller ns: westlake.anl.app.<pid>.2 have no permission`). Route a loads NWeb from the
**runtime/bridge**, not from app code, so the faithful A0 must load from there too. This is the plan for that; it needs
outer approval before any build or board window.

## Why this is the honest entry, not a workaround

The point is not to bypass the app boundary (window 3 proved that is the wrong layer, and the outer ruled it out). It is
to run the probe from **the same place route a's real WebViewProvider will call NWeb from**: the runtime's own native
namespace, which already has `/system/lib64/platformsdk` in its search path (the directory holding
`libarkweb_core_loader.z.so`, NWebHelper/NWebAdapterHelper).

## The load point (`evidence/load-points.txt`, `evidence/open-site-scan-runtime-bridge.txt`)

`open_site_scan.py` over the deployed U13 runtime (18763dd4) and bridge (84695d62): the only fixed-path loads that go
through the runtime CL namespace are the three in `B7BindFixes.loadWestlakeNativeLibs`, run during every app's bind:

| path | state on board |
|---|---|
| `/system/android/lib64/libwestlake_jni_gapfill.so` | present, `[B8-NATIVE] loaded` |
| `/system/android/lib64/liboh_tls_boundary.so` | present, `[B8-NATIVE] loaded` |
| **`/system/android/lib64/libwestlake_html_compat.so`** | **absent on every board** → `[B8-NATIVE] System.load … failed` |

- The namespace these resolve in is created just before, `[B8-NATIVE] native namespace created for runtime CL
  (search=/system/android/lib64:/system/lib64/platformsdk:/system/lib64/chipset-sdk:/system/lib64/chipset-sdk-sp)` — it
  **includes platformsdk**, unlike the sealed app namespace F1 hit.
- The `html_compat` failure is only a missing file: ANL's `path_is_in_app_domain` runs `realpath(path)` first, which
  fails for an absent file and yields the "outside app domain" text. gapfill and tls_boundary, same directory, load
  fine — so `/system/android/lib64` is a permitted path; the only thing wrong with html_compat is that nothing is there.

**Nothing consumes html_compat on success.** It is named only at the `B7BindFixes` load site and in the self-contained
pure-Java `HtmlCompatFallback.fromHtmlCompat` (no JNI into the `.so`). No deployed `.so` strings `html_compat`; no symbol
is resolved from the returned handle; `loadLib` swallows the result. So placing a different `.so` at that path changes
nothing for any process except that its `JNI_OnLoad` runs.

## Effect on other processes, and how the probe stays inert for them

The load point fires in **every** appspawn-x child during bind. The probe must do nothing in any process but
`org.westlake.a0probe`:

- The probe `.so` gets a **`JNI_OnLoad`** whose first action reads the process name (`/proc/self/cmdline`). If it is not
  exactly `org.westlake.a0probe`, it returns `JNI_VERSION_1_6` immediately — no thread, no `dlopen`, no NWeb, no log
  beyond one line. This is the same process-name gate the outer specified.
- In `org.westlake.a0probe` it runs the existing probe body (ApplicationContext → NWebHelper → CreateNWeb → load → frame
  sampling), now on the runtime CL namespace that can see platformsdk.
- During the window the file exists, so **every** app that binds loads a tiny guard that returns in microseconds. That is
  the one cost; it is bounded to the window and reverted at the end. The U13 unified state is a system image, so the
  window is a short overlay: nothing on the boards' persistent state changes.

## The change (no frozen file rebuilt)

- **Reuse the probe**, rebuilt as `libwestlake_html_compat.so` with a `JNI_OnLoad` front end (same `a0probe.cpp` body +
  the process-name gate; `a0shim.c` is dropped — no App activity, no `System.loadLibrary`). Built on hw248 with the
  frozen clang, linked `--no-undefined` against the board libraries, two builds byte-identical, as before.
- **No APK.** The probe is driven entirely by the runtime's existing load during the bind of a throwaway launch of a
  bundle whose only purpose is to be named `org.westlake.a0probe`. The bundle is the same tiny signed APK from
  `2026-10-03-m2-a0-probe` with its native libs removed (it only needs to install and launch so a process by that name
  binds). Alternatively, no bundle at all and the gate matches any process — rejected: that would run the probe in a
  system app. The named throwaway bundle keeps it to one process.
- **No runtime/bridge/BCP/JAR edit.** `B7BindFixes` already loads this path; we only supply the file it looks for.

## Short-window overlay and rollback

1. LOCK; record `runtime-fingerprint` (must be `821de739cf81`, the U13 unified state) — note this probe file is **not**
   on the fingerprint path (`FINGERPRINT_PATHS` lists `/system/android/lib64/*.so`, so a bind-mount over a **non-existent**
   name does change the set; see step 6). 
2. Install the named throwaway bundle (`prepare_sandbox` as in window 2).
3. **Bind-mount** the probe `.so` onto `/system/android/lib64/libwestlake_html_compat.so` (the file is absent, so the
   mount adds it without hiding anything; `mount --bind` over a created empty file, or an overlay — exact mechanism in
   the board script, read-only-checked first).
4. Launch the bundle; its bind runs `loadWestlakeNativeLibs` → `System.load(libwestlake_html_compat.so)` → the probe's
   `JNI_OnLoad` → the probe. Capture `[A0]` lines and a screenshot.
5. Other processes launched in the window load the guard and return; confirm no `[A0]` lines from any other pid.
6. **Rollback:** unmount the bind; remove the created empty file so the path is absent again; uninstall the bundle and
   its dirs; `param` reset; kill only the bundle-uid processes. Then record `runtime-fingerprint` again — it must be back
   to `821de739cf81` **with the same file count** (the html_compat name absent again). If the count or hash differs, keep
   the lock and post. (The after-lock record is taken before the mount, so both ends are the clean unified state.)

## Prediction / criteria

Same as `2026-10-03-m2-a0-probe` §Criteria, with the namespace question now answered by the first log line:
- **PASS:** `[A0] RESULT PASS` — a frame whose centre pixel is `#12ab34`, process alive. Settles that NWeb is reachable
  and renders from the runtime namespace, i.e. route a's loading model works.
- **F3/F4/F5/F6** now mean the engine/init/create/renderer, not the loader — the loader question is resolved by this
  entry. F6 (no frames) → the renderer-spawn fallback (single-process mode 1).
- A guard line in a non-probe process that is anything but the immediate return = bug; the window is abandoned and rolled
  back.

## What needs outer approval

1. The entry: supplying `/system/android/lib64/libwestlake_html_compat.so` via a window-only bind-mount (the runtime
   already loads this path; no frozen file is modified).
2. Running a guard `JNI_OnLoad` in every process that binds during the window (bounded, returns immediately for
   non-probe processes).
3. The fingerprint handling in step 1/6 (the html_compat name is absent in the unified state, so the mount adds one file
   to `/system/android/lib64/*.so`; both the after-lock and before-unlock records are of the clean state with the name
   absent).

Nothing is built or deployed until this is approved. On approval: build the probe as `libwestlake_html_compat.so`
(×2 identical), extend `board/run_a0.sh` with the bind-mount + its rollback, and request a window.

## Files

- `evidence/load-points.txt`: the three load points, the namespace line, the html_compat failure, and the
  no-consumer check.
- `evidence/open-site-scan-runtime-bridge.txt`: full `open_site_scan.py` output for runtime 18763dd4 + bridge 84695d62.
- `results.json`.
