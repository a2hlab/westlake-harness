# Plan2 final sidecar and spare consent boundary

This supersedes the prior checklist's scope and spare-UI assumptions as documentation only. The original checklist, contracts, driver, seal, candidate proofs and exact appendix remain unchanged. No approval or signature is supplied here.

## Contract conclusion

The current contracts do not require the user to accept privacy on5cd before61b may be signed. This conclusion is conditional on completing the actual61b acceptance and the specified spare fingerprint rehearsal; it does not authorize skipping either.

1. `specs/demo-baseline/t5-seal.spec.md:40-44` defines the spare rehearsal: “The spare board self check matches the original fingerprint through the user-approved exact parameter realization with template and generator hashes parameters complete rendered file hashes and retained raw execution logs”. It does not add spare-board feed interaction or privacy acceptance to that criterion. Lines34-38 require every component match with unapproved differences rejected. Both actual r5 selfchecks are pinned: mode live-readonly, PASS,940 comparisons each (811 declared byte objects plus129 APK identities); original nonfile gates are retained. The outer signer, not this sidecar, accepts the evidence.
2. `specs/demo-recovery-followup/t6-sealpack.spec.md:12` explicitly says “范围是 v1 无 Boat、61b20-key 加5cd既有128交叉对照；不得扩回61b全量128” (spacing normalized here). `t4-integration.spec.md:16` repeats the same Plan2 scope. The landed booklet's `inputs/scope-approval.json` pins the board25810 approval and both contracts. No new current61b128 run or new scope decision is required. Historical112 remains historical; do not mark the old all_128_observed field true to represent current20.
3. `specs/demo-recovery-followup/project.spec.md:9` states “不得自动点击隐私同意”; `t1-watchdog.spec.md:18-22` requires privacy sequences with no automatic touch and no fabricated UI READY. The locally viewed5cd screenshot shows a real feed behind the personal-information protection prompt. That is an observed rendered feed plus an unresolved user choice, not accepted unobstructed feed/article interaction. WAITING_FOR_USER_CONSENT must remain visible in the signoff sidecar and manual.
4. `t6-sealpack.spec.md:30-34` still rejects missing interaction signoff. The scope distinguishes the61b demo's existing real feed/article/back/refresh evidence from5cd's spare fingerprint criterion; this is not permission to omit61b interaction acceptance or fabricate5cd PASS.

Accordingly,5cd consent is pending for5cd post-consent UI interaction. It is not a new blocker for signing61b solely under the spare fingerprint-rehearsal clause once its actual PASS and all61b requirements are accepted. If the outer operator separately chooses to require a5cd interaction acceptance, that additional acceptance remains pending until the user's real choice and later images; it must not be called satisfied by this document.

## Correct sidecar fields

`final-sidecar.pending.json` splits:

- `scope`: explicit Plan2, current61b20, existing5cd128 reference pins,10 game exclusions and historical112 provenance.
- `primary_demo_61b`:61b live selfcheck, same-boot interaction/current frame and final booklet; outer UI approval remains null.
- `spare_fingerprint_rehearsal_5cd`: actual activation selfcheck PASS, current boot8d0f7543-2352-4d9b-a7ce-e3b5d0ba12a5, original487 activation history and r4b directory completion; outer acceptance remains null.
- `spare_ui_user_action`: WAITING_FOR_USER_CONSENT, image/record SHA, user_choice null, automatic_consent false, UI-pass claims false. This state is permitted to remain explicitly pending in a signed61b sidecar; it is not coerced to PASS.

`final-sidecar.schema.json` is an independent attachment format, not a replacement gate or an implementation change. The signer fills actual approved_by/approved_at and the three outer acceptance fields only after review. All supplied approval fields remain null. Any later privacy choice or5cd UI result needs separately pinned evidence and a new record.

## Role and legacy entry correction

The actual pinned Plan2 driver is `RUN/tools/demo_seal_61b.py`, SHA `a7add5519e9f3cf932c620a7e8e71246cb350caa3c7681f42f41c04017e9b446`. Its reviewed() at line362 still requires exact approved_by `outer(claude)`; line649 concerns execution-window authorization separately. The Plan2 membership code accepts the actual manifest subset and records t5_regression_scope (lines595-599,634-638,683), while retaining the historical all_128_observed key at614. This sidecar records honest scope-specific fields rather than relabeling20 as128 or rerunning that old driver. Neither the original seal nor any legacy boolean is modified.

The old checklist's extra5cd UI prerequisite and unresolved-Plan2 suggestion are withdrawn by `scope-correction.json`. Existing scope approval is authoritative; this correction creates no new exception and lowers no current contract criterion. Final seal signature remains the outer operator's action. Zero board commands were issued.
