# Task 58 follow-up: preserve R155 dlopen caller namespace

The previous static review treated the wrapper local-array/code-shape difference as harmless. That was wrong: R155 ends `WLSCPL_OpenPreparedNamespace` with **b dlopen**, while task58 used **bl dlopen**. OH musl passes its caller return address to `dlopen_impl`; a real call presents the default-namespace child plugin, while the tail call preserves the sealed NativeLoader caller. The 26 original providers and ordered NEEDED lists were already correct; changing a library filename would not restore this call boundary.

The only functional source edit changes the prefix from an automatic array to a static constant, restoring R155's emitted tail call. All canonical/prefix/flag checks remain. The locked build regenerates manifest, child and host identities normally. `loader-tail-call.patch` and the final loader source retain the edit; the remaining source snapshot and recipe provenance are in `../task58/`. No namespace access or artifact verification is relaxed.

## Offline gates

The final instruction gate requires **b dlopen** and rejects the previous **bl dlopen** artifact as a negative control. Host/child/provider dynamic tags match the previous R155-aligned lists. All three reproduce twice; 26 R155 providers retain original bytes; the explicit closure has 319 libraries / 2830 NEEDED edges. Six closure controls (one positive, five negative), four missing-sigchain-export controls and the V1 host tests pass. `static-dispositions.json` records this focused correction to the prior full static inventory.

## Device gate

The candidate generation **6cb40cd6** was activated with host **b7205719**, child **03aa6216**, runtime-provider **3aa5d169**. The observer read back these identities on boot **42f125dc-5d9e-405e-91b4-0f9e929c3c5f**, then HDC lost its remote status marker before any app click. Subsequent HDC listings were empty and the Mac USB tree contained none of the boards. No child maps or screenshot exist for this follow-up. The last observed board state is the active candidate, **not a completed rollback**.

On reconnect, first verify the boot ID and active generation; use `deploy.py down` only on the same pinned boot, or restore the saved B5 mounts if the board rebooted. First require exactly one offset-zero ART mapping and one route-a libopenjdkjvm mapping from the launched child, then inspect HelloWorld before proceeding to Wikipedia/NPE and ZigZag. A failed control triggers whole-generation rollback.

## Validation

Known-answer suite: 69 tests, 2 skipped, 0 failures. Lifecycle at transport stop: 3 pass / 5 fail. Caller identification, mismatch rejection and sigchain exports pass. Live child identity and all UI/NPE scenarios remain unverified or failed. The prior task58 success in the identity scenario is not reused for this new generation.

The mapping gate was replayed against actual archived evidence: R155 child25183 maps pass, previous task58 double-ART fault maps fail (`mapping-gate-controls.json`). The outer loop confirmed that all three boards and the Android device disappeared together and requested a physical hub check. The 5ea lock remains held while the active candidate awaits reconnection; this is a checkpoint, not a completed rollback or final acceptance.
