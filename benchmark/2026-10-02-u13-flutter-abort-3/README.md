# Three Flutter SIGABRT keys + fd-musicplayer ColorSpace — static dead/alive + predicted moves

Offline, no board, board #90. The dispatch: the candidate base's SIGABRT Flutter keys that my GetLongField fix's
predicted-4 (glmark2/localsend/fluffychat/immich) did not list — **fd-saber, fd-kitchenowl, fd-libre** — locate each
abort (DFX first frame, abort message, Flutter engine entry), decide same-root; plus **fd-musicplayer** "can't create
bitmap without a color space". Each: alive/dead, fix layer, real count of keys whose first fatal moves.

## Result in one line
All three Flutter keys **are** GetLongField fid==null aborts (same root), and a readelf test proves they funnel through
the **same** `AAssetManager_fromJava` my fix patched — so they are **already covered by the deployed U13 runtime
`18763dd4`** (predicted move **+3, no new fix**). fd-musicplayer is a **separate, alive** wall: our `ImageDecoder.
nGetColorSpace` stub returns null; fix is a **one-.o runtime** change (predicted move **+1**).

| key | verdict | abort | fix | predicted move |
|---|---|---|---|---|
| fd-saber | ALIVE | GetLongField+1664 fid==null ← libflutter (imports AAssetManager_fromJava) | already in 18763dd4 (my asset_manager.o) | +1 (free) |
| fd-kitchenowl | ALIVE | same | already in 18763dd4 | +1 (free) |
| fd-libre | ALIVE | same | already in 18763dd4 | +1 (free) |
| fd-musicplayer | ALIVE | Java `createScaledBitmap` → null source colorSpace | runtime: `ID_nGetColorSpace` return SRGB (one .o) | +1 (new fix) |

## The three Flutter keys — same root, already covered (the surprising part)
Every one aborts identically (`evidence/flutter-abort-3.txt`): `#05 JniAbort+2516` ← `#06 GetLongField+1664`
(the fid==null path, hardened in `benchmark/2026-10-02-getlongfield-null`) ← `#07 libflutter.so`. So the dispatch's
"not in GetLongField" means "not in my predicted-4 list" — the abort **is** GetLongField fid==null.

**Why #07 is libflutter (no libandroid frame), and why it's still my wall:** `AAssetManager_fromJava` tail-calls
`GetLongField`, so its frame is elided and the backtrace shows its caller (libflutter) directly above GetLongField.
The decisive test — `nm -D` / `readelf` on each app's `libflutter.so` (pulled from `westlake-inputs/apks/fdroid100/`):

```
com.adilhanney.saber   libflutter 11747864B buildid fdf0a0a6..  ->  U AAssetManager_fromJava
deckers.thibault.aves  libflutter 11747864B buildid fdf0a0a6..  ->  U AAssetManager_fromJava   (identical to saber)
com.tombursch.kitchenowl libflutter 11581856B buildid 889a1df3.. ->  U AAssetManager_fromJava   (different build, same)
```

`U` = **undefined import** (0 local AAssetManager definitions), so libflutter does **not** statically carry its own
copy — it resolves `AAssetManager_fromJava` to the runtime's, which is exactly the function my getlongfield-null fix
lazy-inits. saber/libre share a byte-identical libflutter (fdf0a0a6); kitchenowl is a different engine build but the
same import and the same crash → **engine-level root, one fix covers all three.** Corroborated by DIGEST 538 (saber was
always in the AssetManager fid==null cluster) and 546 (the field is AssetManager.mObject; "the Flutter engine reads
resources via the same NDK interface").

**Coverage:** my `aa149019` asset_manager.o (lazy-init: `if gAssetManagerOffsets.mObject==null { GetFieldID; }` then
GetLongField) is in the final U13 runtime `18763dd4`. It self-heals **every** runtime copy on first use, so every
libflutter that imports `AAssetManager_fromJava` is covered. **No new fix** — the predicted +3 rides the same U13
single-variable window that validates the original 4; the only contingency is that window confirming the asset_manager
fix moves the 4 at all (same mechanism, same choke point). Net: the GetLongField fix is predicted to move **7** keys
(the 4 + these 3), not 4.

## fd-musicplayer — separate, alive, one-.o runtime fix
`main_threw: IllegalArgumentException: can't create bitmap without a color space` at `Bitmap.createBitmap:1203` ←
`createBitmap(source,…):979` ← `createScaledBitmap:831` ← `FoldersFragment.g` (album-art thumbnail). The null is the
**source bitmap's** color space: `createBitmap(source,…)` reads `source.getColorSpace()` → null → throws.

Root (`evidence/musicplayer-colorspace.txt`): `ID_nGetColorSpace` (`android_graphics_compat_shim.cpp:79`, registered
for `android.graphics.ImageDecoder.nGetColorSpace`) **deliberately returns null** — a G2.4 workaround for a
ColorSpace-class fid==null abort, with the stated assumption "no Android UI path strict-requires non-null ColorSpace."
fd-musicplayer refutes that: `Bitmap.createBitmap(source,…)` strict-requires it. A bitmap decoded via ImageDecoder gets
its color space from this stub → null → the scale throws.

Fix (`fix/musicplayer-ngetcolorspace.md`): make `ID_nGetColorSpace` return `ColorSpace.get(Named.SRGB)` instead of null
(keep a null fallback). ColorSpace now registers before ImageDecoder (`AndroidRuntime.cpp:306`), so the original
fid==null risk that motivated the null stub should no longer apply. Layer: **runtime**, one .o in
`liboh_android_runtime.so`; assemble with cc-t3's U13 runtime. **Predicted move: +1 (fd-musicplayer).** The fix is
general (any ImageDecoder-decoded bitmap that is then scaled/copied) but only this one key is asserted.

**Confirmation gaps (static, before building):** (1) confirm the source bitmap was decoded via ImageDecoder (so
nGetColorSpace is on its path) vs BitmapFactory (then the null originates in the shimmed Bitmap/hwui decode — libhwui
has no reproducible source, DIGEST 610); (2) confirm returning sRGB no longer trips the ColorSpace-class fid==null
abort the G2.4 stub guarded against.

## This round's rule
A tail-called NDK function (`AAssetManager_fromJava → GetLongField`) elides its own backtrace frame, so the frame above
GetLongField is the *caller*, not the owner — don't read "#07 libflutter" as "libflutter has its own copy." `nm -D` on
the app's actual .so settles import-vs-static in one read and here flipped "3 uncovered walls" into "+3 already covered
by the merged fix." And a deliberate null-returning stub (`ID_nGetColorSpace`) carries its own refutable assumption;
fd-musicplayer is the counterexample that retires it.

## Files
- `evidence/flutter-abort-3.txt` — the three identical DFX backtraces + the readelf `U AAssetManager_fromJava` proof + DIGEST refs.
- `evidence/musicplayer-colorspace.txt` — the full Java stack + the `ID_nGetColorSpace` null stub + the register-order note.
- `fix/musicplayer-ngetcolorspace.md` — the one-.o runtime change (nGetColorSpace → SRGB) + prediction + confirmation gaps.
