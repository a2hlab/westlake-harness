# U15 #1 remainder, normal-domain bionic gap (fd-meet): compat v3 NOT built — libbionic_compat is not in fd-meet's lookup scope (calibrated on the board), so it would move 0; the full gap set is 14 LIBC symbols, all already in native_abi v2; route = put org.jitsi.meet in the native cluster

#90, offline. Nothing was deployed to a board and nothing was built: this round's dispatched artifact predicts 0 first-fatal moves, and per AGENTS a 0-prediction part is not built. The stop is reported with the evidence below.

## 1. What the normal domain can actually see (OH musl source, then the board)

**OH musl's per-library relocation scope** (hw248 OH musl `dynlink.c`, `add_can_search_so_list_in_dso` and
`find_sym_by_saved_so_list`) has three parts:
- every `is_global` DSO in the process;
- the dlopen root's dependency tree, entries accessible from the relocating library's namespace;
- the library itself.

**Versions** (`check_verinfo`). A provider without `.gnu.version_d` accepts any `@LIBC` import. compat b8a87f6f has
VERSYM/VERNEED but no VERDEF, so its unversioned exports **would** match. **Version is not the blocker; scope is.**

**fd-meet's board run** (U12 window 4, 5ea, APK `72a89e53` = `org.jitsi.meet_26000002.apk`). SoLoader opens each
library as its own root:

| library | board first `relocating failed` | model A: normal domain, global set {} | model B: + compat 015aa3a6 global (the deployed compat) |
|---|---|---|---|
| libhermes.so | `__register_atfork` | `__register_atfork` ✓ | `__register_atfork` ✓ |
| libreactnative.so | `__register_atfork` | `__register_atfork` ✓ | `__register_atfork` ✓ |
| libc++_shared.so | **`android_set_abort_message`** | **`android_set_abort_message`** ✓ | `__assert2` ✗ (compat exports android_set_abort_message) |

**Only model A reproduces the board.** libbionic_compat is loaded in these processes as a NEEDED of
`liboh_android_runtime.so` (link line `-lbionic_compat`). It is neither global nor in the app library's dependency
tree, so app libraries never see it.

**So "compat v3 = b8a87f6f + exports" moves fd-meet by 0.** The same holds for every normal-domain key.

## 2. The full LIBC gap set of fd-meet in the normal domain (`replay_normal.py`, model A; `evidence/replay-fd-meet.txt`)

All of `__register_atfork`, `android_set_abort_message`, `__assert2`, `__errno`, `strtoll_l`, `strtoull_l`,
`__system_property_get`, `__sF`, `__cmsg_nxthdr`, `__FD_SET_chk`, `__FD_ISSET_chk`, `__FD_CLR_chk`, `__open_2`,
`__gnu_strerror_r`. **14 symbols**, across:

| library | gaps |
|---|---|
| libc++_shared | 7 |
| libjsi | 6 |
| libjingle_peerconnection | 4 (`__cmsg_nxthdr`, `__FD_*_chk`) |
| libhermes, libhermestooling, libreactnative, librnscreens, librnworklets | `__register_atfork` |

libjsctooling additionally lacks the JavaScriptCore API (`JS*`). That is an optional JSC library a Hermes build does
not load, so it is not counted.

**Coverage.** native_abi v2 `f8619ad5` exports **all 14**; compat b8a87f6f exports 5 of them.

**Model C** (native domain: `westlake_native/` first + native_abi v2 global): **0 LIBC symbols missing in all 13
libraries** (libjsctooling's JSC names aside).

## 3. Who else misses the same batch (all 326 U12 + U13 stage-A runs, every key; `scan_runs.py` → `scan-runs.json`)

| key | domain | gap symbol (library) | first-fatal wall? |
|---|---|---|---|
| **fd-meet** | normal | `__register_atfork` (libhermes, libreactnative); `android_set_abort_message` (libc++_shared) | **yes** (U12) |
| x | normal | `__register_atfork` (libcrashlytics) | no: caught; x's terminal is the telephony NPE (U13 JAR), lit/white per window |
| fd-plus | normal | `android_set_abort_message` (libc++_shared) | no: it dies at bind on `ScanCallback` (stubs 87cf65cc) |
| ooniprobe | normal | `__errno` (libjnidispatch) | no: lit key |
| toutiao | normal | `__cmsg_nxthdr` (libsscronet), `__errno` (libttcrypto) | no: its wall is ICU (U14) |

By the first-fatal measure, **only fd-meet is blocked by this batch.** The native/Flutter-domain hits (`_ctype_`,
`__gnu_strerror_r`, `__pthread_cleanup_push`, `android_dlopen_ext`, `ATrace_beginSection`, `slCreateEngine`) belong
to the native_abi v1/v2 and C4 clusters already reported.

## 4. Minimal fix that does move fd-meet: one package into the native cluster

**The change.** Add `org.jitsi.meet` to `native_cluster_path()` in `libapp_native_loader` (deployed `eebd62f2`,
13 packages; source `westlake-harness-bms-deploy benchmark/2026-09-30-n3-native/flutter/app_native_loader.c:62-66`).
- That package's domain then gets `westlake_native/` first and the **RTLD_GLOBAL native_abi**. With U14 native_abi v2
  (f8619ad5) that already exports the whole batch.
- **No new export anywhere.**
- This is how mcdonalds, Element and burgerking, the other React-Native/Realm apps, are already handled.

**Prediction.** fd-meet's first fatal **moves past `__register_atfork` (high)**: the replay is 0 missing in the native
domain, calibrated by model A reproducing the board. Next wall unknown (RN/Hermes init). Every other key 0.

**Risk to check before deploying.**
- In the native domain fd-meet resolves `libandroid.so` from `westlake_native/` (ee2fb82c) instead of the root
  libandroid.
- It gets no private libz (its APK ships none, and nothing NEEDs libz).
- The same holds for the 13 existing members.

**Build route** (not done this round; needs the outer's go):
1. Reproduce eebd62f2 faithfully from its recipe (same A′ procedure as native_abi and EGLImpl).
2. Add the one string, build ×2.
3. Gate: only the package-list string and the length/loop constants change.

**Not chosen: a normal-domain global ABI provider (host change).** It would also fix fd-meet, but it exposes the batch
to every normal app (ooniprobe, x, fd-plus, toutiao would start binding these symbols) for one first-fatal mover.

## 5. `__register_atfork` semantics (for whichever provider carries it; `evidence/register-atfork-semantics.txt`)

**AOSP 14 r1 `bionic/libc/bionic/pthread_atfork.cpp`.**
- `__register_atfork(prepare, parent, child, dso)` stores `dso` as the entry's `dso_handle`. The handlers are kept in
  bionic's own list.
- `__unregister_atfork(dso)`, called from `__cxa_finalize` on `dlclose`, removes every entry with that `dso_handle`.
  A library that registered fork handlers can therefore be unloaded safely.

**route-A native_abi** (`native_abi.c:12-18`, unchanged since d2053066).
- It forwards to OH musl `pthread_atfork(prepare, parent, child)` and **drops `dso`**.
- musl has no per-DSO unregister, so the handlers of a library that is later `dlclose`d stay registered. The next
  `fork()` would call into unmapped code.
- For Hermes/React Native/Crashlytics this never happens: SoLoader never unloads.
- Recorded limitation: a faithful `__unregister_atfork` would need its own handler list (AOSP's), not a forward. It is
  not needed for any observed key.

## What was wrong before

- The cluster table and this dispatch assumed the normal domain "sees" libbionic_compat. The board line
  `libc++_shared … android_set_abort_message` is the counter-evidence: compat exported that symbol in U12 and the
  relocation still failed.
- Rule: **before adding exports to a provider, replay the consumer with and without that provider in scope, and keep
  the model that reproduces the board's first-missing line.**

## Files

- `replay_normal.py`: normal/native-domain musl-order replay, full gap list, `--global`, `--native-domain`.
- `scan_runs.py` → `scan-runs.json`.
- `replay-normal.json`, `replay-native-v2.json`.
- `evidence/replay-fd-meet.txt`, `evidence/register-atfork-semantics.txt`.
- `results.json`.
