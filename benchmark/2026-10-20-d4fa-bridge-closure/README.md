# Exact d4fa bridge producing inputs recovered

The earlier `UNKNOWN_EXACT_BUILD_CLOSURE` entry must not be replaced merely because a current AudioTrack source looks similar. This inspection found the original producing input chain and verified the actual d4fa output. A new independent baseline rebuild has **not** been run by this lane.

Let `ORB_WS` be the existing mounted Orb workspace (`$HOME/OrbStack/a2hlab/home/<VM-user>/a2hlab/ws`). The old `LEGACY_VERIFY` prefix resolves to that same workspace for read-only inspection. The original compiler prefix-map flags still require deliberate preservation during reproduction.

| Stage | Exact input / evidence | Observed result |
|---|---|---|
| Original bridge15 | `$ORB_WS/out-touch21/fd/bridge15/artifacts.json` | 50 source hashes and 900 header hashes match existing bytes; original audio source8e922c5d and objectbca071e6 agree with recorded pins. |
| Reused incremental objects | `out-focus34/incremental/build.json` and `build-history.jsonl`; `out-ability38/native-policy/artifacts.json`; `out-ability38/native-stack/artifacts.json` | All52 objects in the final ability38 reused-object dictionary match their original SHA. The link command has109 explicit file inputs, all present. |
| mc46 final change | Westlake `ddb2f480e2b70af3e338304602ffe0f4b12c84bd`, `westlake-mc46/framework/core/jni/oh_mediacodec_shim.cpp` | Only MediaCodec changed: new objecta0b78a1c replaces original06c0e052; final2015744-byte library is exactly d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b. Audio object is retained. |
| Exact compile/link entry | Harness triage46 `benchmark/2026-09-26-toutiao-crash-triage/scripts/build_bridge_mc.py`, commit2191c8c9fa15bf0cc82c150d816508b580c26730 | Reads ability38 artifacts, checks every reused object, selects `compile-oh_input_bridge.cpp` and `link-bridge`, replaces only the MediaCodec input/output arguments. This is the producing recipe, not generic current CMake. |
| Audio original command | `out-touch21/fd/bridge15/artifacts.json`, `commands` element containing `oh_audiotrack_shim.cpp` | Exact compiler argv and source/header profile are available. The original source matches the T18 source8e922c5d, but baseline object equality must still be reproduced before mutation. |
| Original toolchain | `toolchains/ohos-sdk/native/llvm/bin/clang-15` and `lld` | Actual compilerb107ce03 matches the original recorded compiler hash. Linker8583bdc8 is present. Current clang++ symlink uses a ccache wrapper; direct clang15 needs `--driver-mode=g++`, not an unrecorded SDK substitution. |
| Raw logs | `out-touch21/fd/bridge15.log`, `out-touch21/build-fd.log`, focus34 object logs, ability38 policy/native-stack compile/link logs | Original logs survive. The bridge15 log says50 objects/0 failures; ability38 command records contain original rc. No independent final mc46 stdout/stderr/rc receipt was found; the historical triage text only summarizes its hashes. |

## Immediate handoff

Video_plan has the exact mounted paths and owns the build. First take private immutable copies of the original recipe,52 objects, patched MediaCodec object,109 link inputs and toolchain; preserve full original source/header pins and incremental command history. Run an unchanged baseline relink with the actual mc46 object and require exact d4fa. Separately compile the unchanged original AudioTrack command and require bca071e6. Capture argv, stdout, stderr, rc, hashes and toolchain identities at execution time.

Only after those controls pass, derive the smallest getter change from the exact old AudioTrack owner, retain every other original object and use the same link chain. A fresh baseline log can close current reproducibility; it must never be called the missing original mc46 log. Any mismatch requires comparison before a candidate is described as deployable. No board operation, runtime replacement or compile was performed by this lane.

The input inventory uses aliases and full hashes; source bytes remain in the original mounted store. It is not yet a durable archive of the entire closure. Original harness evidence is also available in sibling ability38/triage46 Git objects (ability38 artifacts commitc7a4a54c536faf2f7ac0208218417a79c132dc0c). Orb CLI timed out but the mounted filesystem worked; hw248 targeted search did not locate this specific original build tree and is not claimed exhaustive.

## Subsequent fresh control (separate from historical logs)

Before this report froze, video_plan completed a new Mac baseline relink at `$HOME/.local/share/westlake/t18-production/baseline-mac-01`. This lane independently read rc0 and hashed its actual output: exact d4fa,2015744bytes. `results.json` pins the new argv/input list/stdout/stderr/rc/result separately. This confirms the new link control; the old AudioTrack recompile and changed production candidate remain pending here. The missing historical mc46 full execution logs are not reconstructed or relabeled.
