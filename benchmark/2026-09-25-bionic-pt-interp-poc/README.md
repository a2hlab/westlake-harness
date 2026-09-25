# #39 — Bionic PT_INTERP minimal viable verification + 57-library rebuild plan

**Board entry:** `#39` in `.octos/OUTER_LOOP_REVIEW.md`
**Date:** 2026-09-25
**Mode:** read-only research + minimal on-board exec. Only `/data/local/tmp/bionic39` was written; no `/system`, no remount, no reflash, no app launched.

This is step 1 of the Bionic direction ([#37 feasibility](../2026-09-25-bionic-libc-feasibility/)): prove that a native process brought up by a **real AOSP14 Bionic `linker64`** runs on a **stock OH 6.1.0.31 DAYU600** board with **zero SELinux denials**, and that the in-process thread layout is Bionic's — the ABI fact Toutiao's `metasec` depends on. It confirms hanbin's PoC-2 on our own platform. If it holds, we emit the batch plan for rebuilding all 57 in-process runtime libraries.

**Result: it holds.** `tp_probe_dyn` came up under the Bionic `linker64`, exit 0, reproducible; `tls[1] == pthread_self()` and `pthread_internal_t.tid@+16 == gettid()`; **0 avc**.

---

## Part ① — Bionic provenance

The linker and libc were extracted, read-only, from the **official Google AOSP 14 arm64 system image**. arm64 / Android 14 Bionic is the ABI `metasec` targets, so no cross-arch guessing is involved.

| field | value |
|---|---|
| zip | `arm64-v8a-34_r04.zip` (Google dl.google.com sys-img) |
| zip sha1 | `d9f2011131919abe952814e041f16f317242c3fa` (matches Google's `sys-img2-3.xml` manifest) |
| zip sha256 | `1447958a4c6747c44390ac5f5f4c894be6d1dfce93868a0385a95c5f0ae4c339` |
| build | `UE1A.230829.036.A1` · API 34 · release 14 · security patch 2023-09-05 · userdebug/test-keys |

**Extraction chain (all read-only):**
`system.img` (GPT) → `super` (liblp logical partition `system`, ext4) → `/system/apex/com.android.runtime.apex` (zip) → `apex_payload.img` (ext4) → `debugfs rdump`.
The two small parsers used — `scripts/gpt.py` (GPT partition table) and `scripts/lpunpack.py` (minimal liblp reader) — are included so the path is reproducible without root or Android host tools.

| file | bytes | sha256 | build-id | soname |
|---|---|---|---|---|
| `bin/linker64` | 2052848 | `ffd6af09…88ac88dd` | `754da550a9a0a6253736cb09421cd8e4` | — |
| `lib64/bionic/libc.so` | 1168752 | `d9c96460…a32fba2c` | `a87908b48b368e6282bcc9f34bcfc28c` | `libc.so` |
| `lib64/bionic/libdl.so` | 136608 | `10eca143…fdf57d62` | `68dbee43b38ecf35adb7a992155439d5` | `libdl.so` |
| `lib64/bionic/libm.so` | 331656 | `a01413bf…b70e748e` | `4392071b5402c384f493539827bf25c0` | `libm.so` |

Full hash list in `PROVENANCE.txt` (also captures `libdl_android.so`, `libc_malloc_{debug,hooks}.so`, `crash_dump64`, `linkerconfig`, `etc/linker.config.pb`).

---

## Part ② — On-board verification

**Board:** `5cd1e3dd00000000000000000923012c` (assigned by the outer loop after #31 measurement ended). Kernel `Linux 5.15.180 aarch64`, shell `uid=0 root, u:r:su:s0`. hdc `Ver 3.2.0d`.

**Test program** (`scripts/tp_probe.c`): reads `TPIDR_EL0`, then TLS slot 1 (`TLS_SLOT_THREAD_ID`), compares it to `pthread_self()`, reads slot 5 (stack guard), and checks `pthread_internal_t.tid` at offset +16 against `gettid()`. On arm64 Bionic, slot 1 *is* `pthread_self()` — that identity, plus the tid offset, are exactly what `metasec` reads.

**Build** (`scripts/build.sh`, NDK r23b): two forms —
- **static control** (`-static`): its own libc, no interpreter — isolates the toolchain from the linker path.
- **dynamic** (`-fPIE -pie -Wl,--dynamic-linker=/data/local/tmp/bionic39/linker64`): `readelf -l` confirms `PT_INTERP = /data/local/tmp/bionic39/linker64`, `NEEDED = libdl.so, libc.so`.

**Verify** (`scripts/verify_onboard.sh`): pushes linker64 + `lib64/bionic/{libc,libdl,libm}.so` + the four binaries to `/data/local/tmp/bionic39` only; snapshots `dmesg` line count; runs each binary with `LD_LIBRARY_PATH=…/lib64/bionic`; diffs `dmesg`/`hilog` for `avc`. No `dmesg -c`, no `/system` write.

### Results (`onboard-run.log`)

| case | outcome |
|---|---|
| **A** static control | **SIGABRT (exit 134)**: `TLS segment is underaligned: alignment is 8, needs to be at least 64 for ARM64 Bionic` |
| **B** `hello_dyn` via linker64 | `bionic39 hello`, **exit 0** |
| **B** `tp_probe_dyn` via linker64 | **exit 0**; `tls[1] == pthread_self == 0x7f932844f8`; `slot1==self yes`; `pthread.tid@16 = 23724 == gettid (match yes)` |
| **B2** explicit-linker, absolute path | **exit 0**, `slot1==self yes` (relative path is rejected: `expected absolute path`) |
| reproducibility | 3 further runs, all `slot1==self yes`, tid matches, exit 0 (distinct tids 24351/24356/24361) |
| **avc** | **0** — dmesg delta empty, hilog empty |

The only linker output is a benign warning that `/linkerconfig/ld.config.txt` is absent (OH has no generated Bionic linker config); Bionic falls back to the default namespace and honours `LD_LIBRARY_PATH`, which is enough.

**About case A:** this is *not* a linker-path failure. NDK r23b emits TLS segment alignment 8; Android 14 added a hard check that the main executable's arm64 TLS segment be ≥64-aligned. The static binary trips it before `main`; the dynamic binary sidesteps it because `tp_probe.c` declares no `thread_local`, so its executable carries no TLS segment. The abort is itself corroboration that the shipped libc is **genuine AOSP14 Bionic** — it enforces the newer rule. A static baseline, if wanted, needs a newer NDK or an aligned `thread_local` in the program.

### Acceptance

- ✅ helloworld runs with Bionic `linker64` as PT_INTERP, prints result, exit code reproducible
- ✅ `TPIDR_EL0` / `pthread_internal_t` layout is Bionic's (`slot1==pthread_self`, `tid@+16==gettid`)
- ✅ zero avc, no policy patch
- ✅ hanbin PoC-2 (Bionic interpreter needs no sepolicy patch) holds on **stock OH 6.1 arm64**

Board left clean (`/data/local/tmp/bionic39` removed).

---

## Part ③ — 57-library rebuild batch plan

Generated by `scripts/make_plan.py` from `deps39.json` (`scripts/deps39.py`, run in the VM against `out-all0925/native-runtime`). Every library is split into `in-runtime` / libc-family / external(OH) `DT_NEEDED`, given a topological level over the in-runtime edges, and — for the OH-facing ones — the count of undefined symbols each external OH library actually satisfies.

### 47 mechanical (libc-only) libraries — batch by topo level

Batch order = level ascending: a level-N library only needs levels `< N` already rebuilt, so each batch is internally parallel. Disposition tally: **31 aosp · 9 rebuild · 6 retire · 1 art**; ~63 MB total.

- **`aosp`** — generic AOSP library: take the AOSP 14/15 prebuilt or rebuild from AOSP source with the NDK/Bionic sysroot.
- **`rebuild`** — westlake-specific: recompile against the Bionic sysroot (drop `-D__MUSL__`, OH libc++ → NDK libc++).
- **`retire`** — musl-compat shim, unneeded once the process is real Bionic.
- **`art`** — `libart`, special (see below).

| Batch | libs | notable |
|---|---|---|
| **L0** (20) | 6 retire/rebuild + 14 aosp | `libicuuc`(29MB,aosp), `libz/liblog/libexpat/libjpeg/libwebp`(aosp); **retire** `libwestlake_bionic, libwestlake_securec, liboh_popen_boundary, liboh_process_cpu_time, liboh_tls_boundary`; **rebuild** `libandroid_native_network_compat, libwl_missing_natives, liboh_network_jni, liboh_webview_startup_order` |
| **L1** (5) | aosp | `libbase, libicui18n(3.9MB), libnativehelper, libpng, libultrahdr` |
| **L2** (8) | 7 aosp + 1 retire | `libcutils, libft2, libharfbuzz_ng, libicu_jni, libjavacrypto, libziparchive, libstatssocket`; **retire** `libwestlake_libcore_linux` |
| **L3** (4) | 2 aosp + 2 rebuild | `libutils, libminikin, libstats_jni`(aosp); **rebuild** `libwestlake_runtime_boundary` |
| **L4** (3) | `libandroidfw`(aosp), **`libart`(art)**, `libwestlake_binder`(rebuild) |
| **L6** (2) | `libbinder_ndk`(aosp), `libwestlake_asset_bridge`(rebuild) |
| **L7** (2) | `libmedia_jni, libstatspull`(aosp) |
| **L10** (3) | `libjnigraphics`(aosp); **rebuild** `libframework-connectivity-jni, libframework-connectivity-tiramisu-jni` |

Per-library detail (producer, bytes, disposition, in-runtime deps) is printed by `make_plan.py`; the raw facts are in `deps39.json`.

**`libart` is not a free rebuild.** It must match the Android boot image (`boot*.art`/`.oat`) it loads; the ART build and the boot classpath image are one unit. Sourcing ART for Bionic means taking it (and its boot image) from the same Android 14/15 tree as the linker, not recompiling ours against Bionic in isolation. This is the single highest-risk item in the mechanical set.

### 10 OH-facing libraries — Bionic client shims

These call OH firmware libraries directly. Under Bionic they cannot link OH's musl/libc++ innerkits as-is; each needs a client shim. The split that drives cost:

- **C-API forwarders** (GLES/EGL/vulkan, `native_*`, `hilog`, `hitrace`, `napi`, `*_ndk`, `begetutil`, `sync_fence`): thin — a stable C ABI, forwardable.
- **C++ innerkit bridges** (`ipc`, `utils`, `want`, `ability_*`, `window/wm`, `render_service_*`, `dm`, `mmi`, `udmf`, `pasteboard`, `samgr`, `appexecfwk_*`, …): heavy — vtable/RTTI/`std::string`/`sptr` across the musl↔Bionic C++ ABI boundary.

| lib | L | ext libs | syms | C-API | C++ innerkit | effort (pd) |
|---|---|---|---|---|---|---|
| `liboh_adapter_bridge` | 6 | **34** | 384 | 52 | **332** | **53.4** |
| `libwl_opengl_jni` | 2 | 2 | 374 | 374 | 0 | 19.7 |
| `libhwui` | 8 | 9 | 198 | 197 | 1 | 11.0 |
| `liboh_ime_helper_capi` | 0 | 2 | 29 | 1 | 28 | 5.2 |
| `liboh_connectivity_state` | 0 | 1 | 7 | 0 | 7 | 2.0 |
| `liboh_android_runtime` | 5 | 3 | 9 | 9 | 0 | 1.4 |
| `liboh_account_state` | 1 | 1 | 3 | 0 | 3 | 1.4 |
| `libandroid` | 9 | 3 | 6 | 5 | 1 | 1.4 |
| `liboh_hwui_shim` | 1 | 1 | 3 | 3 | 0 | 1.1 |
| `liboh_permission_queries` | 0 | 1 | 1 | 0 | 1 | 1.1 |
| **total** | | | | | | **≈98 pd (≈20 person-weeks)** |

Effort heuristic: 1 pd base/lib + 0.05 pd per C-API symbol + 0.15 pd per C++ innerkit symbol. Estimates, not measured.

**Cost is concentrated.** Two libraries are ~74% of the OH-facing effort:
- `liboh_adapter_bridge` (53 pd) fans out to **34** OH innerkits — the IPC/ability/window/RS/MMI surface (`ipc_single` 43 syms, `utils` 38, `cesfwk_innerkits` 33, `mmi-client` 31, `want` 26, `render_service_client` 21, …). This is the real T1 body of work and the natural place to stage sub-batches.
- `libwl_opengl_jni` (20 pd) is 374 GLES/EGL C-API symbols — thin per-symbol but numerous, and it lands in the same Mali-G57 `libmc` musl-island question raised in #37.

`libhwui`'s 198 symbols are almost all GLES/EGL/surface C-APIs to the Mali stack, so it is cheaper per-symbol than its count suggests and shares the OpenGL island decision with `libwl_opengl_jni`.

---

## What is verified vs deferred

**Verified (R2):** Bionic provenance (hashes), on-board exec via PT_INTERP (exit 0, reproducible), the Bionic `pthread_internal_t`/TLS identity `metasec` relies on, and zero avc — all on the stock OH 6.1 board.

**Deferred / unverified:**
- exec via `source_app_namespace` with an app uid (the T1 launch path; this PoC ran only in the su shell);
- Bionic over a long-lived process with **no Android property area** (only a short probe here);
- `libm` was pushed but not exercised (`tp_probe` pulled only `libc`+`libdl`);
- the ③ effort numbers are heuristic.

## Layout

| path | what |
|---|---|
| `results.json` | machine-readable facts (provenance, on-board results, batch plan) |
| `onboard-run.log` | cleaned board transcript (evidence) |
| `PROVENANCE.txt` | Bionic extraction hashes |
| `deps39.json` | per-library DT_NEEDED / level / external-symbol facts |
| `scripts/tp_probe.c`, `scripts/hello.c` | test programs |
| `scripts/build.sh` | NDK build with PT_INTERP → on-board linker64 |
| `scripts/verify_onboard.sh` | push-and-run, avc check (only `/data/local/tmp`) |
| `scripts/deps39.py` | dependency-fact extractor (VM) |
| `scripts/make_plan.py` | batch-plan generator from `deps39.json` |
| `scripts/gpt.py`, `scripts/lpunpack.py` | read-only image parsers used in Part ① |
