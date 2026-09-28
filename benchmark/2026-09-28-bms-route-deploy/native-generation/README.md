# B6 #34: whole-generation build blocked by frozen inputs

The previous single-library swap failed the sealed loader identity gate; rebuilding only libsigchain cannot make a coherent generation. The prescribed whole-generation build now fails before compilation: `build-preflight.log` records exit 1 at `.work/product-tls-generation/frozen/toolchain/bin/clang-15`. No #34 board commands or deployments occurred. No identity checks were disabled. This is an input blocker, not a policy refusal or progress past getTheme.

## Required recovery

Restore the matching `.work/product-tls-generation` closure, including:

| Input | Pinned SHA-256 / evidence |
|---|---|
| `frozen.sha256` (327973 bytes) | `0bcca016a908da75a8c18c79745773974e9f8dcefbab1e8538e65ff9101044c8` |
| `tool_runtime.lock` (226 bytes) | `3c53b9a106da434ef1b52dc0ecfea0dc0996e90829ef666b9220c3ee181b83b9` |
| `frozen/toolchain/` | Preflight requires `bin/clang-15`; absent at every searched logical root. |
| `frozen/sysroot/` | Representative required `lib/aarch64-linux-ohos/libc.so` absent at every searched logical root. |

The marker hashes come from the existing `ROUTE_A_INPUTS.json`, not newly generated substitutes. The freeze ledger is needed to identify the payload contents; an arbitrary installed SDK is not evidence of this closure.

`input-search.json` checks 18 logical roots: the root and `src/` of seven 00.Workspace trees, westlake-bms-suite, and this worktree's bms import. `frozen-marker-search.txt` is a recursive basename search across the eight 00.Workspace/suite trees; it found eight provider `base-inputs.sha256` files but no `frozen.sha256` or `tool_runtime.lock`. `ledger-missing.json` additionally checks all 448 ledger entries for path availability: 170 were absent in those roots, comprising the two markers and 168 `upstream/openharmony-6.1.0.31/` entries. That audit is scoped to those logical paths; it does not assert that the upstream sources cannot be recovered elsewhere. It also does not certify hashes of files merely found by path.

Historical `.work/bionic-musl-provider/...` origin paths are **not** mandatory if checked-in frozen library hashes match: `generate_route_a_inputs.py` records unavailable origins explicitly. Recoverable frozen library copies exist in the 00.Workspace/suite trees. The absent pass1/pass2 provider outputs are generated prerequisites, not irrecoverable source inputs. Do not conflate these with the required product freeze.

## Build receipt and resume point

From the task worktree:

```sh
DOCKBUILD_MOUNTS="$PWD" ~/orca/workspaces/westlake-inputs/tools/dockbuild.sh run \
  -n b6-generation-preflight -- \
  'ROUTE_A_PROJECT_ROOT=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src WLASC_P0_TYPED_REJECT_CAPABILITIES=1 bash bms/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/build_target_in_container.sh'
```

After recovering inputs, use the existing generation flow to include bridge `0084775af8a47de3272170599726686b696ccd8b6c3efd0ea81854494d98f8f4`, regenerate the sealed manifest and child plugin, and pin/link the host. `build_target_in_container.sh` builds the host object; the full generation script performs the host link. Deploy/rollback the coherent generation together. None of those steps has been completed here.

## Contract result

Fresh lifecycle: **3 pass, 4 fail, 1 skip**, overall non-passing. `lifecycle.json` and `lifecycle-explain.md` retain the output. Caller, artifact-negative and symbol-negative checks pass against #31/#33 evidence. Wikipedia, regression quick, next-wall and NPE checks remain failed against that historical evidence. The new identity-gate selector matches zero tests and is **skip**, not pass; no new generation exists to validate. No new screenshots, loaded-generation SHA receipts or NPE result are claimed. Point-lighting delta remains zero. The #33 rollback evidence is historical; #34 did not re-observe the board.
