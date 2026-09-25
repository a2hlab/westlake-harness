# A real Bionic app process on stock DAYU600 / OH 6.1: what hanbin changed, what it would take here

#35 found that hanbin gets Toutiao past `libmetasec_ml.so`, which we cannot, by running the app process on **real Bionic libc and linker** instead of OH musl. Board entry #37 asks four things:
- exactly what hanbin changed;
- whether each change is possible on our stock DAYU600 / arm64 / OH 6.1;
- what it costs in stages, and which steps cannot be undone;
- whether we can swap only the app process's libc and linker and keep westlake's adapter layer.

This is read-only research: no board, no device, hanbin untouched. Lines relied on are quoted verbatim in `evidence.txt`. `results.json` holds the same content in machine-readable form.

## What it settles

- **Switching the app process to Bionic does not require writing the system partition.**
  - hanbin's 14 overwritten OH service libraries are mostly general APK integration (AMS routing, `.apk` install through BMS, Activity stacks in missions, dialog re-parenting) or leftover debug probes.
  - The Bionic-specific system changes are small: SELinux types for an Android property area plus `setpcap`, `file_contexts` labels, and the spawner's socket name.
  - hanbin's own PoC found the Bionic interpreter and libraries map "零 avc, 不需要 sepolicy patch" (`app_fwk_bionic_design_v2.html:474`).
  - westlake already starts `appspawn-x` from the root hdc shell out of `/data/local/tmp` and forks the app from it (`probe_source_app.py:521-537`). A Bionic `appspawn-x` whose interpreter also sits in `/data/local/tmp` fits that model unchanged. One board exec confirms it.
- **What it does require is rebuilding everything that runs in the app process.** A process has one thread and TLS model, so this is not a drop-in libc swap.
  - Of our 57 runtime libraries, 47 depend only on libc and libc++ and each other; for them it is a mechanical AOSP-native rebuild.
  - The other 10 talk to OH through 42 of the 47 hash-gated firmware libraries plus 5 OH NDK libraries; `liboh_adapter_bridge.so` alone needs 34 of them (recounted from `DT_NEEDED`). Those OH client libraries must also exist in a Bionic-compatible form.
  - The Mali-G57 driver (`/vendor/lib64/chipsetsdk/libGLES_mali.z.so`, the only vendor blob) stays a musl binary. It needs a musl-compatibility island like hanbin's `libmc`.
- **Two inputs are missing locally.**
  - An arm64 Android Bionic: no Soong tree and no Android 15 arm64 runtime libraries locally.
  - OH 6.1 client source: only 13,414 headers locally. hanbin ported OH master `weekly_20260302`; its memory records that as sdk 6.1.1.33, and its board runs 7.0.0.18. That is not the 6.1.0.31 release on our boards.
  - Neither blocks the minimal test below.
- **The board allows more than we have used.**
  - The hdc shell is root (`u:r:su:s0`).
  - SELinux enforces, but permissive has been used for real runs (`burgerking-blind/README.md:55-58`).
  - `/`, `/vendor` and `/sys_prod` are read-only ext4 on `by-name` partitions, with no device-mapper device in 54 mount lines.
  - A sibling project on the same D600 / OH 6.1 ran `mount -o rw,remount /` and wrote `/system/android/…` (`01.OH61AOSP16/docs/errors/appspawn-x-v2sig-wall-rootcause.md:204-206`).
  - So a hanbin-style system install is probably possible, but it is not needed and carries the real brick risks listed below.
- **An arm64 Bionic we can test with is already in the lab.**
  - HANDOFF.md:7 says one of the four D600s is flashed with Android as a same-hardware control.
  - The Android phone used for #26, `N100CU025C18D000128`, is a UNISOC `uis7885_2h10_native` running Android 16 userdebug with `su`. Bridge's notes record the OH D600 as `hardware=uis7885`, and D600 is the same SoC (UMS9620).
  - Its `/apex/com.android.runtime` (linker64, libc, libm, libdl) and `/apex/com.android.art` (libart, `dalvikvm64`, boot image) can run the minimal test with no build at all.
- **The minimal path to "metasec under real Bionic on our board" is a headless PoC (T0), 3–5 days, with nothing irreversible.** Running Toutiao itself on a Bionic westlake is T1, 6–10 weeks. Full UI is T2, adding 2–3 months. That matches hanbin's own estimate of 4–6 person-months (`app_fwk_bionic_design_v2.html:431`).

## 1. What hanbin changed (acceptance 1)

**Where Bionic and ART come from.**
- The source is AOSP `android-14.0.0_r1` (`fetch_missing_aosp_projects.sh:57`), built with **Soong** (`build_aosp_lib.sh:260`, lunch target `oh_adapter-userdebug`), arm32 only.
- Libraries built: `linker libc libm libdl libc++ libstdc++`. ART is built from the same tree, and the boot image is built on the host with dex2oat.
- Bionic carries four patches:
  - one to the linker, pointing its configuration and default search paths at `/system/android/{etc,lib,lib/oh-kit}`;
  - three to the property-area code.
- A fifth patch, `pthread_create.cpp.patch` (the 2 MiB stack floor mentioned in #35), is in the tree but not in their apply script.

**The zygote and `PT_INTERP`.**
- The zygote is AOSP `app_process`. After linking, `patchelf` rewrites its interpreter to `/system/android/bin/linker`, because Soong always forces `/system/bin/linker` (`compile_zygote_x.sh:53-57, 183`).
- `zygote.cfg`: uid root, `secon u:r:appspawn:s0`, on demand, with init-owned `Zygote` and `UsapPoolPrimary` sockets.
- Children run `SetSelfTokenID` and `HapDomainSetcontext`, which moves them into `normal_hap`.
- The property area stays at `/dev/__properties__`.

**OH client libraries rebuilt for Bionic ("oh-kit").**
- 30 `liboh_kit_*.so` libraries, from about 2.15 M lines of unmodified OH master `weekly_20260302` source plus 92 patch files.
- Built with AOSP clang for `armv7a-linux-androideabi34`.
- Their layers: L0 `c_utils/ipc_single/samgr_proxy/hilog/begetutil`; L1 surface, sync fence, native window, vsync; L2 a render-service client subset; L3 window, ability, input, common events, datashare, bundle and network clients.

**The Mali blob.**
- In an isolated `mali` namespace, a `libmc.so` impersonates `libc.so`. It exports 328 C libc symbols with musl calling conventions and forwards them to Bionic.
- The OH musl `libc++.so` and the vendor blob then load on top of it.
- Their own configuration labels the blob's single-instance loading of `libsurface`/`libhilog` "UNVERIFIED HYPOTHESIS" (`ld.config.txt:77`).

**Files overwritten on the device** (`deploy/deploy_all_init.sh:66-76`), and why:

| Files | Class | Why |
|---|---|---|
| `policy.31`, `file_contexts` | **needed for Bionic** | property-area types, fork capability drop via `setpcap`, ashmem, zygote/linker labels |
| `libappspawn_client.z.so` | general; the socket name is Bionic-era | AMS → zygote routing; socket name `"Zygote"` |
| `system-sandbox.json`, dexopt part of `libinstalls` | Bionic-era dexopt | let installd run AOSP `dex2oat` |
| `libappms`, `libbms`, `libinstalls`, `libappexecfwk_common`, `libabilityms`, `libmission_list`, `libwms` + `libwmutil`, `librender_service_base` | general APK integration, would be needed with any runtime | `.apk` install and launch through OH services, Activity stacks, dialogs; the render-service change trusts the client-sent pid ("SECURITY-RELAXING") |
| `librender_service`, `libskia_canvaskit`, `libsurface` (shadow copy) | debug leftovers | log probes only |
| `libscene_session{,_manager}` | unexplained | no source patch; the device runs the legacy window manager |

Policy is rebuilt on their build server, loaded live through `/sys/fs/selinux/load`, then written to `/system` (`deploy_update.sh:1887-1925`). Labels on `/system/android/bin` are set by hand with `chcon`, and `restorecon` must not be run on it.

**Timeline and size.**
- Decided 2026-07-31; five PoCs passed 2026-08-03; first UI 08-10; Toutiao main UI 08-14; still going on 09-18.
- Code: `framework/zygote-x` 2,134 lines; `framework/gpu-mali` 3,647; `aosp_patches` 107 files, 5,652 lines; `ohos_patches` 69 files, 4,202 lines; oh-kit patches 12,198 lines.
- hanbin started from a Soong AOSP tree and full OH source. That is why the two weeks from PoC to Toutiao UI are not a guide for us.

**Their five PoCs, all passed 2026-08-03** (`app_fwk_bionic_design_v2.html:451-474`):
- a pure static Bionic process completes authenticated OH IPC (binder, samgr, a WMS reply);
- a render-service client subset compiles against Bionic headers with zero skia symbols;
- the input-client subset cuts cleanly;
- the Bionic zygote starts under init in `appspawn:s0` with zero AVC;
- a Bionic crash on the OH kernel dies cleanly.

## 2. Each hanbin change on our platform (acceptance 1)

| hanbin step | On stock DAYU600 / OH 6.1 | Verdict |
|---|---|---|
| Bionic interpreter via `patchelf`, zygote exec | Our parent is exec'd by the root hdc shell from `/data/local/tmp`; the interpreter can live there too (same label, same domain as the `appspawn-x` binary already executed) | **feasible**, verify with one exec |
| App process in `normal_hap` mapping Bionic libraries | westlake children already map their libraries from `/data/local/tmp` in `normal_hap` | **feasible** |
| Android property area at `/dev/__properties__` + policy types | We need no device node: patch Bionic's property path to a file under `/data/local/tmp`, or run without properties (T0 finds out whether ART and metasec tolerate that) | **verify** in T0 |
| arm64 Bionic + ART runtime | not local. For T0: prebuilt from the same-SoC Android D600 (Android 16). For T1+: build against the NDK sysroot plus AOSP private headers (`android-source/bionic-android15` is local) and run on those prebuilt libraries, or set up Soong | T0 **feasible**; T1 needs a toolchain decision |
| oh-kit (OH client libraries for Bionic) | OH 6.1.0.31 source not local; hanbin's is master `weekly_20260302`, and wire formats must match our stock services | **blocked on source.** Alternative to verify: load the **stock** OH 6.1 client libraries in a `libmc`-style musl island (what hanbin did for Mali only), with a C-ABI seam inside our own 10 bridge libraries |
| Mali blob via `libmc` island | `libGLES_mali.z.so` (Mali-G57) with more dependencies than hanbin's G52 (`libgralloctypes`, `libmapper4.0`, `libhidlbase`, `libnativewindow`, display-buffer HDI) | **verify**: symbol census like hanbin's (their blob: 404 UND in five buckets) |
| Overwrite OH service libraries | not needed: our host-HAP launch does not go through AMS/BMS `.apk` routing | **not needed**; if ever wanted: needs `remount` (likely possible) and OH 6.1 source (blocked) |
| Persist a SELinux policy | policy sources for 6.1 not local; live-load plus persist is how hanbin bricked a board | **not needed** for T0–T2; `setenforce 0` stays a debugging aid only |
| System partition writable | root shell, ext4, no dm device seen; sibling project remounted `/` rw on this board type | **likely**, unverified here; unnecessary for T0–T2 |

## 3. Stages, effort, and what cannot be undone (acceptances 2 and 3)

**T0: does metasec run under real Bionic on our board? (3–5 days, fully reversible)**
1. Copy from the Android D600:
   - `/apex/com.android.runtime/{bin/linker64, lib64/bionic/*}`;
   - `/apex/com.android.art` (`dalvikvm64`, `libart*`, boot jars and image);
   - the few `/system/lib64` dependencies (`libc++`, `liblog`, `libbase`, …).
   Stage them under `/data/local/tmp` on an OH D600.
2. `patchelf --set-interpreter` on `dalvikvm64` to point at the staged `linker64`, and provide a small `ld.config.txt` (or `LD_LIBRARY_PATH`) plus `ANDROID_ROOT`, `ANDROID_ART_ROOT` and `ANDROID_I18N_ROOT`.
3. Run a test dex that `System.loadLibrary("metasec_ml")` (the APK's own arm64 library) and exercises its JNI entry points. Watch for:
   - the `a-4` thread;
   - `vfork` (0x2043b8 needs a Bionic `pthread_internal_t` at TP+8, which real Bionic provides);
   - whether metasec's own threads live past the 6–7 s at which ours die.
4. Answer in passing:
   - Bionic on the OH 6.1 kernel under the shell and `normal_hap` domains;
   - behaviour with no property area;
   - logging to stderr.

Nothing here touches the system partition. Undo is `rm -rf` of the staging directory.

**T1: westlake's runtime on Bionic, headless (6–10 weeks, reversible)**
- A Bionic `appspawn-x`, exec'd as today but with the Bionic interpreter. The fork model is unchanged.
- ART and the 47 libc-only runtime libraries rebuilt for `aarch64-linux-android` (NDK libc++ instead of OH libc++).
- The 10 OH-facing bridge libraries on one of two routes:
  - (a) an oh-kit port of the L0 clients (`c_utils`, `ipc_single`, `samgr_proxy`, `hilog`, `begetutil`) from OH 6.1 source, once obtained;
  - (b) stock 6.1 client libraries in a musl island with a C seam, which needs a `libmc`-style layer and a PoC like hanbin's PoC-3.
- Exit criterion: Toutiao's `Application.onCreate` and SDK initialisation, including metasec, complete with real OH IPC and no window. That is exactly where today's 7 s `a-4` crash sits (#32).

**T2: full UI (another 2–3 months, reversible)**
- Surface, vsync and render-service client (L1/L2), input, window and ability clients (L3).
- hwui on Bionic with the Mali-G57 blob in the island.
- WebView on real Bionic: our WebView Bionic shim goes away.
- DFX: a self-installed crash handler, as hanbin's PoC-5 did.

**T3: hanbin-style system install (not recommended; needs OH 6.1 source)**
- Overwrite service libraries, add a zygote init service, persist a policy.
- The only reason to do it is OH-native launcher and install integration, which westlake does not use.

**Steps that cannot be undone without a reflash** (all belong to T3; none to T0–T2):
- **A partially written `policy.31`.** hanbin's board went dead on 2026-09-08: stuck at the OH logo, hdcd never started (`deploy_all_init.sh:1298-1306`).
- **init `.cfg`:**
  - `critical` on a crashing service gives an endless reboot loop;
  - `critical:[0]` gives a respawn storm;
  - `bootevents` with `disabled:1` means the desktop never appears.
- **Overwriting boot-critical OH service libraries** (foundation, render service): boot stops at the logo.
- **Namespace config and libnativeloader edits in `/system`.**

Recovery is reflashing the factory PAC with Unisoc UpgradeDownload on Windows. The OH 6.1 PAC is on another machine, not local. hanbin's rules for anyone doing T3:
- back up every file on the device before writing it;
- roll back only by copying the backup, never by a reverse edit;
- never write a boot-critical file in the same run as stopping services.

## 4. Can westlake keep its adapter layer? (acceptance 4)

**Kept:**
- the Java framework patches and adapters;
- the host-HAP launch and `/data/local/tmp` deployment;
- the build, stage and probe harness;
- the host-side boot image pipeline;
- the **source** of the native bridges.

**Rebuilt:**
- libc and linker;
- ART in its Bionic flavour;
- the C++ runtime (NDK libc++ instead of OH libc++);
- all 57 runtime libraries;
- the OH client layer (oh-kit port, or a musl island for the stock libraries).

**Retired:** the musl-side compatibility layers that exist only because the app process is not Bionic:
- the Android-ABI namespace;
- `libwestlake_bionic`'s 27 exports;
- the WebView Bionic shim (sigaction, jmp_buf, stdio and property ABI translation);
- `wl_fastlibc`'s `getenv` special case;
- INIT_ARRAY cleanup;
- the sigchain special handler.

**Not needed:** hanbin's system-install model.

So the answer is in between. It is not "swap two files and keep everything": every native library in the process is rebuilt. But it is also not "adopt hanbin's model": no system writes, same launch path, and the Java adapter layer is unchanged.

## Method and limits

- Two read-only research passes ran in parallel: hanbin's changes, and westlake's in-process dependencies and board facts. I re-read the decisive lines myself; they are in `evidence.txt`. Those lines cover:
  - the overwrite list and `patchelf`;
  - the Soong lunch target and AOSP tag;
  - the `policy.31` brick;
  - the Mali "UNVERIFIED" note;
  - the design doc's PoC, estimate and boundary lines;
  - our mount line (0 dm devices in 54);
  - the permissive runs;
  - HANDOFF.md:7;
  - the sibling project's remount;
  - our launch chain;
  - the firmware list (47 libraries, one vendor blob).
- Not verified: that the phone used for #26 is the fourth D600, which is inferred from the matching SoC and HANDOFF; whether an interpreter under `/data/local/tmp` execs; whether Bionic runs without a property area; whether the root partition really remounts rw on our boards; and whether AVB is enforced.
- Effort figures are engineering estimates, not measurements.
- A related pointer: the Bridge project has TLS work that publishes the stack-guard word into new threads' TLS template (`01.OH61AOSP16/src/adapter/framework/native-compat/thread-template-publisher`, verified on the host only). It is relevant to #35's slot-level alternative, not to this report.

## Layout

| Path | What |
|---|---|
| `README.md` | this report |
| `results.json` | the same content in machine-readable form: changes, verdicts, stages, irreversible steps |
| `evidence.txt` | lines quoted verbatim with file:line (hanbin, westlake, board logs, sibling project) |
| `excerpt.py` | regenerates `evidence.txt` |
