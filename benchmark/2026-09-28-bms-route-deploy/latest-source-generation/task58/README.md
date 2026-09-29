# Task 58: restore a coherent R155 startup protocol

The prior candidate mixed V2 startup machinery with R155 providers. Its reordered links alone did not fix startup. This trial restores the four groups in task 56's `RESTORE-PLAN.input.md` together, using the correctly identified **80c9aee0** runtime-provider baseline. The old payload is a V1 source starting point, not a claim of exact R155 source provenance; missing behavior was reconciled against the supplied disassembly.

## Offline evidence

- **26/28 R155 provider files retain their original bytes**, including ART `59e1bb45`. Only sigchain and runtime-provider change. The previously built abort bridge remains in staging but is no longer a runtime-provider dependency.
- Host, child, and runtime-provider each reproduce across two build passes. The full explicit host closure contains **319 libraries and 2,830 NEEDED edges**; six closure controls (five negative) cover missing members, unpinned lookup, wrong SHA, and SONAME mismatch.
- All three ordered NEEDED lists, SONAME/flags, TLS content/size and init/fini symbol order match R155. Final full-function inventory has **88 differing core records** (host 48, child 14, provider 26), with individual owners and dispositions in `static-dispositions.json`. This is a static protocol control, not proof of runtime equivalence.
- V1 host tests: direct sequence **8/8**, loader **18/18** (including three inherited-member controls, each with positive/missing/identity/wrong-name variants), hook table **2,220 checks**, and ABI layout pass. ELF topology mutation checks and four missing-sigchain-export negative manifests also pass.

## Restored groups

G1 retains the 128-byte mandatory host runtime service table, supplies its final three real callbacks, installs sealed-open before READY, and restores the two-output namespace getter. Namespace forwarding wrappers preserve the R155 null guard.

G2 restores the V1 manifest/loader/direct validated entry as one unit. Request/receipt, UID/GID, generation/SHA/Build-ID and audit checks remain. R155 disassembly additionally establishes `dlns_create2` flags **2** at `RealOpenLocalNow+0xac`, and three preloaded members that must already be mapped and are verified but not loaded again (registry, bionic compat, lzma; `WLSCPL_LoadSealedProvider` 0x3b1c–0x3cf0). Unexpected provider return terminates the child, with R155 exit 122/123 behavior restored. The retained verified-file implementation supports 16/20-byte Build-IDs; no hash check is disabled.

G3 restores non-zygote `startVm(false)`, the full environment and **16 MiB** stack, verified bridge → JNI registration → Java cache ordering, and the original libopenjdkjvm dependency. Extra javacore bootstrap, abort VM option and abort/base direct dependencies are removed. Typeface no-op and deferred Java initialization remain.

G4 removes host stdio interposition and preserves R155 libhilog position. The separate original bionic-compat provider is unchanged.

## Static limitations and BTI decision

New host/child/provider ELFs have **no GNU_PROPERTY_AARCH64_FEATURE_1_AND BTI property**, established by fresh `llvm-readelf -n` and section inventory in `bti-notes.json`. Thus the builtins function `__emutls_unregister_key` being `ret` instead of R155's `bti c; ret` does not request an enforced BTI landing-pad check for these ELF mappings. The outer loop explicitly accepted this disposition. No binary patch, permission relaxation, or BTI property edit is applied. An OH compiler-rt source reference was downloaded during investigation but is not a build input.

Remaining differences include generated identity values, data addresses, diagnostic line/log differences, verified-file implementation improvements, and the previously reviewed receive-bound arithmetic. `static/evidence/` contains dynamic sections, symbols, strings, all function diffs and full decoded-instruction coverage; `static-dispositions.json` records each differing function's owner.

## Reproduction and source retention

`source-restoration.patch` is the delta from the exact pre-task-58 build sources, with before/after SHA in `source-final.json`. `source/` retains the final changed files; `recipes/` retains the actual build wrapper, inner recipe and development steps. The source patch/final snapshot are authoritative; intermediate editing scripts document development and are not idempotent installers. `SOURCE_CLOSURE.json` and `ROUTE_A_INPUTS.json` preserve the emitted identity inputs without rewriting bytes.

Build with the locked dockbuild toolchain and retained provider input pool. Run `recipes/finalize_candidate.py`, the closure negatives, V1 tests, static inventory and dispositions before deployment. Deployment uses VM hdc, a held 5ea lock and the pinned boot ID. Every failure rolls back all generation mounts and reads back B5 plus both installer hashes.

## Target trial: blocked, whole rollback completed

Candidate **402f5c54**, host **9f67b34f**, child **62f7fdc6**, runtime-provider **9a121cd7** passed the live loader identity gate in PID **26935**. At 12:27:38.012 VM creation completed; at 12:27:38.038 HelloWorld crashed in the **system** `libopenjdkjvm.so!JVM_NativeLoad+100` (ELF PC **0x6bf0**), reading address **0x278** with `x8=0`. Disassembly and the GOT relocation establish a null `art::Runtime::instance_`. The fault maps show both route-a and system copies of ART, and two distinct openjdkjvm copies. Namespace binding to a second uninitialized Runtime is a hypothesis, not a completed causal proof. See [fault excerpt](trial/helloworld/fault-excerpt.txt), [instruction](trial/helloworld/system-JVM_NativeLoad.txt), and [relocation](trial/helloworld/JVM-runtime-relocation.txt).

The [candidate screenshot](trial/helloworld/final.jpeg) is a white launch window, not HelloWorld UI. Wikipedia and candidate ZigZag were not run after this first control failed. Java implicit-null delivery remains **unverified**.

The requested signal order is directly observed: musl calls **slot 0** at `0x7f02cd7210`; subtracting the route ART load bias gives **0x417210**, the real `art_sigsegv_handler`. It then calls DFX in **slot 3**. ART declining this native fault is not evidence of failed Java NPE handling. No candidate SIGBUS registration/dispatch was captured; that conditional criterion remains **unverified**. See [signal evidence](trial/helloworld/signal-chain.txt) and `signal-chain-results.json`.

All seven mounts were rolled back and B5 hashes read back; both installer copies remain **675536e8**. [ZigZag](rollback/zigzag/final.jpeg) shows TAP TO PLAY; [HelloWorld](rollback/helloworld/final.jpeg) shows its buttons and CREATED/RESUMED. Neither successful baseline launch produced a new fault. HelloWorld's initial rollback launch retained the dead candidate PID in AMS and `aa force-stop` printed error 10106401 despite exit 0; a later normal desktop retry spawned B5 PID **6787**. No foundation/device restart was needed. The 5ea lock is released. Outer-loop screenshot acceptance remains pending.

The first staging attempt stopped at a read-only mountpoint before candidate activation. Attempt 2 briefly remounted root rw only to create the directory, restored ro immediately, then deployed. Both attempts have receipts. Full raw logs remain in the VM paths recorded in provenance files; small excerpts and screenshots are retained here.

## Validation and handoff

Known-answer suite: **69 tests, 2 skipped, 0 failures**. Agent-spec lifecycle: **4 pass / 4 fail** (caller, artifact rejection, symbol coverage and identity pass; Wikipedia, candidate regression, advancement past getTheme and Java NPE fail). The contract is unchanged. `lifecycle.json` and `lifecycle-explain.md` retain the actual tool verdicts. Task 58 is **blocked**, with zero lighting increase.

Raw source snapshots, unified patches and tool output retain original whitespace to preserve recorded hashes and patch context; unrestricted `git diff --check` therefore reports archival whitespace. The check on authored README/JSON/recipe changes passes.
