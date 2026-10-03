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
| 2 | **Realm `_ctype_`** | im-vector (`librealm-jni`) + mcdonalds (`librealmc`) current first-fatal = **`_ctype_`** (C2b, `bind_failed`, UNOWNED). The only exporter is libbionic_compat `b8a87f6f`; but native_private can't see libbionic_compat, and U14 native_abi `7605812c` has NO `_ctype_`. Fix: **add `_ctype_` to native_abi as a new source** (copy b8a87f6f's verified 257-byte table + pointer). cc-t3/native owner. | native_abi **new version** on `7605812c` base | im-vector, mcdonalds clear the BIND wall (then item 3 clears their NEXT wall, the Realm SlabAlloc sysconf crash) | item 3 (sysconf) for the keys to actually light; else they move to the sysconf crash | deploy_generation native-list check; `_ctype_` visible to the 13-pkg native domain (deployed loader `eebd62f2`); anki (librsdroid, Realm) may also need it — confirm |
| 3 | **sysconf translation** | bionic↔musl `_SC_*` remap (`sysconf`, and `getpagesize` is already correct in musl so optional) → `libbionic_compat`. See `2026-10-03-u17-sysconf-compat`. cc-t3/native owner. | libbionic_compat **new version** + ns-order change (②) | **0 immediate** (second-order wall). With native_abi(`__gnu_strerror_r`): **+2 fennec, firefox** (past mozjemalloc MOZ_CRASH). With item 2 (`_ctype_`): **+2 im-vector, mcdonalds** (past Realm NULL-table) | native_abi `7605812c` (for fennec/firefox to reach it); item 2 (for the Realm keys) | ns-order: libbionic_compat ahead of libc.so (② proven collateral-free); runtime fingerprint unchanged except the two libs |
| 4 | **runtime `oh_anw_unwrap`** | gate-free export: `OHNativeWindow* oh_anw_unwrap(ANativeWindow*) = as_adapter(a) magic-check → a->oh` (NO directPathLive gate; `oh_anw_get_oh` gates on state∈{UNBOUND,LIVE}, window-19). Lets route-a + fd-plus SurfaceFromJava drop the probe-only `+0xc0` raw offset. runtime/bridge owner (cc-wiki bridge). | liboh_adapter_bridge **new version** on U16 570e82e0 | **0** (enabler; no key by itself) | none (pure addition) | export present (readelf); route-a/fd-plus switch from `+0xc0` to it; no behavior change for existing callers |

**Batch total predicted move**: fd-plus (1) + fennec + firefox (2, via 3+native_abi) + im-vector + mcdonalds (2, via 2+3)
= **up to 5 keys**, all contingent on the pairings above. native_abi `7605812c`'s OWN C2a effect (firefox/fennec/vlc/ppsspp
reaching load) is the U14 base, carried forward. Items 3 and 4 are predicted-0 alone but enter the batch because they are
REQUIRED pairings for items 1/2 and the route-a path — not solo walls.

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
