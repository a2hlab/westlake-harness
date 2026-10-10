# Explicit 61b t3 regression reference

## Evidence first

The previous orchestrator required a healthy 5cd reference even when 5cd was absent from USB/HDC. The original 61b t3 signed baseline already has 128 selected records; it is a different, explicitly named reference, not a silent substitution. This revision introduces `--reference 5cd|61b-t3` (default `5cd`) and binds the chosen kind into the outer-authorized plan. No board, lock, VM or SSH was accessed. A disabled preview is not a live seal or a UI pass.

| Item | Evidence / SHA256 |
|---|---|
| Original 61b signoff | `$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/t3-outer-signoff.json`, `0e9b825a0ccbfcbe6af0bc1ccd7f93d55d323e1869b8ecdc957a7591048aa387` |
| Corresponding t3 selector directory | `$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/t3`; the existing comparator resolves each signed batch and its selected record, including sibling-worktree mappings |
| Pinned selected records + final images | `evidence/reference-t3-index.json`, 128 entries; `a6409e5a85522e583d96e25947b99aa9161c06ad8bf58ed9f847f835a0267dc4` |
| Partial Enforcing observations | `evidence/enforcing-prerun-89.json`, 89 entries; `17d506d7829dcfea1eb936c91c7d254ccc13c55ff28caf1cabcce8575ed74674` |
| Disabled v1 reference plan | `plan-reference-61b-t3.json`, `b9e171e555f8834733f195a3ebe24210e84df1ee70ae64d7f47f680819f722d4` |
| Known answers | `evidence/tests-reference.txt`: 57 tests, exit0 |
| Independent generation | `evidence/build-reference-{1,2}.txt`: plan/index/notes byte-identical across two builds |
| Fresh previews | `evidence/dry-run-reference-61b-t3-v1.txt`, `dry-run-reference-61b-t3-v2.txt`, `dry-run-reference-5cd-v1.txt`; exit0, zero transport |
| User paths / landing | `evidence/user-paths-reference.txt`: 22 files, 0 violations; `evidence/preflight-reference.txt`: 22 files, 0 too large, 0 user paths, 0 data home paths |
| Driver | `scripts/lab/demo_seal_61b.py`, `9043076f50ea6ead20e9d85c3d643786b39ea6cf45de5db1004ea238605c56a8` |

## Reference binding and receipts

The plan's `reference` object records kind, signoff file path/SHA and baseline record directory. In `61b-t3`, `record_index` additionally pins all 128 selected record files and final image files; directory contents are not treated as an unhashed reference. The signoff must have board `61b0657200000000000000000324012c`, exactly the canonical path suffix and original SHA. Record/image pins are checked before any execute dispatch and again after comparison; comparison baseline_record must match the indexed record for each key. Unused 5cd input/directory placeholders do not block this branch. In default `5cd`, the explicit reference must match the legacy signoff_5cd and baseline_5cd_t3 bindings, preserving the original comparator invocation and 5cd serial check.

The selected reference is passed to providers through `DEMO_SEAL_REFERENCE` and `DEMO_SEAL_REFERENCE_SIGNOFF_SHA`. A `regression_review` receipt still requires current plan SHA, current autonomous boot ID, fresh outer signature, no_mac_repair, exact comparison SHA and pinned evidence. Additionally:

| Reference | baseline_serial | Required regression checks | Additional receipt fields |
|---|---|---|---|
| 5cd | `5cd1e3dd00000000000000000923012c` | all_128_observed, no_regression_vs_5cd, identity_unchanged | Existing receipt format retained |
| 61b-t3 | `61b0657200000000000000000324012c` | all_128_observed, no_regression_vs_reference, identity_unchanged | reference_kind=61b-t3, signoff_sha256=0e9b825a…(full SHA above) |

The compiled `seal.json.regression_reference` records the same kind/file/hash/index/annotation bindings, selected baseline serial, annotated comparison SHA and signed outer-review receipt SHA. The existing seal compiler and selfcheck are unchanged. `comparison.raw.json` preserves the original comparator output; `comparison.json` adds explicit reference provenance and, only in 61b-t3, Enforcing annotations before outer review.

## 5cd partial observations are annotations, not exemptions

The input is the existing `resume-organicmaps/compare-observed-89/comparison.json`, under `$WORKSPACES/westlake-harness-tools-inventory/benchmark/2026-10-10-5cd-demo-regression/`. The offline builder resolves its relative paths against that source worktree, follows the observed-89 aliases to completed-full-round/continuation records, verifies record serial/key/finished status and recomputes the comparator signature. The notes pin the comparison, global `enforce-at-capture.txt` (`1`) and every actual finished record. This global capture evidence is **not** claimed to be a continuous per-key enforcement trace.

The partial report has **89 changed / 39 missing**, with semantic triage **63 same_class / 26 suspect**. `changed` may merely mean image bytes differ; it is not 89 failed UI verdicts. For a fresh 61b comparison, a row is marked `env_enforcing_suspect=true` only when both reports classify that key as changed and package/APK SHA match. Reasons/semantic triage from the 5cd row and overlapping reasons are attached for outer review. Candidate category, summary and changed-key membership remain intact; automatic_exemptions=0. An image-only match is weak correlation, not a causal Enforcing diagnosis. The 39 unobserved keys cannot acquire this annotation.

## Known answers and remaining work

New tests cover both reference kinds in v1/v2; incorrect file SHA; t3 board other than 61b; a correctly hashed but noncanonical t3 file; unknown/CLI-plan mismatched reference; wrong receipt serial/reference/signoff; drifted prerun record; annotations without waiver or app-identity substitution; and unsigned reviews refusing. The prior 46 tests remain green, with 11 added tests (57 total).

Use `build_reference_plan.py` to reproduce the disabled v1 plan/index/notes. For v2, outer must bind mode=v2, admitted active Boat overlay and the existing v2 regression admission; passing `--mode v2` to a v1 plan only permits preview and cannot authorize execution. Current pending provider/installer bindings are not filled by this reference revision. A new bound plan/driver SHA and fresh window authorization are required before execution. The prior failed attempts and earlier evidence files remain untouched.
