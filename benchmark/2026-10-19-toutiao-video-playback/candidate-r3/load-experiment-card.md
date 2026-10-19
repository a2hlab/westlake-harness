# r3 minimal load-experiment card (61b, outer-run, read-only after deploy)

**Purpose.** r3 removes one *statically proven* fatal (libmffmpeg null init slot reached by libttmplayer's by-name `DT_NEEDED`). Whether that makes the whole android-ns routing correct is **inference**, not proof. This card lists the read-only items to confirm in one small window. It is a card, not a script; the three-file apply/rollback is outer CAS executor r5 (89b054e1, independently reviewed by cx-seal). No writes here; all reads after one video tap in the identified Toutiao child `C`.

## Preconditions (apply done by the CAS executor)
- Three files at their postimages (`selected-change-r3.json` → `deploy_three_files`): run.sh `79275cf9` (at `W_new`), compat `9f558aaf`, `$RT/lib/arm64-v8a/libmffmpeg.so` `d2882303`.
- Fresh reboot → new `boot_id` → new parent (P1 lifecycle, OPERATIONS card §4). Single-file backup `...libmffmpeg.so.ttvideo-before-<boot8>` (r5 executor naming) present, sha `fecf91e1`.

## Already proven statically (do NOT re-litigate on the board)
- `SanitizeInitArray` runs only on the ART explicit entry; musl by-name `DT_NEEDED` does not (link_stubs 87a2e823 L552-559; dynlink e50b30f2 L2408/L2552).
- `do_init_fini` has no null guard (e50b30f2 L3446-3457). Original mffmpeg slot `0x45c168`=0, 0 relocs → the r2 **predicted** fatal (static; observed P1 window LOAD-FAIL was the libvcbasekit ns0 relocation that masks it).
- `d2882303` = original with `DT_INIT_ARRAYSZ` `8→0` only; `INIT_ARRAYSZ=0` ⇒ `n=0` ⇒ no slot called; `SanitizeInitArray` early-returns ⇒ ART opens the real path ⇒ one inode shared with the `DT_NEEDED` load.

## Verification items (this is what the window is for)

| # | Read (no writes) | Pass | If not |
|---|---|---|---|
| V1 | `[SOURCE-NATIVE-INITARRAY] .../libmffmpeg.so` is **absent** from the child stderr delta (replaced file has nothing to drop); and **no** `.libmffmpeg.so.westlake-init.*` mapping in `/proc/C/maps` | confirms the early-return / single-inode path | STOP: the deployed mffmpeg is not `d2882303` or a stale sibling exists |
| V2 | exactly one `/data/local/tmp/asx/lib/arm64-v8a/libmffmpeg.so` offset-0 mapping in `/proc/C/maps`, inode == the deployed file's inode; same inode used by the ART load and the `DT_NEEDED` load | single file/inode (outer requirement) | report two inodes / a dotted copy |
| V3 | `[SOURCE-NATIVE-LOAD] .../libttmplayer.so` present and **no** `[SOURCE-NATIVE-LOAD-FAIL]` for libttmplayer or libvcbasekit; **no** `_ZNSt6__ndk18ios_baseD2Ev: symbol not found` | the inferred __ndk1 closure holds (libvcbasekit binds APK libc++ in the android ns) | record the exact first relocation error verbatim; routing inference is **false**, do not claim r3 |
| V4 | compat IID GOT read in `C` (P1 success criterion, OPERATIONS §5): `[B+0x4730b0]==Cb+0x3b98`, `[B+0x4730e8]==Cb+0x3b90`, with `B`=libttmplayer offset-0 start, `Cb`=compat offset-0 start | IID identity holds from the android ns | if unreadable → **unknown**, not success |
| V5 | inode of `/system/lib64/libOpenSLES.so` mapping in `C` is single (one copy) | inherit gave one OH OpenSLES | report copy count |
| V6 | the next `[SOURCE-NATIVE-LOAD-FAIL]` or first ULE after libttmplayer, verbatim | — | this is the **next first-fatal** (expected: surface/ANativeWindow/EGL, next-walls P2/P3); record, do not fix in this window |

## Verdict rules
- **"r3 load blocker removed"** requires V1–V3 pass and V4 pass. V4 unreadable ⇒ unknown.
- V3 failing ⇒ the "routing becomes correct" inference is refuted with the exact symbol; the derived mffmpeg stays valid (it removed the proven fatal) but a further provider edge is missing — continue closure, do not re-bake the runtime.
- No audio/video/surface success is claimed from this card. V6 names the next wall only.
- Small-window discipline: ≤30 min, read-only, board lock held, then rollback or hold per outer.
