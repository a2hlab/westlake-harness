# Original WMC object rebuild and T29 b0e relink preparation

This delivery is an **offline, plan-only input audit**. It does not claim a reproducible WMC build yet. It preserves the original Ability38 compile command and T29 final link command rather than reconstructing a link line from library names. No compiler, linker, VM, SSH, REA or device command ran. No candidate WMC source exists in this delivery.

## Verified chain

| Item | Full SHA256 |
|---|---|
| Ability38 WMC source | `1844e81ba3183430040717e3fca7bffadf0d9a9724e55a543da1480aaf667a5e` |
| Original `oh_window_manager_client.o` | `f91b354ffa408fed7ff3002e1ed24a786b65621fd9b985c37db9b0fab461b8ed` |
| Ability38 original artifacts.json | `5db328cf263ba1575401d096b5afe3f5cecb3298066b14811a85a3d6570e223b` |
| T29 original final link argv JSON | `e960b1d1c12776cf6deceac1792abb0a60f3fb43d1de74eb935b88bd14d619cb` |
| T29 final bridge baseline | `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4` |

The MAIN `bridge-source-binding/check_binding.py` was replayed read-only and returned0. It joins the archived source/object/original compile rc0 to the T29 actual link rc0 and ELF bytes. This is record verification, not a new reproduction. [original-records.json](original-records.json) pins the original archive, receipts, logs, source and existing recipe. Original compile output is the retained `compile-window-manager.log` plus its artifacts command/rc record; this review does not relabel it as separate historical stdout/stderr streams.

## Inputs checked locally

- **Compile:** original385 argv tokens, including all include/define/prefix-map options; source selection, output and `.d` are explicit. Original `.o.d` contains624 entries:1cpp,576h,45hpp,2in. **615** have original relative paths and bytes in the local source-closure tar. **9 Ability38 headers** are instead present in its small source snapshot. Their full hashes are listed separately; correspondence to the original dependency content is not established by the historical `.d` alone. No same-name substitution is silently accepted.
- **Link:**111 explicit files:53objects (including CRTs),56shared libraries,1builtins archive,1driver. All111 have T29 receipt hashes; **106** are present in the local tar and all106 match the receipt. The other5 exist as local files and all5 match: exact macOS clang++, T18 candidate-audio.o, and T29 consumer-0.o/consumer-1.o/consumer-logger.o. The unchanged T29 consumer/logger objects must remain; using a pre-T29 bridge list would lose them.
- **Tool bytes:** Linux clang-15 `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913` and lld `8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4` exist in the local archive, but not at the recorded mounted SDK path. T29 macOS clang++ `6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1`, ld.lld `489c6d6628a56c027eac4dceee87910f7ca28b0c5a0e5188c32cb0108c08a837`, and readelf `2e8ccf494ea3ef05f10f54b3299a69253815f99f8aac8d54d32f3445725b35da` exist and were hashed. No tool was launched.

See [compile-dependencies.json](compile-dependencies.json), [header-gaps.json](header-gaps.json), [link-inputs.json](link-inputs.json), and [tools.json](tools.json). Missing mounted files are not missing archive bytes. Local existence observations do not characterize VM state.

## Existing retrieval source, no network required for these archived bytes

`$REPO/benchmark/2026-10-20-t18-build-evidence/source-closure/.private/archive-02/window.tar.gz`,84089815bytes, SHA `922e0291a10cc73a1cb6833c19c92c7baab163a7b1a23d92023657b1c40e8fa2`, provides the106 link files,615 compile paths,9 source-snapshot alternatives and original Linux tool executables. Exact member paths and hashes are in the input indexes. The existing source-closure packet/outer-success receipt is the prior remote provenance reference; this task neither downloads nor uploads. T29 objects/raw/bridge remain in `$REPO/benchmark/2026-10-20-t29-window-observation/.private/production-01`; T18 audio object remains under `$HOME/.local/share/westlake/t18-production/production-02`.

## Reviewable entry and exact commands

```sh
python3 "$DELIVERY/plan.py"
```

Default only prints [baseline-plan.json](baseline-plan.json); it creates no output and invokes no subprocess. `--execute` is intentionally unsupported. The plan is pinned by [plan-input-pins.json](plan-input-pins.json). It contains complete argv arrays, not shell-quoted approximations:

1. Original T29 link, same order and inputs, new output `bridge-original-object.so`; require exactb0e.
2. Original Ability38 compile, map the two documented producer roots into a new staged tree, redirect only object/dep outputs; require exactf91b.
3. Same T29 link, replace precisely its one WMC object and output path; require exactb0e again.

Aliases: `$REPO` this checkout; `$MAIN` main checkout; `$HOME` user home; `$MAC_SDK` existing DevEco native SDK; `$ORB_WS` recorded mounted original input root; `$HISTORICAL_ROOT_0/1` the two original producer roots retained verbatim in private records; `$STAGED_INPUTS` a future freshly restored input tree; `$OUT` a future exclusive new output directory. Do not execute unexpanded strings. The recorded link command's sysroot uses `--sysroot=...`; its explicit CRT/lib/builtins paths remain unchanged in ordering.

Before any future execution: all staged inputs/tool resources/system dependencies must be pinned; preserve original roots' prefix-map semantics; verify no include fallback escapes to unpinned files; use a new OUT, never a historical/frozen output. Every step must open persistent argv/stdout/stderr files **before** running and persist rc on success/failure/timeout. Stop on nonzero rc or any full-SHA mismatch. The existing T29 production recipe supplies the established raw recording and ABI/JNI comparison pattern; do not invoke its whole bridge→shim pipeline for this single-object baseline task.

## Unresolved prerequisites (execution remains blocked)

1. Original `-MMD` excludes system headers. The624-entry depfile is not a complete SDK/sysroot/resource closure; whole host OS dynamic-tool dependencies are also not closed. Only explicit link runtime files and identified compiler bytes are proven here.
2. Nine Ability38 header snapshots need explicit source-binding review and staged-path mapping; their availability does not by itself prove original compile inputs. Full object SHA equality is the required future baseline check, not an assumption.
3. Original compile is Linux; T29 final link used macOS driver bytes. `clang++` alias/resource directory and the complete original SDK/include tree must be restored explicitly. No silent compiler replacement or cross-host reproducibility claim.
4. Original compile cwd is not recorded in artifacts.json; the relative `sys/types.h` forced include and include search and staging prefix-map effects need review. The original command is retained exactly for that review.

No candidate compile, source patch, ABI acceptance or deployment authorization is included. The future executor must be reviewed after these gaps are closed; this plan deliberately offers no execution bypass.

## Offline verification

Three tests pass: original link order preserved, only WMC/output differ between links, and original compile options preserved except declared root/output remapping. Default preview rc0; `--execute` rc2. No compiler was invoked by tests. Validation and raw SHA indexes accompany this packet.
