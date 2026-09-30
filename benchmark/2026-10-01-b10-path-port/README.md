# B10 live-path migration, without rewriting freezes

The landing imported historical author-specific paths under temporary exceptions.
Blind replacement would also change live sources pinned by old prediction manifests.
The rule is now explicit: port unpinned live inputs; preserve frozen bytes and disclose
any live-source pin instead of silently rewriting its checksum.

Baseline master: `a29ec98102f07c8c6aecaa18937694a70a74c383`.
`results.json` inventories all **10 temporary files** and **3 permanent copies**:
**6 temporary memberships removed** (5 scripts and one archive-location comment),
**4 retained** pending a separately authorized freeze/cache migration.

## Retained live pins

| Live file | Reason to retain the existing exception |
|---|---|
| static-wall-prediction/registration_sources.py | Compressed `v3/jni-results.json.gz` (and the root cache) pins this live input; `jni_gate.cached` refuses its changed SHA. Plain-text SHA search misses compressed provenance. |
| static-wall-prediction/scan_jni.py | `v4-r2/freeze.json` pins the live absolute source path and SHA, not just the independent background-start frozen copy. |
| static-wall-prediction/update90.py | `task90-r15c/freeze.json` pins its `scanner_sha256`; changing it breaks historical scanner identity. |
| v2-scanner-feedback/profile.py | The live `SHA256SUMS` pins this source and is itself embedded under r17op `freezes/v3/evidence/b10-SHA256SUMS`; retained conservatively rather than invalidating that transitive provenance. |

These are **not new approvals** or permanent conversions. The three original frozen
copies retain their permanent entries unchanged. All unrelated registry entries are unchanged.
The outer loop should apply only the six membership deletions to its latest registry,
not replace an advancing master registry with this branch's baseline snapshot.

`prepare.py` is safe to port: its freeze resolves `code/prepare.py` inside the frozen
directory, not the live generator. `extract_unified_failures.py`, `collect_results.py`
have retrospective provenance hashes, not a prospective
live-source freeze; those historical receipts remain unchanged and refer to the prior
commit. No old report or checksum has been regenerated to match the new code.

## Resolution and validation

Live input defaults use `lab_paths.workspaces()` (`WORKSPACES` takes precedence).
The two historical sibling repositories resolve below `WORKSPACES.parent` as before.
Finalizers get their own resolved base instead of inheriting the pinned scanner's
author-specific `BASE`; the retained scanner and its consumers are not claimed fully portable.
The archive comment uses `$LAB_HOME`; it executes nothing.

```sh
python3 benchmark/2026-10-01-b10-path-port/test_port.py -v
```

Imports run in fresh subprocesses with a different WORKSPACES and do not invoke
generators. Tests check the exact exception delta and all 13 before/after hashes.
Live source changes may invalidate scanner caches by design; historical cache files
and their SHA receipts are not edited.

The first overlay run exposed the compressed registration-source pin through
`b10_jni_gate_blocks_new_missing` and `b10_v3_cache_and_exceptions`. Its attempted
port was reverted byte-for-byte and its temporary membership restored; all other
temporary source hashes were then searched in gzip evidence too. No old selector,
cache SHA, or exception approval was changed to hide this finding.

Final fixed-master overlay: path gate **0 violations**; spec gate exits **0**
with **64 passed / 9 approved exceptions / 0 unexpected failures**. Cargo itself
still exits 101. See `HANDOFF.md` for the six frozen scoring dependencies that
are absent from baseline master, the WORKSPACES prerequisite, and full receipts
in `validation/`.
