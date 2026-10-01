# N11c loader probe (offline)

R3 recorded `LOAD_ERROR:10` and exit 123 but did not identify the failing library or guard. This candidate adds per-library diagnostics only; it is not authorized for deployment while U9 is running.

## Reproduction and scope

- Baseline child `163da8055b69e049df6999b6f37ab4d77b2ea5f61cbb3f59fa4309cbe76bf4d2` was reproduced byte for byte from the N11b recorded object inputs and frozen compiler/linker commands.
- Candidate and independent repeat both produced `875db30d9c7dab20eca16c3f1326cc03919924e0c24b333ac08ecf16e98fe8a0`. Only `sealed_child_provider_loader.o` changed.
- `abi_diff.py --calls` reports exactly one changed call set: `WLSCPL_LoadSealedProvider` adds `HiLogPrint` and `dlerror`, removes none. Exports remain 2/2, with zero signature drift or consumer breaks. `LoadWithOps` is inlined into this exported function by the compiler.
- Both child dynamic dependency lists remain `libc.so` only. HiLog is a weak reference to the already resident host logging dependency, so diagnostics do not introduce another loading edge. If no resident HiLog symbol resolves, logging is skipped and the future evidence gate must fail; provider behavior remains unchanged.
- Every `open_local_now` iteration logs a zero-based index, closure total and absolute library path before opening, then `null=0` on success. On NULL it logs `null=1` and the immediate `dlerror()` text, or `<none>` if the callback consumed the error. All admission, namespace, handle comparisons, cleanup and return codes are unchanged. See `probe.patch`.

## Package and gates

`prepare.py` creates `westlake-generation-n11c-child-u9-875db30d` from the U9 bundle, changes only the child bytes, and updates its baseline references to U9. J10g, T7e images, N10b runtime and frozen installer remain unchanged. The package retains `rollout_ready=false`.

The first production dry-run rejects unregistered native findings. Exact semantic comparison against approved U9/N11b reports auto-approved 154 identical findings. Two N1 findings retain the N11b NOLOAD sites but now cite the new `n11c-child.c` source member; they remain in `needs-outer-review.json` for review. No gate was weakened and no board lock was taken. Final production dry-run must pass after registry landing and approval before a future window.

Build with the recorded workspace objects visible to `dockbuild.sh` (`DOCKBUILD_MOUNTS="$WORKSPACES"`) and a fresh `N11C_BUILD_OUT`. The first attempt failed before compilation because the historical object directory was not mounted; the rerun passed. `build-receipt.json` records portable commands, object hashes and source hashes. Binary artifacts remain in `$WORKSPACES/westlake-n11c-probe-build/`; this directory is not a deployment instruction.
