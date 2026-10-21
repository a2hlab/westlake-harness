# G24 host build readiness — independent G16 source review

The misleading shortcut is to identify the deployed host from `n4-host.c` alone, or to substitute the later N5 loader build for the G24 `eebd` loader. Exact local outputs and G24 journal pins now identify two reusable source-build paths. **Source-level incremental candidate work is feasible with the retained inputs; strict end-to-end provenance is partial, and no new build was executed.**

`input-audit.json` records actual local file hashes, not filename inference. All pinned comparisons in this audit match: 73 host compilation inputs and their 73 frozen copies, 17 explicit reused host link inputs, 4 host tools, 6 original host logs, 17 N3 source files, and 3 N3 toolchain/libc files. Both U13 payload files and both corresponding original build outputs match. Local inspection returned rc 0. This is not a compiler/test/preflight result.

Use `$WORKSPACES` for the parent of the worktrees. `$MAIN=$WORKSPACES/westlake-harness`, `$BMS=$WORKSPACES/westlake-harness-bms`, `$DEPLOY=$WORKSPACES/westlake-harness-bms-deploy`. Main observed at `908ea20dfd2a3f55db20a5bed5455c4410e5d3b7`. All writes are confined to this report directory.

## Exact G24 identities

Source: `$HOME/.local/share/westlake/commercial-game-20261021/g24-window02/journal.json`, `plan.expected`; full journal SHA is in `input-audit.json`. This consumes existing evidence and does not reconnect.

| Journal target | SHA256 | Independently hashed local matching output |
|---|---|---|
| `/system/bin/appspawn-x` | `2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e` | `$BMS/benchmark/2026-10-02-u13-single-native/.artifacts/host/baseline/appspawn-x-candidate1` |
| `/system/android/lib64/libapp_native_loader.so` and route `74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac` alias | `eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c` | `$DEPLOY/bms/src/.work/n3-native/flutter/libapp_native_loader.so` |
| Loader under route `74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d` | `a3d4b80d943dd78972e5689a29810406f97056e0ce8f040d2ec24ac3618d9929` | Different journal object; excluded from the `eebd` build claim |

Both matching U13 payloads also remain in `$BMS/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4/native/`: `payload/runtime/appspawn-x` and `payload/route/libapp_native_loader.so`. Its `package.json` mounts the route loader to the system alias. No claim is made about a live winning namespace.

## Host: usable exact-baseline incremental build path

Read the original `$MAIN/benchmark/2026-10-02-u13-single-native/host-build-receipt.json` and `build.py` (archived here). The baseline command pair `commands[0:2]` reproduces G24 `2a87118e…`; the candidate pairs produce **different** `c2883376…` bytes. Do not select that U13 candidate as the G24 baseline and do not launch the whole multi-component build merely to build the host.

The source/patch sequence that determines the present host is:

1. U10 provides the retained compile/link recipe (`benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json`, SHA `8eaec4315b379e1e3675b38a5e298271716279c049db1ba3ede5c3815ea0cb40` as pinned by U12).
2. U12 `benchmark/2026-10-02-u12-private-zlib/inputs/baseline-stock-host.c` is `507bf160dfae87851345c8fc564c9378356a773cc84272d2ec0635b1c0ef0c50`; `route.patch` records the scoped zlib route delta. The complete applied `candidate-stock-host.c` is `8be12abcb99ccc5f7fbd01f31d04b41a0b47db83d0ceac7f6bfda872b34e7b90`. Its receipt records two identical `2a87118e…` outputs and names the earlier reviewed U11 donor.
3. Required companion `resident-compat.h` is `e4f7321547d6cafac5734a7ff3b9338cc0e8a93e94ff5932bafa3caa23cb35e0`; `zlib-route.h` is `695b7a95ecc9de90e92b8b80f5443182dcef601c7d45facb6291c141527eea32`. All three U12 files match U13 `sources/baseline/host/` byte-for-byte. The U13 `native-checks/n4-host.c` sidecar matches the complete C file, but does not alone carry its header/recipe closure.
4. U13 `host.patch` changes the candidate zlib header's package list; that subsequent delta is **not** in G24 `2a87118e…`. Use the U13 baseline and U12 inputs for this identity.

Original Mac clang is `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/clang`, SHA `6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1`; adjacent `ld.lld` is `489c6d6628a56c027eac4dceee87910f7ca28b0c5a0e5188c32cb0108c08a837`. Both actual files match. Preserve the recorded prefix maps, source path and flags. The recipe uses the retained b68 frozen sysroot and 17 explicit `.o`/`.a` inputs (including the b80 service object). Every exact path and hash is in `input-audit.json`.

The six original compile/link log files exist under `$BMS/benchmark/2026-10-02-u13-single-native/.artifacts/raw/host-{baseline,candidate1,candidate2}-{0,1}.txt`; all match their recorded hashes. The original receipt explicitly records `exit_code: 0` and `runtime_tee: true` for each. Empty successful compiler output remains empty; no synthetic output was added.

**Limit:** this is an incremental source rebuild using retained objects. The receipt's 17 explicit link inputs omit the individual `-l` resolutions, version script and implicit/transitive inputs. This audit finds all 14 named library candidates and the version script and records their present hashes/search order; it does not retroactively establish which historical bytes were selected. Source rebuilds and historical patches for every retained object are not established. Do not describe this as a proven clean rebuild of the entire host from source.

## ANL: original N3 source and toolchain found

The relevant source directory is **`$DEPLOY/benchmark/2026-09-30-n3-native/flutter/`**, not the later N5 directory. This N3 directory is absent from the current main tree but present in the deploy worktree. Its retained `source-sha256.json` matches all inspected local source files:

| Input | SHA256 |
|---|---|
| `app_native_loader.c` | `aa1cd7c09164f1e6eefb928e8bc856ecb4df3ce22f81842d6595911c5c1f1d06` |
| `flutter_domain.inc` | `0117797953a738f248d13f9f8be04e76d6052f1e0f70cf0f0e5c88f16472c15b` |
| `app_native_loader.map` | `cf01d4631974151f85f0944b233efda617bb9a2338dbef163df568dfafc592d3` |
| frozen `toolchain/bin/clang-15` | `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913` |
| frozen `toolchain/bin/ld.lld` | `8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4` |
| frozen `sysroot/lib/aarch64-linux-ohos/libc.so` | `ab5ad48a82295e6ec144aaac730bfa053e744e4903c01d51707ce0935385d905` |

Frozen root: `$DEPLOY/bms/src/.work/b68-generation/.work/product-tls-generation/frozen`. These are the Linux toolchain inputs; this audit only hashes them and does not execute them on macOS or probe a VM. Source-index C-file identity alone was insufficient: `flutter_domain.inc` is a substantive included implementation. The U13 native sidecar has the exact N3 `011779…` include. N5 retains the C file but changes the include and emits `6d001bb8…`, so its successful build cannot stand in for `eebd…`.

The original entry is `bash benchmark/2026-09-30-n3-native/build-flutter.sh --anl-only` from `$DEPLOY` in its recorded Linux environment. Its first two compiler commands compile `flutter/app_native_loader.c` into `anl.o`, then link the map + `anl.o` + `-lc`. It subsequently compiles/links the ABI before the `--anl-only` early exit; the name does **not** mean only ANL gets rebuilt. The existing script also checks the retained N1 runtime file before compiling, though that file is not an ANL link input. It exists locally and is inventoried. Do not silently remove these steps or call a newly invented wrapper.

`build-final-loader.log` contains the exact `eebd…` output SHA and original frozen-check output; its SHA and sanitized copy are recorded. The preceding `build-loader-host.log` names `d1325e86…`, which is a different earlier attempt. N4 `package.json` records `eebd…` before and after, retained from N3b; it is not an N4 rebuild. G24 payload and the original N3 output still hash to `eebd…`.

**Limit:** the located N3 final log does not contain an explicit process rc or capture metadata for stdout/stderr. The script's success path and output hash are evidence, but not a fabricated historical rc=0 receipt. Nor do the inspected N3 manifests enumerate every transitive system header/implicit linker input or a complete historical patch series. The complete applied source is present; strict provenance remains partial.

## Minimal next step and boundaries

An independently authorized build owner can reuse the exact host baseline command pair and the original N3 entry with the pinned source snapshots. Before evaluating changes, reproduce the exact baseline while retaining real rc/stdout/stderr and complete dependency/link-input capture. Keep the old receipts unchanged. If historical strict closure is required before that build, the specific missing evidence is the host resolved-library/implicit-input binding and N3 command/rc/capture record plus full dependency manifest—not a missing `n4-host.c` or an absent VM inferred from old timeouts.

No candidate design is proposed. No compilation, deployment, device command, REA, preflight, network connection, permission change, registry edit or main-tree edit occurred. G14/T38 and previously refused operations remain untouched. Existing runtime limitations and lack of live winner/UI proof remain in force. This is build-preparation evidence, not deployment approval.

To repeat only this local inspection: `python3 inspect_inputs.py --workspaces "$WORKSPACES"`; stdout is JSON. `archive-index.json` distinguishes original byte hashes from sanitized archive hashes. Original sources/artifacts/logs remain at their persistent paths. `landing-paths.txt` enumerates this report's files only.
