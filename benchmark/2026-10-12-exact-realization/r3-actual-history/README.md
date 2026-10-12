# Actual r2 placement history binding

The completed main-tree r2 transaction replaces the earlier unavailable positive history. The frozen r3 builder ran locally once against the real success inputs and returned rc=0 in 6.635 seconds. Its full offline admission checked the parent executor rc=0, the prepared activation, admission/authorization, transaction backups and all 487 original placed receipts before writing the binding. Every referenced input SHA was then checked again locally.

`activation-binding.candidate.json` SHA-256: `b6a0e01ca3c20dde019219f7251998f314fc12a66a0e3ec81c0d9a957591ca68`.

This is **OFFLINE_HISTORY_BINDING** only. `realization` equals `origin_realization`, both pointing to the original candidate proof; `appendix` is null and `synthetic` is false. It does not certify current device bytes, current boot, UI acceptance or final seal signing. No device call, execution authorization or restore action was issued. A Python audit guard denied subprocess creation, shell execution, exec/spawn and socket connection inside the build.

The binding retains portable `$WORKSPACES/westlake-harness/...` references to the actual main evidence. `build-result.json` preserves the recorded invocation and `build-binding.log` its output. Large backups and runtime inputs stay at their existing locations; this is not a standalone runtime archive. Frozen r3 and all older freezes remain unchanged.

For final seal validation, create a **new** binding using the final sealed realization plus its separately pinned appendix and these same original placement inputs. Do not rewrite this candidate binding. Current-boot read-only selfcheck and independent outer signing remain separate steps.

The current final demonstration draft is independently frozen at `benchmark/2026-10-12-v1-seal-assembly/final-demo-draft/`: its activation-history pending item is now satisfied by this evidence; fresh live selfchecks and final signing remain pending. Game review is explicitly an as-of 5/10 snapshot, not a claim that the remaining games passed. Historical 112-app results are not this round's measurements.
