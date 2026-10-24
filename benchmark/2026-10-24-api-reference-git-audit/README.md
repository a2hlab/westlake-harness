# API observation build-reference audit — Git metadata only

**Both expected historical SHAs are valid. The current-path mismatch is not evidence that the old observations used the newer generator. Keep the full-table reference failure visible.** No historical script body was exported, restored, reconstructed, semantically inspected or executed. The target is conservatively treated as within the stopped-object boundary; only Git metadata and opaque byte digests were used.

The affected public observations are:

- `OBS-20261019-REENTRY`, `/rows/0/build/0`, path at observations.json line 34.
- `OBS-20261020-61B-EXISTING-R2-NORMAL-ICON-FEED`, `/rows/27/build/0`, path at line 2416.

Both refer to `benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh`, expected SHA **c2855d54eb7acea0502731a5be5c1310a6d9471048beae11df59d8186a3b0667**. Their public JSON introduction commits are respectively `207edc4c2e72eeca747da57b7a02c56e4770de3a` and `bf117897c7d2420321026e4ee6d3d002821b484a`; both introduction objects contain this same reference and resolve the script to the historical blob below.

| State | Commit / Git blob | Content identity |
| --- | --- | --- |
| Historical generator | commit `9d81797952d9ef041f2910faa6d716468115fa23`; blob `c02e8aaeb2b1918aec33912bd7c8e06306c48994` | 12,746 bytes; SHA c2855d54… |
| Changed generator | commit `14f691a59ba07f5d28eb5c6c5cb5f3df1411f967`; blob `13172bdea97a8549f27020bf5a1752eb0de94b31` | 16,638 bytes; SHA `0862a334f863d4de3bf3d4c4dda7ab1df7c6000e3b0e3d02e6c46f014aaf84d3` |

The modifying commit is titled “Require pinned board inputs and preserve complete package build commands”; its parent is `0d858b22f9119c13f42a6174377062cfad1db5b0`, where the same path still resolves to blob c02e8aae…. This conclusion uses the raw Git object transition, not a script-body diff. Full metadata and SHAs are in `results.json` and `git-metadata.json`.

## Minimal disposition within the current boundary

The old rows describe historical evidence; they should conceptually be anchored to the historical source identity, **not corrected to the current generator SHA**. However, `render.py:30–36` accepts a repository-relative ordinary file and compares its current bytes to the recorded SHA. It does not resolve a Git commit/blob. It fails before writing CSV/HTML (writes begin at line 38). Appending commit metadata or using a Git URL in the path does not satisfy that file check.

Therefore this task makes **no row or renderer changes and does not materialize a historical source snapshot**. Retain the existing red gate. If the outer lane appends an independently supported new candidate observation, preserve all prior row objects and explicitly report “JSON appended; HTML/CSV refresh pending the existing historical-reference mismatch”; do not report full-table verification or regenerated publication. Any future historical-reference format/tool change would be separate work, not a silent exception here.

The main observations file already has unrelated working-tree changes; its sampled SHA and main HEAD are recorded, rather than falsely claiming this working copy is the committed HEAD version. This isolated report is the only new output. Shared Git refs are already known read-only for this lane, so no denied Git write was retried: `author_commit=null`, no push. The outer lane can commit the report using the path-only list.
