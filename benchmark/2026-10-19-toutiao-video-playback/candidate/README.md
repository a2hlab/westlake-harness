# Toutiao video t2 — offline candidate for the confirmed P1 (OpenSL IID provider)

**Offline build only. Nothing was deployed and no board was touched.** The outer approved t2 for offline build after reviewing t1 `7c7a7ec7ac`. The board window waits for the P0r2 review/schedule.

## Confirmed first fatal (from t1)

On 61b boot `8f7f12bf`, child 9290, run.sh `d3518cef`, a tap on a real feed video produced:

```
[SOURCE-NATIVE-LOAD-FAIL] .../libttmplayer.so namespace=0 ... SL_IID_ANDROIDSIMPLEBUFFERQUEUE: symbol not found
```

`TTPlayer` init was then rejected. See [../static/selected-change.json](../static/selected-change.json).

## Candidate (two deploy inputs)

| Deploy input | SHA256 | Note |
|---|---|---|
| `deploy-inputs/libopensles_android_compat.so` → `/data/local/tmp/asx/` | `9f558aaf…ee761f` | built from `opensles_android_compat.c` `cf45ad43`, copied verbatim |
| `deploy-inputs/run.sh` → `/data/local/tmp/asx/run.sh` | `ea984942…5f73` | `d3518cef` + one LD_PRELOAD token ([source-diff.txt](source-diff.txt)) |

**What the DSO does.** It is not data-only. It exports two data symbols, `SL_IID_ANDROIDCONFIGURATION` and `SL_IID_ANDROIDSIMPLEBUFFERQUEUE`, plus the crt `_init`/`_fini`. Its constructor runs `dlsym(RTLD_DEFAULT,"SL_IID_BUFFERQUEUE")`. If that lookup finds a symbol, it overwrites the SIMPLEBUFFERQUEUE pointer with OH's standard `SL_IID_BUFFERQUEUE`; this is **not** `SL_IID_OH_BUFFERQUEUE`. The source comment's claim of "API compatibility" is unverified here.

**DT_NEEDED closure.** `libOpenSLES.so` resolves on the board to `/system/lib64/libOpenSLES.so` `05d8ac90`, the first hit on the run.sh path (t1 RQ1). `libc.so` resolves to OH musl. The only strong undefined import is `dlsym`. The link-only `libOpenSLES.so` (`486936c0…`, under `out/link-only.NOT-FOR-DEPLOY/`) supplies only the SONAME at link time. It is **never deployed** and is not committed.

## Build

[build_candidate.sh](build_candidate.sh) uses `scripts/lab/dockbuild.sh` with the pinned OHOS clang 15.0.4 `feef13a3`, the same compiler string as the RouteB preload DSOs. The recipe is Westlake `build.sh` `0d8e4f43` (lines 89–93). All steps returned rc 0. **Raw logs** are kept privately and unmodified at `$HOME/.local/share/westlake/toutiao-video-t2-build/20261019T180522/`, with their SHA256 listed in [logs-sanitized/raw-log-manifest.txt](logs-sanitized/raw-log-manifest.txt). The repo carries renamed `*.sanitized.txt` copies in [logs-sanitized/](logs-sanitized/) only, and toolchain hashes are in [toolchain-manifest.json](toolchain-manifest.json).

## Offline gates ([logs-sanitized/40-offline-gates.stdout.sanitized.txt](logs-sanitized/40-offline-gates.stdout.sanitized.txt))

- **Negative:** without the compat DSO, libttmplayer has 2 unresolved symbols (the two IIDs).
- **Positive:** with it, **0 unresolved** against the RouteB/APK/OH-ABI provider set.
- **Exports:** only the two IIDs plus `_init`/`_fini`. No libc-class exports (DIGEST #48 preload hazard). One observed difference: the RouteB `libwebview_bionic_shim` exports no `_init`/`_fini` (it uses a version script). musl runs DT_INIT/DT_FINI by address, not by symbol lookup.
- **Constructor dependency:** OH `libOpenSLES` `05d8ac90` exports `SL_IID_BUFFERQUEUE`.
- **`check_frozen`:** rc 0, 0 violations.

**Not testable offline:** loading in the RouteB preload; the constructor's effect; OH OpenSL behavior with the remapped IID; release/lifecycle. These belong to the board window in [rollback-plan.json](rollback-plan.json), together with the exact deploy steps, rollback and pass criteria (this change only).

**Not claimed:** audio, video playback, or the next wall (P2 audio callbacks, P3 surface, network/content stay unknown).

## Log provenance correction

The first build commit `f3668cef85` had scrubbed `$HOME` **in place** in `logs/`, with no backup, so those files were not raw originals. They are removed. The small build was re-run (`build_candidate.sh`, now with a private `LOGDIR` that is never scrubbed). The rerun is byte-identical: DSO `9f558aaf`, unstripped `701ba399`, link-only `486936c0`. Public copies are produced by [sanitize_logs.sh](sanitize_logs.sh) under distinct names. The closure inputs used by the gates are also persisted privately (`closure-inputs/`).

## Execution card r2

[OPERATIONS.md](OPERATIONS.md) is now a card only and closes t4 review `d953c270` blockers 1–4:

- physical `$RT` targets with preimages and metadata;
- fresh reboot → new parent for both apply and rollback;
- WID-exact `before(W)`/`after(W)` CAS (normalization withdrawn);
- an exact object-specific load result via GOT relocation reads.

The `ops/` script was removed. The candidate bytes are unchanged.
