# Leadership gallery: mechanical adversarial audit

## Evidence first

The requested **129-key partition does not close**: `report-data.json` contains
94 shown + 32 minimal + 2 errors = **128 rows / 128 unique keys / 128 packages**.
The only missing key is **`noice`** (version 2.5.1). `fd-noice` (2.5.7, same
package) is shown once. This is consistent with package deduplication, but no
explicit alias-coverage row maps the omitted key into the requested partition.
No extra or repeated keys were found. Do not classify the omitted version as
minimal/error merely to make the arithmetic work.

`findings.json` binds the four outer deliverables and metadata from master
`c89296a4c6` by full SHA256, with unchanged before/after hashes. It includes
128 screenshot receipts, exact record and screenshot hashes, and signed-path
membership proofs. All checks are local and mechanical; **no screenshot pixels
were interpreted, no outer files modified and no board commands issued**.

| Requested check | Result | Evidence |
| --- | --- | --- |
| Screenshot directory, record key/package, APK identity and signed run | PASS: 128/128; wrong-object 0 | `screenshot_receipts`; 114 U14 window1–5 selected paths and 14 exact metadata references |
| Data name/purpose/pkg/cat exact metadata | PASS: 512/512 fields; also en/version/source 384/384 | `field_differences=[]` |
| Union is 129 keys, no repetition/omission | FAIL: missing `noice`; no duplicates or extras | `partition` and `KEY-COVERAGE` |
| Shown Noice package exactly once | PASS: only `fd-noice` | `checks.shown_noice_once` |
| HTML package/group/category arithmetic and captions | PASS at package level: 128=94+32+2; categories sum94 | `html`; 94 card captions exact, appendix rows32/2 |
| Cover 129 and126+3 | Original metadata scope closes; data partition does not | Requested129=reference126+gains3, declared n_keys129 vs actual128 |
| PPT gallery names/purposes | FAIL exact names: 92/94; purposes94/94 exact | `ppt.errors`; 11 slides, gallery slides2–8 have14/14/14/14/14/14/10 cards |

## Actionable findings

1. **KEY-COVERAGE**: keep one Noice display card, but add explicit key-to-package
   coverage for `noice` or clearly redefine the reporting unit with approval.
   An unrepresented key is not an additional unlit application.
2. **PPT-CARDS**: slide4 uses `Organic Maps` instead of
   `Organic Maps・离线地图与导航 & GPS`; slide5 uses `Noice` instead of
   `Noice：自然平静的噪音`. Both purposes match exactly. These are abbreviated
   names, not wrong-app pictures: picture blobs exactly identify their respective
   key-named thumbnails. Restore exact names or explicitly approve display aliases.
3. **SOURCE-COUNT-UNITS**: the cover says128 F-Droid +1 VLC. That is correct for
   the original **129 APK/key** scope, but the represented128 **packages** are
   127 F-Droid +1 VLC. Label the source-count unit explicitly; otherwise the
   128-app cover can be read as a contradictory129-app source breakdown.

Shown categories: efficiency17, tools27, audiovisual8, health10, games10,
system9, graphics4, education4, communication2, reading3 =94.

## Method and limitations

- `audit.py` reads the outer report at
  `$WORKSPACES/westlake-inputs/reports/2026-10-08-lit-apps/` without writing there.
- Signed-window paths are matched exactly against the five outer pair sheets
  and their signoffs; fallback paths must exactly equal the signed metadata
  screenshot reference. Same key with another unsigned path is not sufficient.
- PPT is read by **python-pptx 1.0.2**. Card caption pairing uses picture/text-box
  geometry, then exact JPEG blob hashes identify the key. The cover collage is
  not counted as gallery cards. All94 gallery picture blobs match key thumbnails.
- HTML embedded image bytes differ from the exported PPT thumbnails. This is
  recorded, not treated as wrong-object evidence: different encodings/resizing
  cannot establish a wrong app without further provenance or pixel analysis.
- This audit does not prove resized image derivation, judge blank/error images,
  revalidate runtime state or functionality, or inspect PDF content. PDF is
  bound by SHA only. The cover's UI-quality claims remain the outer reviewer’s
  responsibility.

## Reproduction and handoff

```sh
"$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python" benchmark/2026-10-08-lit-apps-gallery-check/audit.py
python3 benchmark/2026-10-08-lit-apps-gallery-check/test_audit.py
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test --manifest-path tools/spec-checks/Cargo.toml --test lit_apps_gallery_check
```

Audit execution exit0 means collection succeeded, **not that the gallery
passed**. Check the per-check verdicts and three finding IDs. Known-answer
tests require no external report files or `.artifacts` directory. Scoped raw
validation outputs and exits are in `evidence/validation/` and `validation.json`.
`landing-paths.txt` contains only this task’s reports, auditor and contract/tests.
External deliverables remain untouched; outer review/landing is required.
