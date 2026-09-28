# Runtime generation red-team gate

This directory contains an independent, read-only admission verifier for the
Route-A runtime generation. It does not import a conclusion from an older
`generation.json`; it re-opens the exact current source files, ELF files, link
receipts, namespace graph, and FD admission records, then hashes every observed
input again before returning.

The verifier answers one narrow question:

> Are these exact host source/artifact/receipt bytes eligible to be offered to
> the device owner for a later production-init test?

`PASS` never means `device_verified`, first frame, Unity load, SELinux, or
truly-cold success.

## Run

```bash
./run_tests.sh

python3 verify_candidate.py \
  --project-root /absolute/project-root \
  --source-root /absolute/project-root/source-snapshot \
  --build-root /absolute/project-root/generation-output \
  --manifest /absolute/project-root/generation-output/meta/candidate.json \
  --readelf /absolute/project-root/toolchain/bin/llvm-readelf \
  --report /absolute/project-root/generation-output/meta/redteam-verdict.json
```

The source and build roots may vary per lane, but both must be below the
integrator-selected `--project-root`. All manifest paths are canonical relative
paths. Symlinked inputs and `..` escapes are rejected.

## Candidate contract

The authoritative schema name is
`westlake.runtime-generation-candidate.v1`; the executable checks in
`verify_candidate.py` are stricter than a shape-only JSON Schema would be.
The manifest must contain:

- one current-byte source snapshot with per-file SHA-256 and a deterministic
  aggregate digest;
- every deployable/generated or immutable-base ELF, with path, SHA-256,
  exact 40-hex GNU Build-ID, namespace, provenance, and exact SONAME for DSOs;
- explicit namespace search paths/imports; two equal SONAMEs are allowed only
  when they are unreachable from one another;
- exactly two dynamic roots, `android_runtime` and `adapter_bridge`, including
  caller, callsite, source hash, selected provider, nonzero failure contract,
  identity anchor, and first side-effect anchor;
- the three source contracts `runtime_root_failure`, `startreg_failure`, and
  `preload_throwable_failure`;
- one byte-pinned `westlake.link-argv.v1` receipt for every generated ELF,
  including strict linker argv and every project-local source/build input;
- one embedded `.westlake_generation` string shared by every generated ELF;
- one sealed-FD admission record for each dynamic root, with stable path/FD
  identity before and after load and exactly one namespace mapping.

The test builder in `tests/test_verify_candidate.py` is the executable example
of the complete manifest. It is synthetic oracle code and is never a product
build recipe.

## Gate coverage

The positive candidate must pass all 20 gates. Single-variable mutants prove
rejection of:

1. stale source JSON and symlink input;
2. ARM32, wrong SONAME, short Build-ID, and RUNPATH;
3. omitted dynamic root, missing callsite, and root fake success (the positive
   control also requires identity before first side effect);
4. runtime-load, missing-startReg, and preload-Throwable fake success;
5. namespace-unreachable provider and same-SONAME reachable ambiguity;
6. relaxed linker argv, absolute input escape, and unresolved strong UND;
7. mixed-generation ELF token;
8. FD path swap and duplicate mapping.

No generated binaries, verdict JSON, logs, or temporary work directories belong
in Git.
