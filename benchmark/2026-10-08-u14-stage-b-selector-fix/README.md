# U14 Stage B candidate-union wiring correction

## Evidence first

The previous Stage B entry used `window*/u14-A*/*/runner/**/record.json`: it selected **308** records and silently omitted **40** window6 nested candidate records. The decision draft had already found the complete domain, but its private selector was not the production CLI or Stage B admission. This correction makes both use **`u14-candidate-union-v1`**, with fail-closed domain validation.

Fresh real-tree CLI: **348 records,279 PASS,69 unknown,0 REJECT,71 explanation rows,0 any-PID failure records**. Window counts are101/61/52/51/43/40. The report SHA is `435ab002ef756f4beae36453ecfabcab8225d8fdc20e7793719ec17d93a3dca7`; selection SHA is `707f974975686bc1280ab1a5b7ec43df9c2531595e97ca826c3c0429b9dca237`. This operational report uses the CLI's original absolute-path serialization, so it is not the portable decision draft's `07bfed3e` report. No old hash or historical PASS is borrowed.

| Excluded class | Records |
|---|---:|
| recovery-smoke |72|
| executor-state |125|
| U13-control |14|
| evidence-copy |6|
| known-answer |0|
| symlink |0|
| **Total** |**217**|

`selection.json` lists every included and excluded relative path; `summary.json` and `results.json` are portable evidence views. Raw operational outputs remain in this directory's persistent `.artifacts/cli/`; their exact paths and SHA are in `results.json`. Of20 missing hilogs,19 are icon-locator probes and1 is the61b AntennaPod sixth attempt interrupted before click. That attempt is explicitly **unknown**, not successful crypto or a launched app.

## Fail-closed known answers

```text
union_cli_exit=0
legacy_cli_exit=1
control_cli_exit=1
incomplete or contaminated U14 selection: selected=308 expected=348 missing=40 extra=0
incomplete or contaminated U14 selection: selected=54 expected=348 missing=308 extra=14
entry_rebind_exit=0; common/61b unsigned; gates and promotion authority unchanged
```

The mixed nested glob selects40 candidates plus14 U13 controls; it is rejected for both its missing308 candidates and extra14 controls. Synthetic tests separately isolate control injection, unknown paths, symlinks, interrupted observations, forged legacy summaries, report/control substitution despite rebound hashes, domain growth, and portable entry paths. The existing23 Stage B tests still cover P1 deadlines, P2 exact native tickets and rollback behavior. The U13 CLI's219-run report still reproduces `0488fa09` with41 explanations.

## Entry binding and boundaries

- Both `common/composition.json` and `61b/composition.json` now bind the named union; `prepare.py` regenerates it rather than restoring the faulty glob.
- Both future decision templates and the Stage B selftest source snapshot/provenance bind the exact new tool. `entry-common.json`/`entry-61b.json` are **unsigned** previews referencing fresh report/explanation/summary bytes, not permission to promote.
- Admission independently enumerates current physical candidate records, rejects unknown paths, compares ordered report and declared paths, and checks the selection receipt/exclusion counts. Counts alone cannot admit308 records or control injection.
- Relative `$WORKSPACES/` entry paths are normalized only for identity comparison; report/explanation/summary byte hashes and the full tool SHA remain mandatory.
- No candidate package, reference image, execution flag, signature, gate table, deadline or native ticket rule is changed. Actual124/126 visual coverage still cannot authorize promotion.
- The reviewed selector scope is windows1–6. Window7 requires a reviewed scope extension and fresh complete receipt; it is never silently accepted as a seventh window.

## Reproduce offline

```sh
bash benchmark/2026-10-08-u14-stage-b-selector-fix/replay-selection.sh
python3 benchmark/2026-10-08-u14-stage-b-selector-fix/test_selector.py
python3 benchmark/2026-10-03-u14-stage-b/test_promotion_u14.py -v
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test --manifest-path tools/spec-checks/Cargo.toml --test u14_stage_b_selector_fix
```

Only the first command reads existing candidate hilogs. All other fixtures are local; there are no board, lock, VM or SSH operations. `validation.json` records fresh exits and log hashes; `landing-paths.txt` includes the actual CLI, Stage B wiring/templates/source receipt and this packet. No unrelated worktree modifications are offered for landing.
