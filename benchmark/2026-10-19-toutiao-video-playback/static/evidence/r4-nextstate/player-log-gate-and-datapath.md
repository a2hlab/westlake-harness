# r4 next-state evidence (formal-card input) — player verbose-log gate + data-path

Static only. No board claim. Objects: libttmplayer `b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02` (SHA-identical to the deployed physical, `video-r4-readonly/player-metadata/step-0.txt`); APK `a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395` (`westlake-harness-rea-seal/.octos/rea-inputs/toutiao.apk`, pinned in `benchmark/2026-08-23-toutiao/SCAN-PROVENANCE.json`).

Address convention: REA/Ghidra image base `0x100000`, ELF PT_LOAD vaddr 0 → file off 0, so **file_offset = ghidra − 0x100000**.

## A. Player verbose-log gate (libttmplayer)
REA Ghidra 12.1.4 (ephemeral), evidence_ids: string `ev_dbafe43d…`, xref `ev_9efe6473…`, containing-proc `ev_f6ee059f…`, decompile `ev_ac375204…`.

| item | ghidra | file off |
|---|---|---|
| string `"debug.ttplayer.log.enable"` | `0x4c6e03` | `0x3c6e03` (byte-verified) |
| read site (`__system_property_get`) | `0x394b00` | `0x294b00` |
| containing fn `JNI_OnLoad` | `0x394ac0` | `0x294ac0` |
| verbose flag `DAT_00575bac` | `0x575bac` | `0x475bac` (.bss) |

Decompiled logic (JNI_OnLoad): default value `"false"`; `__system_property_get("debug.ttplayer.log.enable", buf)`; if set and first 4 bytes == `"true"` (`0x65757274`) → `DAT_00575bac=1` ("log enabled by prop"); if == `"file"` (`0x656c6966`) → opens `/mnt/sdcard/ttplayer/ttplayer.log`, `DAT_00575bac=1`; else `=0`.
- **Read once, at library load** (JNI_OnLoad runs during `System.loadLibrary("ttmplayer")`), which happens lazily at first video. So the param must already be set when the player lib loads in that process.
- Read path: `__system_property_get` is serviced by `RT/webview-t-lib/libwebview_bionic_shim.so` `read_oh_property` → `dlsym(RTLD_DEFAULT,"SystemReadParam")` (outer source pin, webview_bionic_shim.c ~2397); OH param precedes the shim's small default table.

### Corrected diagnostic ORDER (prior "set→reboot" was wrong: a reboot clears the non-persistent key before it can be read)
Board is currently restored to **b427 (not r4)**. If this diagnostic is run:
1. apply r4 four files → **fresh boot** (new parent) ;
2. launch app; **then** `param set debug.ttplayer.log.enable true` and **read back** (while running, before the first video load) ;
3. real icon launch → tap video → `System.loadLibrary("ttmplayer")` → `JNI_OnLoad` reads `true` → verbose on ;
4. observe stderr/hilog player state ;
5. rollback four files → **fresh boot** → verify param **absent** (`param get` → errNum106) + feed equivalent.
`param` has no `delete` (only ls/get/set/wait/dump/shell/save); current `param get` → **errNum106 (absent)**. The non-persist reset-to-absent recovery basis is being independently verified by cx-seal; do not treat `set ""` as restoring absent.

## B. Streaming data path (APK DEX, JADX 0.7.1, class_count 139838)
- `com.ss.mediakit.medialoader.AVMDLDataLoader` (+ Configure/Listener/NotifyInfo) present. It `System.load`s `libavmdlbase`/`libavmdl`/`libavmdls` at runtime and catches failure (DEX strings: `"try to load avmdl:"`, `"System.load libavmdlbase"`, `"Can't load avmdl library: "`, `"other exception when loading avmdl library: "`).
- **APK ships 138 arm64 `.so`; none is `libavmdl*`/`libttopenssl`** (local mirror 138/138). These are runtime-downloaded plugin natives (r3 stderr showed a `/data/data/com.ss.android.article.news/files/plugins/…` path); absent on this offline harness → `RT/lib` ENOENT (`open_errno=2`, r4 stderr 2337–2409).
- DEX decision strings (not yet mapped to the firing branch): `"Dataloader is not ready. Put it to the pending list:"`; direct-play/fallback: `DEFAULT_DIRECTPLAY`, `openFallbackReader`, `[attachData] videoUrl not detected, openFallbackReader`, `isDirectPlayInFeed=`, `127.0.0.1` (MDL local proxy).

## C. Observed runtime (r4, child 9360) — observations, NOT root cause
- Crash removed: child alive t5/t20/t25, no SEGV/cppcrash (`video-r4-play1`).
- Engine reached `TTVideoEngine.play → VideoPlayerImpl.doPrepareAction` (play1 stderr :71884); only a caught `Settings$SettingNotFoundException: screen_brightness`.
- One-shot thread-wait snapshot (`video-r4-thread-waits`, taken after rollback, before reboot): player/video/audio threads in `do_epoll_wait`/`futex_wait` at that instant.

## Explicit NOT-proven (do not state as fact)
1. A single `wchan` snapshot does **not** prove the pipeline is fully built, that no decode is running, or that network is excluded.
2. `search_strings "avmdl"` == 0 in libttmplayer does **not** prove there is no indirect (dlsym/callback) avmdl interaction; it only means no literal "avmdl" string constant.
3. "avmdl absence → playback blocked (pending)" is a **hypothesis**; the firing branch (pend vs `DEFAULT_DIRECTPLAY` direct-URL) is not yet log- or decompile-confirmed. The verbose Java path (`TTVideoEngineLog`) was off this session, so the "pending list" line did not appear.
4. This is not characterized as a symbol/ABI/derive defect; the leading direction is a missing runtime **plugin-native provisioning** gap, pending (A/B) confirmation.
