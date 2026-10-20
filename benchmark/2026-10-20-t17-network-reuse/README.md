# T17: exact5cd reuse of the R9 network routing configuration

T16's actual5cd candidate reached TTPlayer JNI_OnLoad after the IID wall. Its retained filtered readout contains seven short `ff_listen_connect2` records with `ret:-97 neterrno:-97`. The three public excerpts are exact receipt bytes with offsets/SHA, not a claim of complete child-log coverage. They contain no configuration JSON or media URLs. This supports selecting the existing R9 configuration for the next bounded5cd test; it does not establish an actual current GOT winner or guarantee error removal.

The only runtime delta from the accepted R8 set is two run lines:

- `WESTLAKE_ANDROID_NATIVE_NET_TARGETS`: append `libmffmpeg.so`, preserving `libsscronet.so`.
- `WESTLAKE_ANDROID_NATIVE_INHERIT`: append existing `libandroid_native_network_compat.so`.

PRELOAD and every other run byte remain unchanged. Derived5cd WID29 run SHA is `11d3d671bd501205a98ee386e64bf1274501d0458a4cdb35945f7424a388244a`; it is byte-identical to the existing R9 template after the previously approved UID20011300/WID29 substitutions. `run-routing.diff` is the exact two-line change. Live WID still requires the same fresh5cd checks and single-line equivalence rule as T16.

## Exact input compatibility and build limits

The three already archived R8 runtime binaries remain byte-identical: media `d2882303`, player `0b4d95c5`, OpenSL compat `6e83e924`. Their persistent copies and full hashes are in `results.json`; no compiler, linker or binary patch is run. The unchanged existing network provider is exactly `f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e`, 22552 bytes. T16's guarded actual5cd preflight input recorded physical/private inode66352:159629, mode644 and UID/GID20011300. The local CAS input independently matches that SHA. Fresh next-window readback must repeat those checks.

The existing network provider's release audit explicitly records **UNKNOWN_EXACT_BUILD_CLOSURE**. Historical source `a25134d6` and recipe `0d3b61f7` explain bounded behavior but do not prove the exact producing source/toolchain/raw build log for f6. This reuse neither rebuilds nor replaces f6 and must not upgrade that provenance gap. R8 binaries retain their existing archived build/derive receipts.

## What the earlier experiment actually established

61b's R9 retry directly read paired getaddrinfo/freeaddrinfo GOT targets into exact f6 functions (+0x23f4/+0x2a00), with mapped-object SHA/dev/inode and before/after maps. Later mirrored logs reached formatter/audio/video decoder preparation. The256-line mirror cap was exhausted; no statement about later absent messages is valid. Playback remained NOT_PASSED and audio unknown. The exact retry archive is `$HW248_ARTIFACT_ROOT/toutiao-video-r9-retry-20261020/window.tar.gz`, SHA `96e22e3d16d33d5bc3ab88d4b67d969a2d51d1defaeae0bfa2ad3cb488eff55e`.

Adding NET_TARGETS changes selected immediate-caller addrinfo conversion. Adding INHERIT changes eligibility in the **shared android_app namespace**; it is not proven media-only and can change other callers' lookup candidates. No actual5cd provider winner is established by matching bytes or this static card.

## Minimal next window

Finish and independently verify T16's original5cd restoration first. Derive T17 from the exact reviewed T16 executor, preserving5cd cfg/UID, preview/admission/holder/deadline, physical/private identity, all backups before swap, foreign-state rejection, exact original rollback, no-parent physical recovery and original power/parameter handling. Use separate T17 backup/stage names and a new apply-plan; never reuse T16's backup as this window's authority. Add only exact unchanged f6 file/metadata and private-inode checks. Source differences require independent review before execution. Reuse the518+26 snapshot partition unchanged.

The candidate places the same three R8 DSOs and the R9 run onto the restored baseline; it is not a run-only change on an assumed still-live R8 state. Fresh-boot, normal icon/feed/video, then confirm **both** media getaddrinfo/freeaddrinfo actual bindings with the existing R9 readpoints adapted to5cd and current guards. The old reader hardcodes61b and must not run unchanged. Expected moved key is **toutiao only**, targeting the observed network failure. Keep ANW observations separate; neither binding, prepare nor a static cover is a video seal. No61b operation, new provider source, random-exit investigation or new runtime build is proposed.

## Prepared executor (still unadmitted)

`derive_t17.py --repo "$REPO"` checks exact T16 executor SHA05099f6c and produces `executor.py`. Differences are the T17 backup/stage namespace, description and unchanged-f6 hash/metadata/private-inode guards. Physical-only recovery checks the physical f6 object without depending on a missing parent. All remaining CAS/admission/window/recovery behavior comes from T16. Local reference/parameter files select the exact two-line R9 postimage. The admission template is unsigned; outer supplies fresh next-window identities after T16 restoration. The unchanged three-DSO input directory remains `$BASE20/t16-r8-candidate-inputs` and is hash-checked again before apply. CLI is the same as T16, using this directory's executor and its new admission.

Eight reused host checks plus exact two-line/public-excerpt checks pass through a real Rust selector. These checks do not replace independent source review or actual network-binding evidence. Preparing the5cd paired reader remains a separate narrow task; the old61b helper cannot be called as-is.

## Read-only paired binding reader

`read_binding.py` replaces the historical reader's fixed 61b identity only for this
5cd window. It reuses the pinned original `map_rows`/`bias_for` PT_LOAD algorithm.
It reads media GOT offsets 4782456 and 4782944, comparing against exact f6 load
bias + 0x23f4 / 0x2a00. It does not read unknown pointees, patch memory, attach,
change UI/settings, or execute on import/preview. Existing build-closure unknowns
above are unchanged.

Outer must supply a new post-reboot `reader-profile.template.json` filled from
fresh raw evidence: boot, observed_at, exact parent/child PID/PPID/birth/UID/exe/mnt,
init mnt, actual libc SHA/path, actual candidate run SHA, and receipt SHA. Supply
the matching raw candidate run as `--run-file`; only its one numeric WID line may
differ from the R9 11d3d671 reference. No old 6395 profile is a current identity.
Profile age must be at most 120 seconds at entry. The reader has a monotonic
120-second limit and stops before the T17 window's 10-minute recovery reserve.

```sh
python3 "$REPO/benchmark/2026-10-20-t17-network-reuse/read_binding.py"
python3 "$REPO/benchmark/2026-10-20-t17-network-reuse/read_binding.py" --execute \
  --repo "$REPO" --profile "$FRESH_PROFILE" --receipt "$FRESH_RAW_RECEIPT" \
  --run-file "$FRESH_RUN_COPY" --inputs "$BASE20/t16-r8-candidate-inputs" \
  --net-elf "$WORKSPACES/westlake-inputs/seal-artifacts-20261012/sha256/f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e" \
  --hdc "$HDC" --holder "$EXACT_T17_HOLDER" --start "$T17_START_EPOCH" \
  --out "$BASE20/t17-network-binding-new-child"
```

The output directory must be new. Raw Board commands survive timeout. Each read
has before/after boot, UID, birth, PPID, tracer, executable, namespace, run hash
and private-run-inode guards. Four mapped objects (player/media/libc/netcompat)
are verified by file SHA and mapped dev:inode, then repeated with unchanged
relevant maps. Merged HDC output uses explicit dd rc and one exact eight-byte od
line; no stderr suppression and no remote temporary file. Missing marker,
short read, process drift or map drift produces UNKNOWN/nonzero. Both exact GOT
matches are required for PAIRED_BINDING_MATCH. This proves these two sampled
slots only, not effective getenv, every loader namespace, audio or playback.

`test_reader.py` runs eight host tests including real shell binary/short/error
reads with merged stdout/stderr. These are not on-board transport validation.
