# B6 #35: generation rebuilt, HelloWorld regressed, whole generation rolled back

Recovering the frozen inputs solved #34's build blocker, but a successful native build did not establish a working R155 replacement. The complete generation linked twice identically and passed its ELF/host ABI gates. On 5ea, HelloWorld returned to the desktop. The final child logged `libartbased.so` missing and `libartbase.so` failing to map its header, then exited. No repaired NPE behavior or new sigchain mapping was proved. Status: **blocked**, lighting delta **0**. All seven generation mounts were rolled back; the original HelloWorld and ZigZag screens were restored.

## Inputs and explicit deviations

Only reads/rsync were performed on hw248. `/opt/wl-src/.work/product-tls-generation` and `/opt/wl-src/upstream/openharmony-6.1.0.31` were copied into local ignored build inputs. Missing frozen binary copies were recovered from westlake-bms-suite; hw248's two prebuilt provider passes were used for the first target-only experiment. The final full build rebuilt both provider passes locally. No build ran on hw248.

`received-input-hashes.json` pins the received markers, clang and libc. The received freeze marker is `74bfcf7c…`, lock `a425147e…`, clang `b107ce03…`, and sysroot libc `ab5ad48a…`. The lock's declared clang SHA differs from the actual file. Its original text is retained verbatim below as requested (these are historical build paths, not the local execution environment):

```text
# Direct (non-container) route-A tool runtime, assembled 2026-07-31 on ecs-9f6c.
# The historical docker-image pin (clang-15 4806f4f1...) is not reproducible on
# this host; this generation uses the local OHOS SDK toolchain instead.
image_id=none:direct-build
toolchain=/home/yao/ohos-sdk/native/llvm
toolchain_clang15_sha256=0f6c31bee51b229c3f25418571cfa01cf0ddb12f6779d5b7df49d6c41ce26d08
sysroot=/home/yao/ohos-sdk/native/sysroot
```

All compilation used local amd64 `dockbuild.sh`. The bridge used the previously locked westlake SDK; the full generation used the recovered hw248 toolchain. `input-drift.json` records changes against the original input ledger. The generator regenerated the ledger, and `--verify` remained enabled. No runtime identity gate was disabled.

`frozen-payload-drift.json` records 16 checksum differences introduced by the Mac copy: eight uppercase/lowercase netfilter header pairs, reached through both sysroot include paths. The remote `xt_TCPMSS.h` and `xt_tcpmss.h` have different bytes; the local paths have the same inode and lowercase-file SHA (`case-collision.json`). The original manifest is retained in ignored `.work/product-tls-generation/frozen.hw248-original.sha256`; `refresh_frozen_hashes.py` pins the actual local bytes and records every difference. This copy is **not byte-identical** to the remote freeze. Preserve case sensitivity for any future consumer of those headers.

## Build integration and retained failed attempts

- The old `0084775a…` bridge had no SONAME/Build-ID and carried an unused `libc++_shared.so` dependency. The existing production build script now supplies `-nostdlib++`, SONAME and SHA-1 Build-ID; the signal-handling source is unchanged. An attempted additional `-z defs` failed against SDK libc's absent special-handler declarations and was removed; the two actual target-musl exports were independently verified. Both build logs remain.
- The host now includes the existing `oh_dlns_abi.h`, and its full-build include path includes that header directory. The recovered SDK required the existing `WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1` option.
- Certified v12 providers remain unchanged. The generated provider set substitutes the newly built sigchain, and the final verifier explicitly checks its SHA against the bridge input. The input ledger includes the bridge binary, source and build recipe. The first frozen-base substitution attempt and its rejection are preserved in the logs.
- The R45 identity pins and local dynamic-root inputs were updated from read-only 5ea copies: bridge `84695d62…` / Build-ID `e5e9bd83…`, runtime `9ccf64f8…` / Build-ID `db3066fa…`. These receipts supersede the historical origin description in the frozen R45 README for this experiment. No board native-root files were replaced.
- This full stock build carries v12 libart `be688d0f…`, whereas the accepted R155 board used `59e1bb45…`. It is not a single-library experiment, and the runtime failure cannot be attributed solely to the sigchain bridge.

`build-generation-r5.log`, `generation-verification.json` and `target-verification.json` record two deterministic builds, successful final host linking, OH 6.1 host ABI checks, and resolved transitive symbol edges. That verifier's historical `rebuilt_provider_members` list omits the added bridge; the explicit bridge equality check, sealed manifest and deployment payload receipts are authoritative for it.

| Artifact | SHA-256 |
|---|---|
| Generation | `f331328985df5b6d2c04b4b7b63bb71544673430d70a96b7a5165cea3174877b` |
| libsigchain | `5a26b5b8ed156233fde6854af5c0a4590d2043b9a0128acb25e4af35ffd84d04` |
| Child plugin | `aecea2401dbaaa8be2d7e2c0b79139efc35d85bb6cf73b818f99e8680034aa80` |
| appspawn-x | `43f629c1ae4efd18cb47781ac63fa7de67443afdc88e9472abfa87ae40a2f7a0` |
| Runtime provider | `34db8f9aa2481bf84c7c3b01e3089dcd656c85bffd7f68bfd5546fbaf3ea0ca4` |

To rebuild after recovering the recorded inputs, run the production bridge compiler in dockbuild with the westlake SDK overrides shown in `build-bridge-identity.log`, run `refresh_frozen_hashes.py`, `generate_source_closure.py`, then `prepare_candidate.py <expected bridge SHA>`, and run `build_generation.sh` through dockbuild. Do not use this failed generation for demonstrations.

## Board experiment and rollback

Board: `5ea34a4500000000000000001123012c`, same boot `56e521b3-858f-4fbf-8e35-daec29525c93`. `deploy_generation.py` checks the held cx-t0 lock and boot before board commands, stages and hashes the entire payload, stops children and parent, switches mounts, and checks the restarted parent executable. `deployment.json` retains all payload hashes, previous target hashes and rollback state.

| Trial | Observation | Evidence |
|---|---|---|
| HelloWorld r1 | AMS socket EPIPE/EACCES, no child | `evidence/helloworld/` |
| HelloWorld r2 | PID 32081, exit203; source maps 203 to loader error13 (external-root mapping) | `evidence/helloworld-r2/` |
| HelloWorld r3 | PID 7435, libartbase load/header failure, ExitCode:1; parent reports exit0; final desktop | `evidence/helloworld-r3/` |

The service restart recreated the socket with wrong group/label. It was restored to the accepted reproducer's exact `660:0:6005:appspawn_socket` identity. The r2 parent mapped an old `/system/android/lib64/libwestlake_thread_guard_registry.so`; both that alias and `/system/lib64/libwestlake_thread_guard_registry.so` were then bound to the new same-inode provider. These corrections did not disable sealed checks.

The r3 child receipt proves the new host/plugin and unchanged framework/boot hashes. Its early maps snapshot does **not** show the new sigchain; it is not evidence the bridge was never mapped later. Parent stdout/stderr were `/dev/null`, so absence of WLCGATE hilog lines cannot establish success. No Wikipedia or repaired-generation NPE claim follows from these trials.

Rollback removed the seven mounts and verified all original hashes before restarting the original parent (PID 9645). Baseline desktop observations then captured HelloWorld PID10528 and ZigZag PID11533. The assistant inspected the final images: both show their own UI. These are rollback checks, **not** successful final-fix quick runs. Screens for outer review:

- Failed candidate: `evidence/helloworld-r3/final.jpeg` (desktop).
- Restored HelloWorld: `evidence/rollback-helloworld/final.jpeg`.
- Restored ZigZag: `evidence/rollback-zigzag/final.jpeg`.

Full raw records remain on the VM in `~/a2hlab/board/b6-generation-hw-5ea-r{1,2,3}` and `b6-generation-rollback-5ea`; local raw copies are ignored under `bms/src/.work/b6-raw-evidence/`. Checked-in hilog excerpts retain original line numbers.

## Verification and boundary

Fresh B6 lifecycle: **3 pass / 5 fail / 0 skip**. Caller, artifact mismatch negative controls, and symbol coverage/missing-symbol negatives pass. Wikipedia, final quick regressions, progress past getTheme, NPE retest, and live identity gate fail. The new identity selector now exists and fails on missing proof. `known-answers.log`: 69 tests, 2 skipped, successful suite. APKs, installer, framework and boot files were unchanged on the board. No push. This is a runtime bring-up blocker, not a policy refusal.
