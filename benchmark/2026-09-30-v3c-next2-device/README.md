# v3c-next2 device check on 5cd

Next2 passes deployment integrity gates but is not an accepted runtime baseline.
The earlier missing `libhitrace_ndk.z.so` error moves to `libwm.z.so`, required
by `liboh_adapter_bridge.so`, and ZigZag exits to the desktop. The previous
static inventory already contains libwm in `/system/lib64`; physical file
coverage is insufficient without the namespace dependency edges. Do not fix
this by repeatedly declaring just the next missing filename.

## Controlled inputs

- Board: 5cd1e3dd00000000000000000923012c, original boot a42f2d6c-d29d-40aa-8145-51b4f85d0187.
- Before: v3c package 668e4f7c, Java r17m a5cbd8d7, old installer.
- Candidate: next2 package 61cecc5a, ANL 1162a6fc, AudioSystem runtime f87dcdf9.
- Java overlay was exposed to package r8b for the deployment transaction,
  then the same r17m bytes were rebound. The external JAR is an explicit variable.
- Full upgrade uses the revised deployer, with SHA/maps/single-ART checks.
  No foundation restart, installer replacement or reboot was performed.
- All app runs use the master bms_batch.py, launch-only, hilog 20,
  shots 5,20 and focus checking. Preflight confirms 16M buffers, privacy off,
  24h screen timeout and a two-second clock skew.

## Evidence accounting

The first run used the wrong input root for HW/ZZ, so those apps were not
executed. It later stopped on a missing HDC status marker during a boot-ID
read. The boot did not change; raw records are retained. The complete retry
uses the existing signed control inputs and original app inputs through a
separate directory of symlinks. No APK or installer was changed.

`facts-verbatim.txt` contains the runner's exact output. No screenshot or
survival total is inferred from the requested six-app plan. Per-app evidence
is in `evidence/`; full hilog and commands remain under `runs/`. Diagnostic
excerpts record original line numbers and source hashes. Script status
`foreground_unconfirmed` is retained even where screenshots visibly show UI.

Surface lifecycle work is separate and remains proposal-only:
`../2026-09-30-egl-surface-lifecycle/`, commit 9a52b12a.

Final screenshot review, Anki library-load findings, rollback and final SHA
state are recorded in results.json. Audio playback
is outside this startup test; a VLC launch does not certify audio output.

## Candidate observations

| App | t20 screenshot | Native result / limit |
|---|---|---|
| ZigZag | OH desktop | fatal libwm.z.so dependency lookup failure; candidate rejected |
| HelloWorld | Hello World and controls | visible UI retained |
| Auxio | five tabs and music-source button | visible UI retained |
| NetGuard | disabled-state main screen and application controls | visible UI retained |
| VLC | blank white window | three AudioSystem registrations logged; newAudioSessionId still has no implementation |
| Anki | LeakCanary Leaks / Heap Dumps / About | old installer entry; no librsdroid.so load record, load verdict unverified |

For Anki, Java class names under net.ankiweb.rsdroid are not ELF-load evidence.
The batch stops the app during cleanup, and no live maps were collected for
Anki in this run. Do not claim either a successful native load or proof that
it never loaded. This is the limit of the observed entry path.

VLC log line 41620: `No implementation found for int
android.media.AudioSystem.newAudioSessionId()`; the earlier max-channel/rate
registrations are at lines 31426–31428. Registration does not certify playback.

Native rollback restores v3c 668e4f7c with the identical r17m JAR; ZigZag again
shows TAP TO PLAY. Final SHA/installer/ledger readback passes. The 5cd lock is
retained only because the outer loop immediately assigned next3 on this board.
