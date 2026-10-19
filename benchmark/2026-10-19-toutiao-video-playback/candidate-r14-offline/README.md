# R14 isolated window module

**OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE**

R10 measured lock reaching a fixed -19 stub. R13 never reached attach, so no
actual wrapper/instance conclusion exists. This module prepares only source and
host error/concurrency evidence. Expected helpful key: **toutiao, conditional**.
Playback, sound, real OH provider ABI and production caller routing remain UNKNOWN.
No APK/player patch, shared library, production resolver or admission is generated.

## Build and replay

```sh
python3 benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/build_host.py \
  --source-repo "$SOURCE_REPO" --out "$PERSISTENT_FRESH_OUT"
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_window_offline_module
```

`SOURCE_REPO` supplies the existing frozen registry and check_frozen.py. Every
build checks it before compiling. CC defaults to clang (override with `--cc` or
`CC`); compiler/linker actual tool paths and SHA, transitive system headers,
compiler version, commands, stdout/stderr/rc, object/test hashes are recorded.
Outputs are a host static object and a host test executable only, never a `.so`.
Use a new persistent OUT; private original logs are not rewritten or uploaded by
this recipe. Optional OH static-object compilation has **not** been performed.

`R14_SOURCE_REPO` can point Rust replay at a complete source checkout. Each selector
builds/tests in a unique `.private/selector-*` directory. The receipt selector also
rejects six tampered actual receipts. Build and failed contexts are retained.

## Interface and tests

`window_module.h` is the entire injected-ops interface. Wrappers are opaque tokens;
only a trusted unwrap callback returns OH identity. No production implementation
of unwrap or any other callback is supplied. All capabilities are mandatory.
See DONOR.md for lifetime preconditions and differences from f12c.

Tests use an independent provider event journal, not slot inspection. Four actual
pthread rendezvous points stop Request/Map/Unmap/Flush while another thread tries
same-wrapper, OH alias and duplicate-unlock calls; a different OH window completes
at each barrier. macOS lacks pthread_barrier_t, so the reusable barrier uses real
pthread mutex/condition wait/broadcast. No sleeps or simulated scheduler.

The public journals, source lock and build index are replay evidence. Raw stderr
and unmodified command paths remain at the indexed persistent private locations.
Actual object/instance evidence, exact provider ABI, caller-scoped paired routing,
build ABI review and a separate authorized window remain prerequisites to any
future deployment. This task does not relax R13 or assert a wall was passed.
