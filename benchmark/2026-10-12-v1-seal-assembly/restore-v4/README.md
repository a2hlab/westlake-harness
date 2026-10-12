# Restore v4: disabled 5cd package with r2b readiness controls

The frozen v3 compiler accepts only the original 23 controls, so a binding change
alone cannot add the readiness worker. v4 adds a pinned 24-control inventory and
an independently pinned r2b helper update. The final local package contains
**24 control targets + 460 runtime targets + 3 stage targets = 487 targets**, with
13 boot members, 22 declared new directories and 6 existing-directory guards.
All 25 offline tests passed. No device, remote, install, reboot or signing operation
occurred. This is a source/package review freeze, **not a signed execution seal**.

## Sources and final package

- Original restore transaction recipe: `../restore-v3`, freeze `ac3a78041ff0d36acb4d893b3602185aed1924a6285e6ce6d6dabe1de5f0a2f0`.
- Measured control24 source: main-tree `benchmark/2026-10-12-v1-seal-execution/readiness-package`, with independently pinned composition, base-plan and worker-preimage records. Guardian baseline commit: `ee50b0cd6c`.
- Final helper: t0 commit `379d1a46de0c388e105157d455916d356c11028b`, `benchmark/2026-10-12-child-readiness/r2b-quiet-reset/checkpoint-manifest.json`, manifest SHA `d07958254c7a1fe72c69062a08d25a1e4c31de36070aeb00f9160718c910417c`.
- Helper SHA `68abf028c80d5c036334fcbd974c609b0d967083ea72ead14b27928346856107`. Watchdog, worker and launch remain byte-identical to ee50. Only the helper's quiet discovery and load-time quiet reset enter the delta.
- Final binding: `binding.5cd.r2b.disabled.json`; deployment: `deployment.5cd.r2b.disabled.json`.
- Final package: `package-r2b-disabled`, manifest SHA `3555eaecc82b05ce25847fee82ae94e07af5a8c885bd39c20a4cf12d7c85e0c4`, plan SHA `593c002c633a5fb4ad09d4298f6010a9b7203a98dabdd7c0fceb4dabc4493208`.

`binding.5cd.disabled.json`, `source-control-audit.json` and `package-disabled`
are the intermediate ee50 preparation history. They are not the final r2b package.
`build_binding.py` verifies that history; `bind_r2b.py` verifies the checkpoint
against its Git snapshot and every listed file before adding `guardian_update`.
The provider verifies all checkpoint bytes again and permits only the helper delta;
watchdog, worker and launch must still match the measured control24 source.

## Target binding and hash chain

The source plan supplies content and explicit creation policy. Its 61b execution
flag, authorization and worker absence are not imported. The worker's 5cd before
image follows from the actually measured absent candidate ancestor, with pinned
`restore-5cd-preimages/028-directories` transport/stdout and same-boot summary.
The original 25 measured preimages are retained; the extra descendant absence is
an inference from that target evidence, not a fabricated additional board probe.

The readiness worker enters the control inventory, plan and boot `members.tsv`.
The compiler refreshes the entry helper/watchdog pins, all 13 boot member hashes,
`STARTUP_MEMBERS_SHA`, `startup.env` and `startup.expected.sha256`. The worker is
transitively checked by boot-entry before the guardian starts it. UID20011300 is
projected through the known configuration, namespace and runtime/request fields;
`AUTH_UID -> TT_OWNER_UID -> RB_OWNER_UID` is retained. Wrong-UID target diagnostics
and the strict ownership predicates remain active.

The 221 original runtime files and 239 typed extras retain their per-file measured
mode/UID/GID/label mappings. The three known live script deltas remain explicit
UID/WID derivations; WID33 is not carried to 5cd. Stage metadata is identified as
historical donor evidence and new-directory metadata as creation policy, never as
observed existing 5cd state. Source details remain in the binding and v3 audits.

## Checks and admission

`evidence/test-v4-r2b.txt` is the original combined stdout/stderr of one final
`--self-test`: 7 primitive checks plus 18 final-package checks, 25 passed, rc0.
The actual 487-target binding drives recording-transport apply/rollback and failure
injection: absent CFG, initial mkdir, metadata/readback, partial transfer, nonempty
owned directory, unknown/replaced inode and retry. The final packaged helper is
also sourced by shell fixtures: quiet discovery makes zero od calls; inherited
quiet=1 resets to 0; wrong-UID target diagnostics remain nonempty. No HDC runs.

`evidence/frozen-and-gate-check.json` verifies every file in b5904, 81af19 and v3
freezes unchanged. v3 `invoke` and `new_executor` are AST-identical: the standard
argv, typed self pin, independent executor pin, exact seal gate and transaction
recipe are preserved. All final manifest file sizes and hashes were checked.

Deployment and startup stay disabled, startup approval is PENDING, and no donor
61b authorization is supplied. A standard invocation still requires matching exact
seal membership even for preview; no synthetic seal was created to bypass this.
Actual admission remains with the user and outer/BMS. Changing activation or
acceptance requires a separately reviewed derivative; this frozen package is not
an executable authorization.

For a new local compile, use the pinned provider with `--compile --binding binding.5cd.r2b.disabled.json --out <new-directory>` from this directory. Keep the
existing frozen output untouched. Large copied runtime payloads remain local and
are transitively pinned by the manifest; `landing-paths.txt` lists the small review
artifacts. Inputs are resolved through WORKSPACES and the recorded local CAS.
