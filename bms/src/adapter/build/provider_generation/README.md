# Project-local ARM64 provider generation

This producer closes the gap between the r2 provider-name fixed point and a
new same-generation provider set.  It does not consume source, headers,
sysroot, libraries or compiler tools directly from `16.12-HanBing` while
building.

The two phases are intentionally separate:

1. `import_inputs.sh` is the only read-only origin acquisition step.  It
   copies the exact AOSP/OH subtrees and target/compiler inputs below this
   project's `.work/bionic-musl-provider/`, records provenance, hashes every
   local byte, rejects symlinks, and then makes the frozen closure read-only.
2. `build_generation.sh` starts a network-disabled, read-only container.  Its
   only source mount is the project-local frozen closure.  It first builds the
   namespace backend and then runs the ARM64 provider producer in strict mode
   (`-z defs`, Build-ID, SONAME and owner/edge smoke gates).

This producer is not a deployment command and cannot establish product or
device verification.  A successful build must still be consumed by the
provider fixed-point/identity verifier, the initial TP/prepare certificate and
the same-generation appspawn product manifest.

```sh
adapter/build/provider_generation/import_inputs.sh
adapter/build/provider_generation/build_generation.sh
WESTLAKE_PROVIDER_BUILD_RUN=repro adapter/build/provider_generation/build_generation.sh
adapter/build/provider_generation/verify_generation.sh
```

The current no-broad-stub replay is explicit so the immutable v11 verifier can
still be reproduced without silently changing its contract:

```sh
WESTLAKE_PROVIDER_GENERATION_ID=provider-inputs-v12-nobroadstub \
  WESTLAKE_PROVIDER_POLICY=no-broad-art-stub-v1 \
  adapter/build/provider_generation/verify_generation.sh
adapter/build/provider_generation/tests/run_no_broad_art_stub_regression_tests.sh
```

Use a new `WESTLAKE_PROVIDER_GENERATION_ID` for every intentional refresh;
existing immutable roots are never overwritten.
