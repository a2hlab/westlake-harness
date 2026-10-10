# reboot_sim eight-input exporter + commands.md step-4 fix (cc-t3 #91)

cx-t0 flagged: `reboot_sim.py --inputs` takes a SHA-pinned eight-input manifest JSON (schema_version 1,
inputs = plan/snapshot/inventory/autostart/closure/recipe/queries/policy + raw_inputs per snapshot item),
NOT a snapshot directory. Two fixes:

1. `scripts/lab/reboot_sim_inputs.py` (NEW, read-only): assembles that manifest from a snapshot dir + plan
   (+ the six aux inputs by path). snapshot + plan + raw_inputs (every item's raw/.stderr pinned to the SHAs
   the snapshot already recorded) are derived; aux not supplied are emitted `sha256:null, status:MISSING` and
   listed on stderr. Only hashes/references; never fabricates content; never touches a board. Modeled on the
   `benchmark/2026-10-10-reboot-sim/real-known-answers/` style ($WORKSPACES/$HOME-relative paths, SHA-pinned).
2. `benchmark/2026-10-10-boat-layer-stage/commands.md` step 4: now builds the manifest with the exporter then
   runs the sim; documented as a REFERENCE/advisory step — if the exporter reports MISSING aux inputs, SKIP +
   RECORD (not a safety failure); the real gate is the post-reboot read-only checks (step 6).

Known answer: against the real 5ea v2 snapshot (`.../2026-10-10-5ea-u13-restore/v2/post-reboot-pre-app/snapshot.json`)
the exporter pins `inputs.snapshot.sha256` to the real snapshot SHA and emits `raw_inputs` = 512 (256 items x
raw+.stderr) each matching the snapshot's recorded pins; unsupplied aux are MISSING. Tests: test_reboot_sim_inputs 7/7.
