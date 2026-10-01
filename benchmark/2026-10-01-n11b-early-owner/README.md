# N11b early owner sharing, child-only U8 candidate

The failed N11 callback was later than the deployed admission path. Actual provider 0509fe23 loads bridge/runtime with plain dlopen before B8 runtime-ClassLoader creation, and its nativeHiLog/JNI handle resolves to a different bridge mapping from the compat shim. The audit is in `../2026-10-01-n11-single-owner/offline-load-path/README.md`; it binds deployed ELF, source SHA, bootstrap DEX, disassembly, timestamps and same-PID address arithmetic. Exact mapping-creation caller namespace was not captured; this candidate tests direct default sharing at an already-observed earlier hook, not an invented creation stack.

## Candidate and boundary

**Child 163da8055b69e049df6999b6f37ab4d77b2ea5f61cbb3f59fa4309cbe76bf4d2**, independently repeated. The pinned recipe exactly reconstructs the N10b dc73a28d baseline. The only semantic addition is direct default -> westlake.sealed.child inheritance of **two sonames**, followed by NOLOAD handle equality with the already-preloaded bridge/runtime. Missing inheritance, missing resident or divergent handles fail initialization; never fresh-load to satisfy the check. `[N11b-EARLY-OWNER] default reuses sealed bridge/runtime; handles verified` is emitted at the existing N10b preload hook before provider initialization. The actual deployed child and N10b marker prove reachability before JNI registration.

Package **$WORKSPACES/westlake-generation-n11b-child-u8-163da805/**, manifest **2efb6947df202d877760ed8f58a065c4f539918c3347cef0db1c279de5527c51**, changes **one of 312 identities**, `/system/lib64/appspawn/libwestlake_android_child.z.so`. Runtime, provider, ART, bridge, host, Java, images, installer remain U8 bytes. Fingerprints **e953c0921536 / 4db882a81732** stay unchanged because these fingerprint lists exclude the child; explicit 312-identity/child-SHA verification is essential. No failed N11 host/runtime and no Emboss runtime are included in this standalone child-only experiment.

## Offline results

- Strict compile/link passed for baseline/candidate/repeat; needed/SONAME and exported dynamic symbols unchanged. Only added import is musl `dlns_inherit`, from existing libc provider. `elf-compatibility.json` records complete surfaces.
- Tests compile and execute the **actual production sharing block**, covering success, inheritance rejection, missing bridge, different handle and missing runtime. Every lookup enforces NOW|NOLOAD; lifecycle **3/3 pass**. These tests do not prove actual board namespace visibility.
- Frozen **8 entries / 2 provider identities / 0 violations**. Source snapshot, patch, exact commands, tools and input objects are recorded; binaries remain in persistent `$WORKSPACES/westlake-n11b-early-owner-build/`.
- Production native gate currently **REJECT: N1 30 + N2 103**, no invalid-input errors. Finding-content comparison strips only issue_id/disposition/exception: **28+103 exactly match approved U8 findings**, **two N1 findings are candidate-only** (old accepted N10b inherited ART NOLOAD guard under a new source profile, and finite owner_paths NOLOAD equality check after inheritance). Issue IDs themselves change with manifest/sidecar binding. `exception-proposal.json` is **proposed, not approved**; no exception registry was edited.
- **rollout_ready=false**. `offline-precheck.json` has mandatory expect.confirm/refute; no board window is scheduled or started. U9 preparation is separate and does not wait for N11b.

After outer approval, require early marker plus ART/JVM/bridge/runtime each one load-address instance; compare provider Java and compat WM pointers in the same bridge mapping. Activation smoke owns the control verdict; no manual stop solely for baseline foreground_unconfirmed. Only after smoke PASS run wikipedia/fd-noice five rounds each, facts verbatim and t20 outer reading. Always verified rollback U8 before unlock in that window.

The full production dry-run also refuses activation at the native exception gate (exit 2), with no device I/O. The first failure is preserved in `production-dry-run.json` / `.log`; no policy override or rollout flag change was used.
