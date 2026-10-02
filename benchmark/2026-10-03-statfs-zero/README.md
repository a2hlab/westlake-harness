# The "free-space reported as 0" cache wall: it is getCacheQuotaBytes, not StatFs

Offline, board #90, no board. fd-libretube's `ensureBindApplication FAILED` in the U10.1T8 long-wait
(`master 5d45806cf5`, `benchmark/2026-10-03-u101t8-unbound-longwait`) was `java.lang.IllegalArgumentException:
size must be > 0` thrown from `coil3.disk.DiskCache$Builder.maxSizeBytes`. The dispatch (and the DIGEST note)
suspected `android.os.StatFs` returning 0. **Decompiling LibreTube corrects that premise: the 0 is the return
value of `StorageManager.getCacheQuotaBytes(UUID)`, and the root cause is an incomplete `mount`/IStorageManager
system-service projection — not StatFs, not libjavacore, not the OH sandbox statvfs mount.**

## ① Which API gave 0, and on which path (decompiled, not guessed)
`evidence/libretube-oncreate-decompile.txt` (+ raw `evidence/libretubeapp.onCreate.smali`, Android SDK
`apkanalyzer dex code` on `com.github.libretube_72.apk`). `LibreTubeApp.onCreate` (~r8 line 383–420) is:

```
StorageManager sm = getSystemService(StorageManager.class);
File coil = ImageHelper.getCoilFile(app);          // = getCacheDir()/coil  (INTERNAL cacheDir)
UUID u    = sm.getUuidForPath(coil);               // -> StorageManager.UUID_DEFAULT for internal storage
long v7   = sm.getCacheQuotaBytes(u);              // <-- returns 0
new DiskCache.Builder().directory(coil).maxSizeBytes(v7);   // require(size > 0) -> "size must be > 0"
```

The long handed to `maxSizeBytes` is `getCacheQuotaBytes`'s result with **no arithmetic in between** (v7→v8 pair
passed straight through). A grep of the two decompiled classes finds exactly `getCacheQuotaBytes` + `getUuidForPath`
and **no `StatFs`, no `getUsableSpace/getFreeSpace`, no `getAllocatableBytes`**. So:
- **API = `android.os.storage.StorageManager.getCacheQuotaBytes(getUuidForPath(cacheDir/coil))`** — not `StatFs`,
  not `File.getUsableSpace/getFreeSpace`.
- **Path = the app's internal `getCacheDir()/coil`** (not `filesDir`). Under the OH sandbox this resolves to the
  per-app data dir; but note **that path is never statvfs'd here** — `getCacheQuotaBytes` is a quota query, not a
  free-space query.

## ③ Root cause: the `mount` projection answers only getVolumeList (0x1e)
Two layers were ruled out before the real one:
- **libjavacore is NOT the cause** (`evidence/libjavacore-statvfs-genuine.txt`): the deployed `libjavacore.so`
  carries the genuine AOSP `_ZL13Linux_statvfs…` JNI and imports `U statvfs`/`U fstatvfs` from musl, building
  `android.system.StructStatVfs`. `StatFs`/`Os.statvfs`/`File.getUsableSpace` therefore **work** on route-A — they
  were never on this code path.
- **The OH sandbox statvfs mount is NOT consulted** on this path — `getCacheQuotaBytes` is a binder call, not a
  `statvfs` syscall.

The real gap (`evidence/storagemanager-mount-shim.txt`,
`bms/src/adapter/framework/activity/java/StorageManagerProjectionProxy.java`): the adapter installs a child-local
`MountBinder` into `ServiceManager.sCache["mount"]` (IStorageManager) that implements **only**
`INTERFACE_TRANSACTION` and `TRANSACTION_GET_VOLUME_LIST = 0x1e`. Every other transaction falls through to
`super.onTransact(...)`. The clean-0 mechanism (matches the hilog: a 0, **no** RemoteException):

```
StorageManager.getCacheQuotaBytes(uuid)
  -> IStorageManager.Stub.Proxy over the local MountBinder (no attachInterface)
  -> Proxy writes token+uuid+uid, mRemote.transact(TRANSACTION_getCacheQuotaBytes, data, reply, 0)
  -> MountBinder.onTransact: code != 0x1e -> super.onTransact() returns false for the unknown code
  -> reply Parcel left EMPTY
  -> Proxy: reply.readException() on empty parcel reads int 0  => NO exception
            reply.readLong()      on empty parcel returns 0    => getCacheQuotaBytes RETURNS 0
```

`getUuidForPath` succeeds (no throw) because it only needs `getVolumeList` (0x1e, implemented) and returns
`UUID_DEFAULT` for an internal path. So the wall is a **JAR / system-service-shim layer** gap: the `mount`
projection is incomplete. This was pre-predicted statically (`evidence/static-gapmap-corroboration.txt`): the
2026-09-24 batch4 gap-map already recorded `StorageManager: 1 of 1 natives unregistered … app calls
getCacheQuotaBytes, getUuidForPath`.

### Why the app still lit
The bridge swallows `Application.onCreate` exceptions (`[B43-BIND] ensureBindApplication FAILED` is logged, then
the Activity launches anyway), so LibreTube's home page was outer-signed lit. The functional cost is **the coil
disk image cache is disabled** (no persistent image cache) — a real degradation, not a white/black.

## ② Cross-key scan of U12/U13 hilogs (same symptom)
Read-only grep sweep of all U12/U13 run hilogs (`size must be > 0`, `DiskCache$Builder`, `maxSizeBytes`,
`maxSizePercent`, `coil3.disk`, the okio `$$ExternalSyntheticBUOutline` throw helper, `StatFs`, `getUsableSpace`,
`getFreeSpace`, `getAvailableBytes`, `statvfs`, `ENOSPC`) across `westlake-harness-u7-executor/benchmark/**`,
`westlake-inputs/generations/**`, `westlake-harness/benchmark/**`. Full detail + citations in
`evidence/cross-key-scan.txt`.

**Exactly one key hits the symptom in scope — `fd-libretube`, U12 only:**

| key | U-gen | board | first-fatal? | signature | file:line |
|---|---|---|---|---|---|
| fd-libretube | U12 | 61b | **yes** (bind "Unable to create application", earliest Caused-by) | `IllegalArgumentException: size must be > 0` → `coil3.disk.DiskCache$Builder.maxSizeBytes` → `LibreTubeApp.onCreate` | `…/2026-10-02-u12-final-assembly/window1/u12-A1-…/61b/…/20261002T212458-d84636f5/…/fd-libretube/hilog.txt:19174,19177,19179` (archived copy: `generations/u12-stageA-evidence-bd08c3f7/…:19174,19177`) |

- It **is** the first-fatal for fd-libretube (root `Caused by` of "Unable to create application" at
  `handleBindApplication`), identical fingerprint to the U10.1T8 observation.
- **No other U12 key** shows it. `libresudoku`'s `coil.util…NavHost` frames are an **r8 deobfuscation-collision
  artifact** (coil names mapped onto compose-destinations `NavHost` inside its own `CrashActivity`) — not a match.
  No `ENOSPC`/"No space left" anywhere; the `statvfs`/`StatFs` hits are OH `OH_RegHook` symbol-registration noise.
- **U13 is a clean negative — but because fd-libretube was _not run_ in U13 at all** (the ~40 U13 keys / 248 hilogs
  contain none of the coil/size>0 patterns). So "not reproduced in U13" means **not tested, not fixed** — do not
  read it as the wall being closed.
- Out of scope (flagged only): the same signature recurs in pre-U12 generations (U4/U6/U9/U10/U10.1/r16/r17) and
  ledger artifacts — the same fd-libretube wall carried forward.

Note the scan (and the harness ledger) could only name the API as `maxSizeBytes` with the free-space source "not
identified" from the r8 stack; **the decompile in ① is what resolves that to `getCacheQuotaBytes`.** This bounds the
blast radius: in-scope it is a **single key**, consistent with the prediction that this is a narrow
`getCacheQuotaBytes`-idiom wall, not a broad regression.

## Minimal fix + prediction
**Minimal fix (single file, existing pattern):** extend `StorageManagerProjectionProxy.MountBinder.onTransact` to
answer the cache/alloc quota transactions with a positive value:
- resolve the transaction codes by reflection on `IStorageManager.Stub.TRANSACTION_getCacheQuotaBytes` (and the
  siblings `TRANSACTION_getAllocatableBytes`, `TRANSACTION_getCacheBytes`), the same reflection-friendly style the
  file already uses for the hard-coded `0x1e`;
- on those codes: `data.enforceInterface(DESCRIPTOR)`, read the uuid string (+uid), then
  `reply.writeNoException(); reply.writeLong(quota)` where `quota` is derived from the **genuine** StatFs —
  e.g. `long avail = new StatFs(<app dataDir>).getAvailableBytes(); quota = Math.max(avail / 8, 64L*1024*1024)` —
  i.e. a sane positive cap (coil only requires `> 0`; the value just caps its on-disk image cache).
- Rollback = delete the added `case` block (getVolumeList path untouched). Single-file, child-local, no native,
  no new binder service.

This keeps the gate pattern intact: the projection grows by exactly the transactions apps actually call, every
returned quota is `> 0` (so no `require` ever trips), and the value is honest (real free space), not a magic
constant.

**Prediction:**
- With the fix, LibreTube's `onCreate` completes: coil disk cache enabled, the swallowed `ensureBindApplication
  FAILED` disappears, UI unchanged (already lit).
- The wall is **specific to the `getCacheQuotaBytes`/`getAllocatableBytes` → size idiom**. Apps that let coil use
  its **default** disk cache (`maxSizePercent`, which sizes off `StatFs` free space) are **unaffected** — StatFs
  works. So this is a narrow class, not a broad regression. The ② scan bounds how many keys share it (expected:
  few; LibreTube is the confirmed one).

## This round's rule
Read the decompiled call site before naming the failing API: "cache size 0 / size must be > 0" is not necessarily
`StatFs` — here it is `StorageManager.getCacheQuotaBytes`, a binder-projection gap, while the libc `statvfs` path
is genuinely present. Fix the smallest layer that is actually missing (one more `mount` transaction), derive the
value from the real free space that already works, and keep `> 0` guaranteed so the app's own `require` never fires.

## Files
- `evidence/libretube-oncreate-decompile.txt` — the decompiled `onCreate` chain + `getCoilFile` (cacheDir) + the
  storage-API census; `evidence/libretubeapp.onCreate.smali` — raw dump for reproduction.
- `evidence/libjavacore-statvfs-genuine.txt` — proof the statvfs JNI is real (rules out libjavacore).
- `evidence/storagemanager-mount-shim.txt` — the `mount` MountBinder only-0x1e projection + the clean-0 mechanism.
- `evidence/static-gapmap-corroboration.txt` — the 2026-09-24 static gap-map that pre-predicted this.
- `evidence/cross-key-scan.txt` — the raw U12/U13 hilog scan (②).
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push. Decompile via Android SDK `apkanalyzer` (read-only on the input apk). Sources read
read-only: the LibreTube apk (`westlake-inputs/apks/fdroid100`), the deployed `libjavacore.so`
(`westlake-harness-bms`), the adapter JAR source (`westlake-harness/bms`), the long-wait record
(`westlake-harness`/`-u7-executor`). The fix is the framework/adapter owner's to implement + ship; this is
static staging only.
