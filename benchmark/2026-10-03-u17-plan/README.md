# U17 native batch plan (cc-t3)

#90, offline. Plan for the next native batch on the U16 native base. Per AGENTS "一版 native 合进全部 native 层簇,
预测为 0 的不进" — one version per native lib merging all its cluster fixes; no solo predicted-0 item. Key counts are from
`benchmark/2026-10-03-u13-first-fatal-clusters` (U13 window1 + U14 ownership predictions); **confirm against U14 window
1–5 actual hilog first-fatals when the batch runs** (the executor runs under `.../2026-10-03-u14-stage-a-plan/window{1..5}`).

Base: **U16 native `1d42dbfb` / `570e82e0`** (the runtime + native_abi the batch rebases on).

## ① Entry list
| # | item | what / where / who | artifact + base | predicted first-fatal move (keys) | pairing dep | gate |
|---|---|---|---|---|---|---|
| 1 | **fd-plus lockCanvas** | the two Surface JNI natives `S_nativeLockCanvas`/`S_nativeUnlockCanvasAndPost` (A2 pure-Java via JNI Bitmap/Canvas + inner libsurface). cc-wiki. | runtime **35c36d00** (cc-wiki fd-plus REV, on U16 1d42dbfb; REV2 `5a37a50be9`) | **+1: fd-plus** (clears the `Surface was not locked` fatal) | fd-plus's EARLIER wall C8 `android.bluetooth.le.ScanCallback` (stubs `87cf65cc`) must also be present | equiv.py: only the 2 funcs differ, 0 new NEEDED (23==23), 0 new object, open 197==197; on-board 3 checks (no-fence wait, ARGB_8888↔RGBA_8888 byte order, dirtyRect ignored) |
| ~~2~~ | ~~Realm `_ctype_`~~ **ALREADY DONE in U14 — DROPPED** | `_ctype_` is already exported by the DEPLOYED U14 native_abi **`f8619ad5`** (cc-t3's native-abi-v2 build `e90947270c`, recipe `benchmark/2026-10-03-u14-native-abi-v2/build_v2_hw248.sh`; `results.json` shows `_ctype_@@LIBC`; `u14-effective-rebind` composition.json:858 = `/system/android/lib64/westlake_native/libwestlake_native_abi.so` `f8619ad5…`). The u13-cluster note "U14 native_abi 7605812c has no `_ctype_`" was pre-v2; the EFFECTIVE U14 native_abi is f8619ad5 WITH `_ctype_`. | — (no build) | im-vector + mcdonalds ALREADY past the `_ctype_` bind wall in U14 (their U14-A1-r3 first-fatal is now the Realm SlabAlloc **sysconf** crash — confirmed in `2026-10-03-u17-native-crash-static`). | — | — |
| 3 | **sysconf translation** — **DEFERRED TO USER** (frozen ns-order, §②) | bionic↔musl `_SC_*` remap. See `2026-10-03-u17-sysconf-compat`. | libbionic_compat new version + ns-order change (frozen appspawn-x) | **+2 fennec, firefox** (past mozjemalloc MOZ_CRASH, native_abi f8619ad5 already deployed) + **+2 im-vector, mcdonalds** (now AT the Realm sysconf crash since `_ctype_` is cleared in U14) | native_abi `f8619ad5` (deployed); — | **BLOCKED**: the sysconf OVERRIDE needs libbionic_compat ahead of libc.so, which is a hardcoded string in the FROZEN appspawn-x (§②). Outer shelved; **user decides** |
| 4 | **runtime `oh_anw_unwrap`** | gate-free export: `OHNativeWindow* oh_anw_unwrap(ANativeWindow*) = as_adapter(a) magic-check → a->oh` (NO directPathLive gate; `oh_anw_get_oh` gates on state∈{UNBOUND,LIVE}, window-19). Lets route-a + fd-plus SurfaceFromJava drop the probe-only `+0xc0` raw offset. runtime/bridge owner (cc-wiki bridge). | liboh_adapter_bridge new version on U16 570e82e0 | **0** (enabler; no key by itself) | none (pure addition) | export present (readelf); route-a/fd-plus switch from `+0xc0` to it; no behavior change for existing callers |
**Correction (2026-10-03, outer)**: item ② (Realm `_ctype_`) is DROPPED — it is already deployed in U14 native_abi
`f8619ad5`. native_abi needs **no build**. So the native_abi base for any future work is **`f8619ad5`** (not 7605812c).
im-vector/mcdonalds are now blocked ONLY on sysconf (item 3, user-deferred).

**Currently-actionable items** (A1 jar takes priority when it lands): **item 1 (fd-plus lockCanvas)** and **item 4
(oh_anw_unwrap)**. Item 3 (sysconf) is user-deferred (frozen ns-order). Item 2 is done.

**Batch predicted move (recomputed vs U14 window 1–5 actual hilog first-fatals)**:
- **fd-plus**: U14 facts `t5=yes t20=no` (starts, dies before t20); JNI `nativeLockCanvas`/`nativeUnlockCanvasAndPost`
  registered, past bind → its U14 first-fatal is the Surface `lockCanvas` fatal → **fd-plus lockCanvas `35c36d00` → +1**.
- **oh_anw_unwrap**: **0** (enabler; route-a/fd-plus drop the `+0xc0` probe offset).
- **sysconf (deferred)**: would be +2 fennec/firefox (native_abi f8619ad5 already lets them reach mozjemalloc) + +2
  im-vector/mcdonalds (now at the Realm sysconf crash, `_ctype_` cleared) — but BLOCKED on the frozen ns-order (user).
So the **buildable-now batch moves +1 (fd-plus)**; the sysconf +4 is gated on the user's ns-order decision.

## ② ns-order risk surface (reorder libbionic_compat ahead of libc.so)
The sysconf fix needs libbionic_compat to win `sysconf` over musl. open_site_scan (`2026-10-03-u17-sysconf-compat`) showed
libbionic_compat is inherited into the sealed-child scope but AFTER `libc.so` in the `dlns_inherit` `shared` list.
**Full collision check (evidence/reorder-collision.txt)**: libbionic_compat's **46 exports vs musl libc's 1873 → ZERO
overlap** (`comm -12` empty). Every libbionic_compat export is bionic-specific (`android_*`, `__system_property_*`,
`__memcmp16`, fdsan, logger, mallopt, `create_android_logger`); even `adler32`/`__sync_*` are absent from musl libc
(adler32 is zlib; __sync_* is compiler-rt). So:

| approach | what changes | risk | verdict |
|---|---|---|---|
| **Reorder libbionic_compat ahead of libc.so** (edit the sealed-child `dlns_inherit` shared list) | today: NOTHING (export sets disjoint). After adding sysconf/getpagesize: only those flip to libbionic_compat (intended). | **empirically zero collateral** (0/46 overlap). Future: any NEW libbionic_compat export that collides with musl would then silently shadow it — add a guard/lint. | **RECOMMENDED** (minimal, proven safe) |
| **sysconf-only interposer / symbol-version** | a dedicated tiny interposer lib (or versioned `sysconf`) ordered ahead of libc, exporting only sysconf/getpagesize | surgical; no exposure from libbionic_compat's other symbols ever | fallback if the reorder guard is unwanted; more moving parts (new lib + ns wiring) |

Recommendation: **reorder** now (collateral is zero), plus a one-line lint that fails the build if a future
libbionic_compat export starts colliding with musl libc (so the "disjoint" invariant that makes the reorder safe can't
silently break). The surgical interposer is the fallback.

## ③ Batching (AGENTS)
- One native version per lib, merging all that lib's cluster fixes: native_abi gets `_ctype_` (+ any other native-domain
  cluster with predicted>0 at build time); libbionic_compat gets sysconf (+ getpagesize if needed); the bridge gets
  oh_anw_unwrap; the runtime gets fd-plus lockCanvas. ONE build per lip, deployed together, three-board sharded, judged by
  t20/t28 screenshots.
- Predicted-0 solo items do NOT enter on their own — but items 3/4 enter as REQUIRED pairings (they unblock 1/2 and
  route-a), which is the sanctioned exception, not a solo predicted-0 wall.
- On regression, bisect by halving.

## Status
Plan only, nothing built/deployed. A1 jar (cc-wiki) still pending — when it lands, A1 runs first. The .so half of A1 is
already delivered (cc-wiki `5a37a50be9`, hw248 `/home/alvin/cc-wiki-m2-nweb-rev/`).
