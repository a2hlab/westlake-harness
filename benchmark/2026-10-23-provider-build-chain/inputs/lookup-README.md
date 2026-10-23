# route-A provider source lookup: can hw248 build records bind the two mapped SHAs?

Read-only lookup for whether existing hw248 build records bind the G34-mapped route-A
`libsigchain.so` `6d5d5538…` and `libunwindstack.so` `d2c1cbc7…` to a frozen build artifact, source
snapshot, recipe and original build log. `dfx-provenance/missing.json` had marked these as not found
locally and not yet searched remotely.

Method: read-only `ssh hw248`; bounded text grep (`*.json`, `*.txt`, `*.sha256`, `*SHA256SUMS*`,
`*manifest*`, `*receipt*`) inside the RUNBOOK-named roots only. No whole-disk scan, no binary grep, no
build or script run, no device/ADB/REA/debugger, no permission change. Raw argv/rc/stdout/stderr are kept
under `$HOME/.local/share/westlake/route-provider-source-lookup-20261022/` (pinned in results.json).

## Result

| Object | Deployed SHA | Frozen build record on hw248 | Bound? |
|---|---|---|---|
| libunwindstack.so | `d2c1cbc7…` | `provider-v12/base-providers.sha256:20` and `base-providers-repro.sha256:20` → `/artifacts/providers/libunwindstack.so` | **yes**, manifest-declared |
| libsigchain.so | `6d5d5538…` | not matched within the bounded search | **no (bounded)** |

The frozen `provider-v12` generation does freeze a `libsigchain.so`, but at a **different** SHA
`ea7becd0…`, not the deployed `6d5d5538…`. `ea7becd0…` is also the route-a libsigchain seen in the G34
transaction-plan baseline — a different mapped instance, not proof of how `6d5d5538…` was built.

## Source / recipe / build log for the one match (revision 2)

For the matched `libunwindstack d2c1cbc7`, SHA equality means the **manifest declares** it:
`base-providers.sha256:20` and `base-providers-repro.sha256:20` both list `d2c1cbc7…` for
`/artifacts/providers/libunwindstack.so`. This lookup did **not** re-hash the remote artifact;
`byte_deterministic_runs=2` is a declared reproduction, not a re-run here.

- **Source snapshot.** `base-inputs.sha256` pins the AOSP source tree `./aosp/system/unwinding/libunwindstack/*`
  by SHA (`Android.bp`, the `*.cpp`/`*.h`/`*.S`, `include/`, `tests/`, plus `.git/logs/HEAD` and the
  `android-14.0.0_r1` remote ref). This is a manifest SHA pin of the source tree. It is **not** a per-artifact
  source→object binding and **not** source-closure.
- **Recipe source.** `libunwindstack/Android.bp` (the soong build definition) is pinned.
  `adapter/build/compile_app_native_loader_arm64.sh` is the app_native_loader compile script and is **not**
  the compile recipe for libunwindstack or libsigchain.
- **Original build log.** Not found in the bounded reads. Only AOSP git ref logs are pinned;
  `base-verification.json` and `independent-audit.json` reference libunwindstack only as a symbol owner and
  soname, not as a build record.

A pinned manifest is not source closure, and a list sharing the SHA is a manifest declaration, not a re-hash
of the deployed bytes.

## Conclusion and next real missing

`libunwindstack d2c1cbc7` is manifest-declared in frozen `provider-v12` (base-providers + repro), with its
AOSP source tree and `Android.bp` pinned by SHA and a declared 2-run deterministic reproduction. No original
compile command or build log was found, and the manifest pins are not source closure. Deployed
`libsigchain 6d5d5538` was **not matched within the bounded search**; `provider-v12` declares a different
sigchain `ea7becd0…`.

Next real missing:

1. The original compile command / build log for `libunwindstack d2c1cbc7` (manifest SHA, source tree and
   `Android.bp` are pinned; the actual build invocation and its log are not).
2. Any build record that produced the **exact** deployed `libsigchain 6d5d5538` — which generation sealed it,
   with its source snapshot and recipe. Not matched in the bounded search.

Path names and version labels are not treated as SHA proof.

No device, ADB, REA, debugger, build or permission change. Any tool access denial would have stopped the
lookup; none occurred (reads 01–05 all rc0).
