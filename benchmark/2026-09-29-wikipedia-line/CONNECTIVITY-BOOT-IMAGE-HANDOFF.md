# R2 connectivity fix — boot-image segment rebuild handoff (for cx-t0)

Wikipedia's R1/R2 wall is now root-caused and the class-level fix is built and verified.
The remaining step is an **oat230 ARM64 boot-image rebuild** that swaps one BCP jar
(`adapter-mainline-stubs.jar`), which needs the v3a generation's host `dex2oat64`
(cx-t0 / hw248 domain). This doc is the complete recipe + inputs so cx-t0 can run it.

## Root cause (proven, decisive smali)

Board 5ea `adapter-mainline-stubs.jar` → `android.net.ConnectivityManager`:
- `getActiveNetwork()` = `const/4 v0,0x0; return-object v0` (returns **null** = offline)
- `getActiveNetworkInfo()` = returns null
- `registerDefaultNetworkCallback()` = `return-void` (empty — never delivers onAvailable)

Wikipedia `ConnectionStateMonitor` therefore decides offline → `MainActivity.onGoOffline`
→ `MainFragment.getCurrentFragment()` NPE (getClass on null) → `System.exit(1)`.
The stub is fully self-contained (zero getService/ServiceManager/binder calls), so no
runtime-JAR / projection / dynamic-proxy layer can reach it — the offline behaviour is a
compile-time constant AOT'd into `boot-adapter-mainline-stubs.oat` (oat version 230).

## The fix jar (built + verified, ready)

- **`mls-online.jar`** SHA256 `83c5ef21f68d22a03bcf0948a12d9ab3ca3166a84f29c8afde51dc088aa50215`
  (staged on 5ea at `/data/local/tmp/b11-mls-online-20260929/adapter-mainline-stubs.jar`;
  Mac scratch copy under this session's scratchpad `jars/mls-online.jar`).
- = board baseline `adapter-mainline-stubs.jar` (SHA `beb369a1173eec0ce6cb070487ea100e50e7f1612e0144bf2be273ca21d7db25`)
  with **only** `android/net/{ConnectivityManager, Network, NetworkInfo, NetworkCapabilities,
  NetworkRequest, LinkProperties}` (+ their inner classes) replaced by Westlake's online
  mainline-stub versions (`vm-copies/westlake-current/framework/mainline-stubs/java/android/net/*.java`,
  which report a single validated unmetered WiFi network and deliver onAvailable immediately).
- Build script: `build_mls_online.py` (baksmali-swap, verified only those classes changed).

## Why a bare bind-mount does NOT work (empirically confirmed)

`adapter-mainline-stubs` is AOT'd into the boot image (`boot-adapter-mainline-stubs.{art,oat,vdex}`).
Bind-mounting the new jar over `/system/android/framework/adapter-mainline-stubs.jar` and
launching Wikipedia: the child process never forks any app Java (no org.wikipedia child logs at
all) — ART rejects the jar↔boot-oat checksum mismatch at child init (cf. build_boot_image.sh [B-6]:
segment-index mismatch → ValidateOatFile → SIGABRT). Rolled back cleanly.
Options ① (append to BOOTCLASSPATH) and ② (getService dynamic proxy) are both dead
(no BOOTCLASSPATH append hook; the class is already in the image; the stub ignores services).

## The recipe (path A — boot-image rebuild, cx-t0 to run)

Source: `01.OH61AOSP16/real-work/src/adapter/build/inner/gen_boot_image.sh` (real-work = the
lineage that produced the board's route-A R155). Key facts:

- `DEX2OAT=$AOSP_ROOT/out/host/linux-x86/bin/dex2oat64` — **must be built first**
  (`cd $AOSP_ROOT && m dex2oat-host libsigchain-host libart-host -j16`) and must match the
  board's libart (B-5: libart/dex2oat/boot-image are co-built; no host dex2oat64 is currently
  staged on hw248 — the frozen `/opt/wl-src/.work/product-tls-generation/frozen/` is a
  cross toolchain + sources + sysroot only).
- BCP = 9 jars in the exact runtime order (B-6, = appspawn-x main.cpp:62 kBootClasspath):
  `core-oj core-libart core-icu4j okhttp bouncycastle apache-xml adapter-mainline-stubs framework oh-adapter-framework`.
  Substitute **`mls-online.jar` for `adapter-mainline-stubs.jar`** in the input set; keep the
  other 8 byte-identical to the board's current jars.
- Single-segment rebuild is NOT implemented (`--target=` is Phase-1-ignored); the image is
  regenerated atomically (all segments). That is fine as long as the other 8 inputs are the
  board's exact current jars so their segment content is unchanged.
- Output = the full boot image set (`boot*.{art,oat,vdex}`, all segments). **Deploy ALL of them
  together** to `/system/android/framework/arm64/` (per feedback_boot_image_full_27_deploy.md;
  the aggregate alone is insufficient).

## Deploy + verify (after cx-t0 produces the images — needs board restart; awaits user OK)

1. Bind-mount `mls-online.jar` over `adapter-mainline-stubs.jar` AND the new
   `boot-adapter-mainline-stubs.{art,oat,vdex}` (+ any aggregate boot files) over their
   `/system/android/framework/arm64/` targets. Keep baselines for rollback (`deploy_generation.sh`
   single-file mode / bind-mount + umount).
2. Restart appspawn-x so it reloads the boot image (RUNBOOK: on a hub board this may cascade to a
   reboot — do on 5ea only with user OK; keep rollback + expect possible physical re-plug).
3. Verify: new child sees `[WESTLAKE-418] ConnectivityManager.getActiveNetwork -> 100` in hilog,
   `onGoOffline` no longer fires, flow reaches `Intent -> Want InitialOnboardingActivity` +
   `createSession`/`CreateNodeAndSurface`, screenshot the welcome page for outer-ring sign-off.
4. Regression: HelloWorld / ZigZag still lit; else rollback the boot-image + jar bind-mounts.

## Parallel fallback (cc-t3)

cc-t3's tolerant `defaultUncaughtExceptionHandler` (item 5, in the runtime JAR at bind time) is a
separate lever: if it makes the main-thread `onGoOffline` NPE non-fatal, Wikipedia may survive to
onboarding even while offline — but a dead main looper may not render; the connectivity fix above
is the clean path (app genuinely online, no crash).
