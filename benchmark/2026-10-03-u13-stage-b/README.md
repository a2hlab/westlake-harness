# U13 production promotion

The earlier certificate interface binds the unsigned bundle SHA while deployment
uses its armed SHA. Confusing these identities would either reject a valid
promotion or silently weaken its provenance. This port keeps both identities:
`arming-correspondence.json` records both complete SHAs, exactly two JSON changes
(`rollout_ready` and `rollout_blocker`), identical native manifest and individually
hashed payload members. Stage A's actual board windows used the armed pair.

The source is `2026-10-02-u12-final-assembly/stageB/promotion_dispatch_u12.py`,
its production hook and review waiter. U13 calls the original strict
`2026-10-03-u13-stage-a-plan/promotion_hook_u13.retention_reason` with the signed
unarmed identity, 122-key reference, report `0488fa09` and board-specific exact
unknown explanations. Actual activation remains bound to the armed bytes.
No runtime artifact, installer, image, JAR or gate criterion is changed.

Each board has a 30-minute promotion window. The transaction verifies the
same-board U10.1T8 baseline, applies the existing approved U13 bytes, verifies all
321 candidate assertions and both fingerprints, then runs activation smoke and
captures fresh HelloWorld/ZigZag t20. The waiter publishes `approval-ready.json`.
A fresh outer signature must bind serial, window root, armed bundle, manifest,
smoke SHA and identity SHA. Only a passing original U13 admission, passing smoke,
that signature and final candidate verification allow retention. Any refusal
executes the existing stopped-parent rollback, 318 baseline assertions, recovery
smoke and final verification. Failed recovery retains the lock.

The signature wait is bounded by 20 minutes and lock-start +24 minutes, leaving
at least 6 minutes for restoration. Single ZigZag crash is preserved and restores
the baseline; any authorized retry requires a fresh output window. No screenshot
brightness is inferred from alive, READY or script PASS.

Offline evidence: `tests-{mac,vm}.txt` (8 known answers each),
`decision-tests-mac.txt` (6 signed-decision known answers),
`decision-reproduction.txt` (219 records, byte-identical report, all three
retention decisions None). Fresh production receipts are isolated under
`common/` and `61b/`; they include the current master policy binding, native gates,
static/frozen checks, RB/T4b, G1/G2 and real executor dry-run. Dispatch refuses
receipt policy drift and checks VM tools, shared binds and HDC before LOCK.

Per-board compositions preserve the installation-chain difference: 5ea/5cd use
U10.1T8 base `190afedd`; 61b uses `c0adc4a9` (its existing libinstalls). No service
restart or installer alignment is part of promotion.

All three windows retained U13 after fresh outer HW/ZZ signatures and final
321 assertions (`diff={}`, `absent=[]`). Unlock: 5cd 09:35:10, 5ea/61b 09:37:50.
Final runtime fingerprints: 5ea/5cd `821de739cf81` (124 files), 61b `452447a4a0ba`
(124 files); boot `ee927db88a67` (36 files). The expected runtime difference is the
preserved board-local installation chain. Outer declared U13 unified at 09:39:28.

Raw window evidence is retained under
`$WORKSPACES/westlake-inputs/generations/u13-stageB-20261003/board-evidence/`.
30,301 files /114,295,026 bytes have per-file SHA indexes in 63 chunks. Original
full executor dry-runs and home-path tool evidence are in the sibling `offline/`,
with SHA/index references in `offline-artifact-index.json`. Public JSON copies in
`window-evidence/` and `offline-evidence/` replace recording-time home/workspace
paths with variables; they do not substitute their SHA for the original proof.
All original directories are preserved. `fresh-facts.txt` is verbatim
`run_facts.py` output; `sheets/*-t20.jpeg` and the original screenshots accompany
the outer signatures. No lit count is inferred by this lane.

Pre-window vmgr RSS: 1,568,928 KiB after preventive reopen; orb 0.094 s, VM boot
and bind unchanged. Post-window: 1,423,936 KiB, orb 0.113 s. No board reboot,
installer alignment, runtime rebuild or gate-registry change was performed.
