# R10 bounded decoder observation (offline handoff)

R9 retry exhausted all256 player mirrors at video `resetCodec`; later silence did not prove codec success or a terminal fallback failure. R10 changes only the mirror attempt budget to4096. It is an observation successor, not a playback repair or deployment admission.

`ttplayer_log_mirror.c` differs from the exact r8 source only by `MIRROR_ATTEMPTS = 256` → `4096`. Original OpenSL C, player0b4d and its105 relocations, mediad288, and r9 runb562 remain fixed. `provenance.json`, `core-freeze.json` and `verify.py` bind exact inputs. Original r8/r9 files are untouched.

Each provider instance attempts at most4096 single fd2 writes of at most1024 total bytes (4MiB). The saturated path still forwards every call once. Entry errno, backend return/errno, dangerous-format refusal, `%n`/alias behavior and no-write-retry remain unchanged. A write may block; greater logging can perturb timing.4096 is a ceiling, not a promise to cover25seconds or every decoder event. No event filter, dynamic reset or system logger replacement is introduced.

## Offline checks

From the worktree containing this handoff:

```sh
R10=benchmark/2026-10-19-toutiao-video-playback/candidate-r10
python3 "$R10/verify.py" source --inputs-root "$MAIN"
python3 "$R10/verify.py" receipt-tests
python3 "$R10/oracle/run.py" --source "$R10/ttplayer_log_mirror.c" --out "$FRESH_HOST_OUT"
R10_INPUTS_ROOT="$MAIN" cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_decoder_observation -- --nocapture
```

The source root defaults to the current repository after landing. An isolated producer checkout can explicitly use read-only `$MAIN` for existing exact artifacts; it does not copy or overwrite them. The oracle uses pthreads, TLS and independent atomic counters, not the implementation's private counter. Each test runs in its own process.8threads make8192 calls: every call must forward, with exactly4096 writes and at most4MiB. Sequential4095/4096/4097, normal arguments, positional formatting, `%m`, filtered/aliased `%n` before and after saturation, long inputs, failed and short writes are covered.

Current producer results:16/16 host cases, source pins,7 rejection cases, shell syntax and spec lint passed. Rust3/3 passed; final receipt selector re-run passed after adding the two explicit pin-drift negatives. These are host behavior and offline rejection evidence, not OH ABI, provider or playback evidence.

## Production recipe — outer execution after review

The three core files are frozen in `core-freeze.json`. Production was **not run by this lane**; no compat output SHA is invented. The outer may use its already reviewed r8 production environment:

```sh
SOURCE_REPO="$MAIN" OH_NATIVE="$EXISTING_OH_NATIVE" LIBLOG_INPUT="$EXACT_D8AD_LIBLOG" OUT="$FRESH_PERSISTENT_OUT" bash "$R10_SOURCE_DIR/build_candidate.sh" --run
python3 "$R10_SOURCE_DIR/verify.py" accept-build --inputs-root "$MAIN" --build "$FRESH_PERSISTENT_OUT"
```

`SOURCE_REPO` supplies the original compat/anchor/toolchain/inputs. The mirror and checker are read from the recipe's own directory. `OUT` must be fresh and persistent. Recipe runs check_frozen before compilation, verifies exact inputs, records commands/stdout/stderr/rc in raw/, uses the original pinned OH toolchain and image, resolves actual libdl.a, retains `--unwindlib=none`, and links real d8ad liblog with exact SONAME. Existing exports/dependencies and the unique vprint relocation are checked without widening the ABI gate. Link-only libOpenSLES and liblog are never deployment payloads.

`accept-build` rejects missing raw execution logs, nonzero stages, inventory/file drift, source/toolchain input drift, recipe drift and ABI changes. Its result remains human-review-pending; it cannot attest runtime binding or playback. A completed production receipt must be reviewed separately. Exact rebuilt compat/provider/GOT and actual video/audio stay UNKNOWN until their separate authorized experiment.

## Evidence handling

Small host raw logs and their SHA are in `evidence/host-01`. `.artifacts/` holds the host executable/object files and unmodified raw Rust logs; public Rust logs are explicitly sanitized with raw SHA in `evidence/raw-log-index.json`. No device calls or production compiler invocation occurred. Frozen core files must not change while outer construction is running.
