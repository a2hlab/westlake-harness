# U14 Stage A closing decision — unsigned draft

## Evidence first

**This packet cannot authorize promotion.** The five signed window summaries
cover **124/126 reference-lit keys**, not126. `fd-seal` is awaiting a fresh61b
candidate observation; `fd-organicmaps` is **“板相关白窗、未定”**, not a confirmed
regression and not measured-lit. Both decisions leave `promotion_authorized`,
`signed_by` and `signed_at` null; execution remains false. No device, VM, SSH,
lock or registry operation was performed.

The legacy direct-runner glob counted308 records and **missed40 window6
candidate records**. Window6 adds a candidate/control directory level. The new
explicit selection includes physical candidate runner records only:

| Window | Candidate records |
| --- | ---: |
| 1 | 101 |
| 2 | 61 |
| 3 | 52 |
| 4 | 51 |
| 5 | 43 |
| 6 | 40 |
| Total | **348** |

Schema-2 `process_selftest` gives **279 PASS /69 unknown /0 REJECT**, with380
`validateAead=OK` events. `selftest_error`, `badtag`, `probe_error` and the
independent **any-PID failure rescan are all0**. Absence of a failure marker is
not successful probe coverage. The69 unknown runs require **71 exact
(record,PID) explanation rows**, all pending outer approval.
The rescan covers328 existing hilog files;20 have no hilog (19 icon-locator
steps and the interrupted pre-launch AntennaPod attempt), explicitly explained
instead of being silently counted as clean logs.

Explanation classes: pre-bind23, bound-then-left25, icon-locator19,
pre-launch-board-loss1, bind-failed1, spawned-after-dump2. The last class follows
the existing aggregator’s classification of a listed PID with no log lines;
it remains an observation-gap explanation, not proof that cryptography passed.
The AntennaPod sixth attempt has no click/hilog/screenshots and explicitly
reports HDC loss. That is unknown, not a failed app verdict or a selftest PASS.

## Record domain and exclusions

`record-selection.json` lists every included and excluded path; their565
record files partition as348 candidates +217 excluded:

| Excluded class | Count | Reason |
| --- | ---: | --- |
| Recovery smoke | 72 | Runs after restoration, not on the candidate |
| Executor state | 125 | Identity/apply/baseline/post-apply/rollback/final records, not app observations |
| U13 control runner | 14 | Window6 baseline comparisons, not U14 candidate processes |
| Evidence copy | 6 | Window6 landing copies of runs already counted |
| Known-answer fixture | 0 | Explicitly excluded when present |
| Symlink | 0 | Never double-count a link or link-containing relative path |

An unclassified record path is a hard collection error. Failed attempts with
zero runner records are not inventively added as runs. Candidate activation
smoke records stay included because they belong to candidate `runner/`; their
launcher icon-locator records are individually explained when there is no PID.

`source-receipts.json` pins record, hilog and all processes-t*.txt hashes.
`selftest-u14-stage-a.json` preserves per-process event lines and their hashes.
PID maps are numerically sorted for stable bytes. Each explanation pins its
primary evidence file, selected source lines and, where relevant, the exact
process-list PID line. The hook’s issue identity remains `(record,pid,unknown,
null)`; evidence line hashes are separate from that issue identity.

## Signed visual coverage

`inputs/window1..5-outer-signoff.json` snapshots the existing outer decisions,
with original-source SHA receipts in `visual-summary.json`. The reference is
the exact U14 StageB126-lit snapshot; neither process liveness nor probe PASS
adds a screenshot-lit key.

- Reference126; signed measured-lit union124; pending `fd-seal` and
  `fd-organicmaps`; confirmed regressions0 **does not imply coverage complete**.
- Candidate observations exist for125 reference keys: Seal is unmeasured,
  OrganicMaps is observed but unresolved. Therefore the decision's `measured`
  is125 and `same_or_lit_within_k_of_n` is124; the two notions are not conflated.
  Reference positives124 + gains3 =127 signed candidate-lit keys in this packet,
  distinct from the historical129-key leadership-inventory scope.
- Gains: VLC own welcome page; 3D Model Viewer own Menu dialog; Termux terminal
  UI with a bootstrap-install error dialog. Gains are3 new keys, not proof of
  complete app functionality. They do not offset the two missing reference keys.
- Lottery: fd-noice6/6, fd-uhabits6/6, wikipedia6/6, noice6/6, fd-notes5/5,
  AntennaPod5/5 measured. AntennaPod attempt6 is separately unmeasured due61b loss;
  do not silently use5/6 or claim6/6.
- Window6 OrganicMaps: candidate0/4 lit at t20, same-board U13 control1/2
  (only splash;5ea turns white at t40,5cd control already white). Window5 had a
  prior candidate0/1: all observed candidate attempts total0/5, but these
  cross-board observations do not replace a61b reference-board comparison.

The window6 blackboard verdict is captured by exact source line number, text
and line SHA in `inputs/window6-outer-verdict.json`. It is copied documentary
evidence, **not a new image review by this lane**.

## Bundle bindings and outer fill-in

| Variant | Approved unarmed candidate | Actual armed candidate | U13 restore |
| --- | --- | --- | --- |
| Common5ea/5cd | 12d30eb0 | 56974aa0 | 2abe4a49 |
| 61b | b0f74132 | afb44370 | 0a31ad35 |

Full hashes and source-composition receipts are in each `decision-draft-*.json`.
Both bind native manifest3460435a and inputs11001e6e. The61b baseline is its
own variant, never the common runtime fingerprint. `inputs/composition-*.json`
snapshots the existing binding, not new authorization.

Outer steps before signing:

1. Restore61b through its owner’s existing procedure; collect a **fresh U14
   candidate** Seal record/screenshot, hashes and outer signature. The draft has
   explicit null fields for that row. Its U13 reference screenshot is labeled
   reference and cannot fill candidate evidence.
2. Resolve OrganicMaps on its reference board with same-board U13 control and
   U14 candidate k/n. Current white-window evidence is unresolved, not waived.
3. Rebuild the exact record domain/report/summary/explanations and complete
  126-reference visual verdict. Review each unknown issue; bind and sign the
   common and61b explanations and decisions separately. No failure-class line
   can receive a missing-coverage explanation.
4. **Selection integration remains an explicit blocker**: the existing StageB
   `stage_a_selection.pattern` and the single-pattern CLI cannot express the
   new candidate-only union as used here. Bind an outer-reviewed extended
   selector, including the pre-launch interruption case, before StageB admission.
   This draft uses `stage_a_selftest` library primitives and pins their SHA;
   it deliberately leaves the original CLI `tool.exit_code=null` instead of
   pretending an unchanged direct-runner CLI covered all348 records. Its local
   `aggregation_tool.exit_code=0` is only the offline builder’s actual result.
5. Fresh StageB native tickets/identity, controls and window screenshot signature
   remain mandatory. `packet_reason()` validates the process/visual core with
   the real U14 `retention_criteria`, not the full device admission hook.

## Known answers and reproduction

```sh
python3 benchmark/2026-10-08-u14-stage-a-decision-draft/build_decision.py
python3 benchmark/2026-10-08-u14-stage-a-decision-draft/test_decision.py
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test --manifest-path tools/spec-checks/Cargo.toml --test u14_stage_a_decision_draft
```

Known answers cover wrong bundle (also actual common→61b cross-binding), one
missing explanation even after rehashing, changed report bytes, a bound badtag,
any-PID badtag outside the process list,123/126,124/126 and125/126 coverage rejection,
evidence byte drift, missing authorization, nested candidate/control selection,
symlink exclusion, unknown-path rejection and the exact shipped issue set.
The sole positive retention fixture is **synthetic test-only**126/126 with
mock outer fields; it is never written into either real decision draft.

Collection exit0 means the offline inputs were built; it is **not permission
to promote**. Build/test/Rust/lifecycle/preflight outputs and hashes are recorded
in `validation.json` and `evidence/validation/`. Large original logs remain in
their source run trees; this delivery never prunes or copies them over originals.
Two fresh builds produce eight byte-identical core evidence files, including
the reference snapshot, preserved byte-for-byte to retain its approved SHA.
