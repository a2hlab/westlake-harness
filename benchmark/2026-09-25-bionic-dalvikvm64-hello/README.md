# #43 — Direction-2 64-bit M2: AOSP14 arm64 ART on real Bionic runs Java

**Board entry:** `#43` in `.octos/OUTER_LOOP_REVIEW.md`
**Date:** 2026-09-25 · **Board:** 5cd1e3dd (shared with #42 by process mutex)
**Mode:** read-only extraction + on-board run under `/data/local/tmp/bionic43` only. No `/system` write, no remount, no reflash. `pidof com.ss.android.article.news` checked empty before every run; the test exits (not resident).

operator's decision: we only have 64-bit boards (DAYU600, OH 6.1.0.31; no 32-bit libs in `/system`; the Toutiao APK ships only arm64-v8a). hanbin's build is 32-bit rk3568 / OH 7.0 and cannot be used directly — **learn hanbin's method, build 64-bit ourselves.** M1 = #39 (Bionic PT_INTERP). **M2 (this):** without recompiling, take the official AOSP14 arm64 ART + boot image + BCP and run a Java hello via `dalvikvm64` on top of the #39 Bionic linker64/libc.

**Result: SUCCESS.** `dalvikvm64` prints the Java hello, exit 0, reproducible 3/3, with the **boot image loaded** (12 image components, 12 oat files, zero imageless fallback), zero avc.

```
bionic43 java hello ok
vm.name=Dalvik
vm.version=2.1.0
compute 6*7=42
```

---

## What was assembled (all read-only from the official AOSP14 image)

Source: `arm64-v8a-34_r04.zip` (build `UE1A.230829.036.A1`, API 34; the #39 download).

| piece | from | notes |
|---|---|---|
| `dalvikvm64`, `libart.so` + 20 ART libs, BCP jars | `com.android.art.capex` → `original_apex` → `apex_payload.img` | the ART runtime |
| `libicu*/libandroidicu`, `core-icu4j.jar`, `icudt72l.dat` | `com.android.i18n.apex` | ICU |
| boot image `boot*.{art,oat}` + real `boot*.vdex` | `/system/framework/arm64/*.{art,oat}` + `/system/framework/*.vdex` | 12 components |
| `linker64`, `libc/libdl/libm` | `com.android.runtime` apex (#39) | real Bionic |
| `libstatssocket.so` | `com.android.os.statsd.apex` | libart dep |
| `tzdata` | `com.android.tzdata.apex` | TimeZone |

The full runtime library closure (45 libs) is resolved by `scripts/resolve.py` starting from `dalvikvm64` and following `DT_NEEDED` plus the libraries ART `dlopen`s at runtime (palette-system, openjdk, javacore, icu_jni, **libart-compiler**), pulling each from the correct source (ART apex / runtime-bionic / i18n / `/system/lib64`). Per-lib provenance in `evidence/lib-provenance.txt`.

## How it is launched (`scripts/run_bionic43.sh`)

`dalvikvm64`'s baked `PT_INTERP` is `/system/bin/linker64` — on OH that is the musl linker — so it is started via the **Bionic linker64 in executable mode** (`linker64 dalvikvm64 …`, the #39 form). Key flags/env:

- `-Xbootclasspath:<12 real jar paths>` + `-Xbootclasspath-locations:<the 12 locations recorded in boot.oat>` (`/apex/com.android.art/javalib/…`, `/system/framework/…`, `/apex/com.android.i18n/javalib/core-icu4j.jar`).
- `-Ximage:$RD/framework/boot.art` — ART inserts the `/arm64/` isa dir itself (pointing at `framework/arm64/boot.art` makes it look for `framework/arm64/arm64/boot.art`).
- `-Xuse-stderr-logger` — routes ART's logging to stderr (see below).
- `LD_CONFIG_FILE=$RD/ld.config.txt`, `LD_LIBRARY_PATH`, and `ANDROID_{ART,I18N,TZDATA}_ROOT` / `ANDROID_ROOT` / `ANDROID_DATA`.

## The eleven blockers, each with its fix

M2 was a chain of missing-piece failures; each was read from the log and fixed. This sequence is the reusable map for M3.

| # | symptom | fix |
|---|---|---|
| 1 | `libartpalette-system.so not found` | ART `dlopen`s it at runtime; stage it + closure (libcutils/libprocessgroup/libtombstoned_client/libselinux) |
| 2 | `Unknown argument -Xno-dex-file-fallback` | drop unsupported flags |
| 3 | `public.libraries.txt: No such file` | provide `$ANDROID_ROOT/etc/public.libraries.txt` |
| 4 | `Failed to get system namespace` | no `/linkerconfig/ld.config.txt`; author a minimal `ld.config.txt` and select it with **`LD_CONFIG_FILE`** (`/linkerconfig` absent, `/` read-only) — the 64-bit equivalent of hanbin `zygote_x_design` P-A |
| 5 | `Error preloading public library libandroid.so` | empty `public.libraries.txt` (a Java hello needs no NDK libs) |
| 6 | `no namespace called com_android_art` | add `com_android_art` + `com_android_i18n` namespaces to `ld.config.txt` |
| 7 | **silent SIGABRT, no message** | ART logs go to logd (absent on OH — the same broken native-log channel #44 tracks); **`-Xuse-stderr-logger`** makes them visible |
| 8 | `LoadNativeLibrary failed for libicu_jni.so` | stage `libicu_jni/libandroidicu/libicu` from the i18n apex |
| 9 | `Unable to open …/framework/arm64/arm64/boot.art` | `-Ximage:$RD/framework/boot.art` (ART adds `/arm64/`) |
| 10 | `Failed to mmap boot.vdex: Empty MemMap` | the `arm64/*.vdex` are symlinks to `../boot-*.vdex`; extract the **real** vdex from `/system/framework/*.vdex` |
| 11 | `JIT could not load libart-compiler.so → Failed to allocate JIT → abort` | stage `libart-compiler.so` (dlopen'd for JIT) |

**Blocker #7 is the one worth remembering.** Until `-Xuse-stderr-logger` was added, every failure was a bare `SIGABRT` with no reason, because ART's `LOG(FATAL)`/verbose route through libbase→logd and OH has no logd. With it, each abort names itself and the chain above could be walked. This is the ART-side answer to the outer loop's native-log-visibility concern (#41 ②/#44): for ART, `-Xuse-stderr-logger` *is* the visible channel; the Java program's own `System.out` was never affected (it is fd 1).

## Boot image really loaded (not interpreted)

`evidence/run-stderr-imageload.txt` (and `-full.txt`): 12× `Using image file …/boot*.art`, 12× `Registered oat file …/boot*.oat`, `Decompressing image took 6.362ms (427MB/s)`, and **zero** `imageless` / `Could not create image` / `fall back` lines. Contrast: the earlier broken-path run logged `Attempting to fall back to imageless running` and then loaded classes from the raw jars — that is the interpreted-BCP fallback the acceptance forbids, and it is absent in the success runs.

## Verified vs deferred

**Verified:** AOSP14 arm64 ART starts on the #39 Bionic linker64/libc on stock OH 6.1; the boot image + 12-jar BCP load (not interpreted); Java runs (`java.vm.name=Dalvik`, arithmetic); 3/3 reproducible, exit 0; no `/system` change (su domain, only `/data/local/tmp`). The conclusion rests on the exit code + boot-image log evidence, not on avc: the su domain is permissive and AVC decisions are cached, so "zero avc" here is **not** evidence of anything (a real app-domain test — M3 — is where avc matters).

**Deferred:** this ran in `u:r:su:s0` (dalvikvm64 from the su shell, as M2 specifies). Running ART under the app domain (`u:r:normal_hap:s0`) is the #41 path (fork+setcon+dlopen in the private namespace, appdat libs) — M3. A real app also needs the NDK public libs (the 10 OH-facing shims of #39/#41) which were emptied here. `libart-compiler.so` (JIT) loaded fine here on real Bionic; under `normal_hap` memfd-RX is denied (#41), so an app-domain ART uses ART's anon-RWX JIT fallback.

## Layout

| path | what |
|---|---|
| `results.json` | machine-readable outcome, provenance, the 11 blockers, verdicts |
| `evidence/run-stdout.txt` | the Java hello output (exit 0) |
| `evidence/run-stderr-imageload.txt` | the boot-image-loaded proof (image/oat lines) |
| `evidence/run-stderr-full.txt` | full ART stderr of one run |
| `evidence/lib-provenance.txt` | each of the 45 libs → its source image |
| `scripts/deploy_bionic43.sh` | **one-shot deploy**: assembles the exact on-board layout (apex/ roots, ICU/tz, emptied public.libraries.txt, ld.config.txt, run.sh) from the VM stage + scripts and pushes it to `/data/local/tmp/bionic43` — nothing is placed by hand, so the layout is fully reproducible |
| `scripts/resolve.py` | dependency-closure resolver across ART/runtime/i18n/system images |
| `scripts/run_bionic43.sh` | the on-board launcher (flags + env) |
| `scripts/ld.config.txt` | minimal Bionic linker namespace config (via LD_CONFIG_FILE) |
| `scripts/Hello.java`, `scripts/build_hello.sh` | the hello + javac/d8 build |
