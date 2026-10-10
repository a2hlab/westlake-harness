# v1 seal compiler alignment

## Evidence first

The old compiler forced BoatAttack into an obsolete route-II-d shape: one
adapter, one JAR and three private libraries. That conflicts with the signed
two-stage sealing decision. **v1 is 128 apps + Toutiao + autonomous startup,
without BoatAttack. v2 is a separately admitted BoatAttack overlay.** No runtime
or frozen file should be replaced merely to satisfy a template.

`build_seal.py` now requires explicit `seal_stage` (`v1` or `v2`) in the overlay
input and stores it in the seal. Wire-format schemas stay `demo-overlays/v1`
and `demo-seal/v1` for selfcheck/restore compatibility. In v1 the Boat slot must
be absent with a reason and no files; in v2 it must be active with exact member
targets/SHA, role names, APK/version, source, rollback and a pinned admission.
The five-file count and forced adapter target checks are removed entirely.
The source/rollback/admission descriptors are pins, not signature verification;
outer must bind the accepted shape, t2b/reboot regression and frozen registration.

The shipped `overlay-inputs.json` is a **v1 draft**, not a seal: Route B remains
pending, Boat is absent. Old tested-route-II-d members are not current inventory.
No artifact, policy, frozen registry, restore provider, live seal or board state
is changed. Final snapshot, interaction signoff, live selfcheck and restore
rehearsal remain outer/collector work.

Fresh known answers cover v1 exclusion, v2 admission, stage omission, variable
member counts, observed bytes/APK/version consistency and the real selfcheck
CLI rejecting drift. The existing `demo_baseline_seal` selector also runs
restore/runbook and selfcheck tests. Raw output is in `evidence/seal-selector.txt`.
Route B must be active in either stage; an absent reason cannot bypass the
mandatory Toutiao component. The draft's pending Route B therefore still refuses
seal creation, rather than producing a misleading v1 with neither special app.

Use the existing compiler command with `--overlays` pointing at a completed,
reviewed v1 input; do not change `seal_stage` to force an unfinished Boat into v1.
