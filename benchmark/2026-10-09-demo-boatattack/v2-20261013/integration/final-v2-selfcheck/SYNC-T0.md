# Canonical interface handoff for T0 / root PROGRESS91 relay

One producer: `final-v2-selfcheck/compile_selfcheck.py`; T0 remains sole owner of the61b identity/full128 driver. No second full128 implementation here.

`planned_selfcheck.json` keeps T0's exact required interface:
- `status: EXPECTED_UNION_NOT_OBSERVED`, `signed: false`
- `inputs: {v1_seal: <original7f5 full SHA>, plan: <actual postinstall plan full SHA>}`
- `all_expected_sha256`: exact original940 effective objects plus actual plan11 placement+7 bind targets and originalBoatAPK. No stale r4 control SHAs; no private-target omission.
- Additional fields outside `inputs` bind source actual R5, original admitted realization/activation, actual BMS UID and parameters. Numbers are mechanically checked, not a substitute for membership.

For61b, the source is original actual R5/running realization. For5cd, source is actual postinstall R5 SHAa5166ded and original activation-binding.5cd; exact487 paths come from the admitted5cd plan. No61b-to5cd string-only UID/WID substitution.

A subsequent boot can legitimately change run.sh's single WL_PARENT_ID. The readonly composition will use the unchanged original realization.running_files + observations validator and r5 binary collector/compare to derive its entire new SHA from independent same-boot host/WMS. If a future driver needs that new SHA, consume the resulting exact dynamic receipt/current observation and recompile the single planned union; do not exempt run.sh or infer WID from it. T0's present `expected=originalseal|boat` is valid only when its original run.sh SHA already equals the independently proven current value; otherwise require this explicit parameter-derived rebind.

Original running compile is61b-only; original r3 appendix rejects changes to existing baseline targets. We retain both gates and add a narrow composition of an independently admitted original base plus the exact Boat plan. Frozen R5 collector/compare/nonfile predicates remain unchanged. This composition is candidate/not_sealed and cannot sign or restore. The finalized seal must still be built from an actual live capture using original build_seal; planned rows never masquerade as observed capture.

No main blackboard write permission exists in this sandbox. Root should relay this exact file; it is not a claim of direct lane delivery.

## Actual5cd handoff now available

Use `actual-5cd-main-plan/composed/planned_selfcheck.json`, SHA `84092e8c60bf0bdad3f5d671c5234b3d2ad6b96ab880720ed3e2bb7607ba86a4`, with actual plan `e9d534dc6ffd08014f702adfdf2990503e57b1ce09b8945e635e79afa4d46f71`. Actual UID20011301; original940 plus the exact candidate increment gives954. `verification.json` records independent regeneration. All planned content is candidate/not_sealed, not placement or UI evidence. The original940-only observation is a negative control against this954 composition. After landing regenerate main-bound composition so its compiler self-pin resolves to main; do not edit archived t4 composition references in place.
