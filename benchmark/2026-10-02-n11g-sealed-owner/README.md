# N11g: explicitly open admitted libraries in the sealed child namespace

N11f was refuted: bridge and runtime each had two mapping bases despite the same inode. Its callback fallback in the **child plugin**, not appspawn-x, tail-called plain dlopen. This candidate changes that one callback's fallback to dlopen_ns in the already-prepared closure_namespace. It does not alter the requested file, path/flag admission, namespace inheritance or frozen providers.

The final child is **85ef355ce1a2d70d05181ffd0dfd71d200c21e877bf1e106a139221981fb9190**. The frozen recipe exactly reproduced N11f **f1b43386** before building the candidate twice, byte-identically. Candidate and package are durable under `$WORKSPACES/westlake-inputs/generations/n11g-u9-sealed-owner-v1/`. Only `/system/lib64/appspawn/libwestlake_android_child.z.so` changes versus signed U9. No board was accessed or locked.

## Provenance and actual linked-artifact gates

Source: approved `benchmark/2026-10-02-n11g-sealed-owner-blueprint/` and N11f's archived child sources/recipe (`benchmark/2026-10-01-n11f-owner-callback/`, outer land a4c3d23824). The explicit namespace open is copied from its existing RealOpenLocalNow implementation. `n11g-vs-n11f.patch` shows the single callback change. Compiler SHA b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913; no toolchain or other linked source was substituted. Build-r1 compiled successfully but its repeat receipt indexing had a KeyError; the corrected orchestration used a fresh build-r2 directory. This was not an ELF/source compile failure; both build-r1/r2 candidate bytes were identical.

- ABI versus deployed U9 dc73a28d and exact reproduced N11f: zero export additions/removals, signature drift or consumer breaks across **103** actual U9 consumers.
- Calls versus N11f: only **WLSCPL_OpenPreparedNamespace** changes. Calls versus deployed U9: four functions, three inherited from already-reviewed N11e/N11f result-channel lineage. Candidate callback disassembly calls dlopen_ns and contains **no plain dlopen call**.
- NEEDED, SONAME and RUNPATH match. Import delta versus N11f removes dlopen and adds none. Versus U9, snprintf/strnlen are inherited from N11f (not new N11g imports). The full ELF surfaces/section/relocation reports are attached; section offsets change with code/string placement.
- Only sealed_child_provider_loader.o changes from reproduced N11f; sealed_provider_manifest.o and all other objects remain exact. All deployed system path/gate bytes remain present.
- Raw deployed_strings_diff reports **2 drops / 23 additions, rc1**. Review maps the two drops to readelf rendering: the ENTRY_RESULT bytes remain present with a nested printed offset, and the scalar/pointer row changes textual rendering with layout. The manifest object is identical. Additions are result-channel lineage plus explicit callback/typed-failure diagnostics. Reviewed allow-list run returns rc0; this is **not** claimed as an unqualified zero-diff result.
- G1/G2 pass. Frozen package/full baseline checks have zero violations. Tests: **5** actual callback/result-channel/window-safety tests and **18** runner tests pass.

## Ownership, typed failure and live marker

Exact bridge/runtime requests preserve N11f's resident-handle return convention. Missing protected owner returns NULL with WLSCPL_FAILB_OWNER_PUBLISH_LATE, never a default load. Other admitted paths are opened with unchanged flags/path through dlopen_ns(&closure_namespace,...); failure captures current dlerror into the typed channel and returns NULL. No SONAME-only redirect is added: U9 libandroid's SONAME overlap must not redirect its requested file to runtime.

Logging resolves HiLogPrint from the already-resident runtime handle, with no weak logging import or default preload. Every callback records `[N11g-SEALED-OPEN] route=resident|sealed|reject path=... owner=... handle=...` when this channel is available. Smoke requires a **live real callback marker**; a silent marker means an ineffective probe, not evidence that the callback was unused. Existing loader-stage branch0 alone is insufficient.

The resident-handle convention is unchanged. Its real-work AppSpawnXRuntime destructor eventually calls dlclose; OH6.1 musl's source `src/ldso/dlclose.c` implements a weak invalid-handle check instead of unloading (read-only source from hw248 OH6.1 tree, SHA in musl-dlclose-source.txt). No new ownership convention, global handle registry or library inheritance edge is introduced.

## Native exception review: not armed

Manifest **6d46334d311065373beef2223cacf4c1a986f21ebb88a643d3f7765d4ea9065f** has **154 auto-identical approved findings**. One inherited ART NOLOAD finding has new source/manifest binding: issue **d75f371b0495**. N1 = 51 excepted / **1 rejected**, N2 = 103 excepted / 0 rejected. `outer-review-proposal.json` requests the same scoped rationale as approved N11f ab9573e6: provider dlopen_ns at line349 dominates ART NOLOAD line360, but the scanner cannot see its DT_NEEDED mapping. Calls in this function are unchanged from byte-reproduced N11f; runtime N11f branch0 is the prior ART/JVM evidence. The proposal is **not approved** by this lane.

Production dry-run therefore **refuses**, gates_passed=false/deployable=false; rollout_ready stays false. Nothing bypasses the gate. After outer registers this final binding and approves the plan, `approve.py --outer-approved` first reruns the strict gates, then jointly arms bundle.json and updates package.json's bundle SHA, runs preflight again and restores both files on failure. The current unarmed bundle SHA is in package.json/results.json.

## Proposed 61b observation and retreat

`plan-61b.json` is **pending approval**, base signed U9, only 61b, <=30 minutes with no new key after minute20. Start with board_run --detach after outer approval; unique N11G_RUN_ID/output per window. after_lock verifies 318 U9 assertions, starts continuous hilog/proc/fault capture before applying the child, and executes the unchanged transaction with deployment gates. Package reference metadata retains U9's legacy 119-file fingerprint domain; the **live** smoke/final domain includes installation-chain paths (123 files), expected RUNTIME **a2919b793eb6**, BOOTIMAGE **4db882a81732**. Do not confuse those two domains. Child is not in RUNTIME, so its explicit SHA witness is mandatory.

Smoke requires the live callback/owner markers, HW/ZZ controls and ART/JVM/bridge/runtime **one mapping base each**. Count load instances (`path@base`), **not distinct inodes**. Any repeat, missing/reject-only marker, branch6 or regression immediately finishes U9. The reviewed N11f 18-key prospective table is reused as hypotheses, renamed N11g in predictions.csv: four session-miss targets, Wikipedia, three canaries and other-cause observations. OrganicMaps is not in this shared 61b plan. Two manifest shards remain sequential; every nonzero shard stops the rest under the repaired runner, and minute20 cutoff leaves unrun keys unknown. The outer reads screenshots and supplies actual verdicts.

before_unlock always finishes U9: stop collector; rollback owned transaction through executor (including bounded OrganicMaps cold_stop recovery if necessary); verify318; HW/ZZ recovery smoke; final318. Capture-stop error is raised only after this recovery sequence, retaining the lock. No installer/foundation restart, board reboot, native promotion or other board use. Restoration failure retains the lock. No window has started.
