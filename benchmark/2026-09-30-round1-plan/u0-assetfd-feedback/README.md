# U0 asset-fd checkpoint receipt

**Correction:** 66 record directories do not mean 66 completed measurements. LibreTube was interrupted after installation: no hilog, t20 process table or screenshot. Do not infer that its cache/TagSoup walls passed. Likewise, SPD's own error Activity is neither gameplay nor a GLES checkpoint pass. Frozen J1/N1/U1 predictions remain unchanged.

## Evidence and score

The four source runs in master `benchmark/2026-09-30-unified-assetfd-5cd-sweep/runs/` contain **35 + 11 + 10 + 10 = 66** unique keys. All APK hashes match the frozen table; all four measured 117-path runtime maps match (`8281e90f8aa0`). Runtime `53f00423`, r17r `dd4f0eae` and both background installer hashes are checked. This is **U0**, before the J1/N1 batches; it is not their acceptance score. Only 35 clicks follow the plan freeze, and all exposure/profile caveats remain.

The outer README's screenshot decision is preserved: **21 lit**, **20/21 baseline lights retained**, NewPipe added, AntennaPod lost. Literal frozen lighting retrieval against this U0 observation is J1 **21/23**, N1 **21/24**, U1 **21/27**, with zero unpredicted lights in each column. These fractions are descriptive precision, **not prospective accuracy or patch success**; `advance`/`unknown` are not darkness promises. The U1 six unfulfilled light labels are AntennaPod, API Demos, fd-noice, noice, Habit Tracker and Wikipedia.

Recounting original `record.json.captured` and UID-qualified process tables gives **124 captures**, t5 **28 alive / 35 absent / 3 unknown**, t20 **28 / 34 / 4**. There are 65 finished records, 62 recorded clicks, three input-gated keys and the interrupted LibreTube. Original producer facts are retained verbatim in `results.json`; no screenshot is re-adjudicated.

## Cluster updates and next walls

`clusters.json` covers all **30 plan clusters / 57 unique cluster-key memberships**: 44 still blocked, 4 passed, 1 passed into another wall, 1 new first wall, 7 unknown. Shared apps count in multiple clusters. A repeated secondary exception establishes that API remains broken; it does not establish first-wall order. Noice's later audio checkpoint is masked by EGL; LibreTube, AppManager, Termux and fd-mobile retain stated observation boundaries.

| App | U0 observation; routing | Original hilog lines |
|---|---|---|
| NewPipe | KEEP01 passed; outer-signed own UI. Next observed failure: application-local `PlayerService` bind throws `InvocationTargetException` (J1). Inner cause is not logged; playback was not exercised, so no claim it blocks startup. | 42968 |
| SPD | N07 still blocked. Launcher PID 18885 first fails libgdx's `libstdc++.so` dependency, then GLImpl JNI; PID 18913 displays the error Activity. N1 needs both app namespace dependency and GLES closure. | 27727, 28941, 36878 |
| AntennaPod | KEEP02 regression: PID 19616 RenderThread SIGSEGV. Native root cause unknown; retain asset-fd and repeat three times before attribution. | 50955–50956 |
| Habit Tracker | KEEP01 advances into N01 EGL recreation fatal. Widget-manager NPE is background/tolerated, not a replacement for the fatal. | 30129, 43869 |
| VLC | Newly selected first fatal is `AudioSystem.native_getMaxChannelCount` (N1); later PID still fails J02 theme attribute 13 (J1). Both layers remain required. | 44741, 61742 |
| fd-mobile | Old background Asset FD throw absent and rendering reached; no proof that the background job completed or that UI is usable. | 50415 |

`next-walls.json` supplies full original log paths, SHA-256 and verbatim numbered excerpts for this table; `per-key.csv` supplies all 66 outcomes. Feeder's main-thread W-ROOM exception and PPSSPP's caught load failure remain blocked as diagnosed in the accepted addendum. R2 boundary: offline log/profile checks only; UI decisions inherited from the outer reviewer, no board action and no native crash root-cause proof.

## Reproduce

```sh
python3 benchmark/2026-09-30-round1-plan/u0-assetfd-feedback/score.py
(cd benchmark/2026-09-30-round1-plan/u0-assetfd-feedback && shasum -a 256 -c SHA256SUMS)
```

The script reads only these four archived runs and the accepted plan. `results.json` records source hashes and profile maps. J1/N1 future results must receive separate receipts; this directory never overwrites the freeze.
