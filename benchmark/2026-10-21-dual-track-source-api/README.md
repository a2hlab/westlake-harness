# G11 — dual-track source/build/API crosswalk (draft; authoritative table unchanged)

**What was wrong before:** the authoritative current-observations table
(`benchmark/2026-10-19-api-progress-update/observations.json`, 50 rows, as_of 2026-10-20) has **no
row** for the G08 ZIP-comment fix, the G09 build, the G12/G13 installer window, or T35–T38. The 315-row
atlas row JAVA-042 still reads `source_location unknown`, `current_deployed unknown`. This draft maps
each of those to exact main-branch files and SHAs. It merges nothing.

- Main read-only at `9084435f65`. Inputs the outer loop must re-check before merging
  (`expected_input_sha256` in `crosswalk.json`):
  - `observations.json` `8d5e7980…`
  - `render.py` `0276c50e…`
  - atlas `api-progress.json` `3e83dfdd…`
  - `source-delivery.json` `e4b36632…`
- [crosswalk.md](crosswalk.md) / [crosswalk.json](crosswalk.json): 9 draft rows, 65 file references.
  Each row carries its own results.json `status` verbatim in `observed_status`, so the summary can be
  compared against it. [gaps.json](gaps.json) lists 10 explicit gaps.
- Reproduce with `python3 -B -I build_crosswalk.py --source-root <main>` (default: the repository containing this script). Verify with
  `check_crosswalk.py`, which re-hashes 69 files and refuses any drift or scope upgrade, or with
  `cargo test --test dual_track_source_api`.

| row | class | verification scope kept |
|---|---|---|
| G08 ZIP comment (66b4e0a2, 44b05158) | public OH system component (installd libinstalls), not an Android API; JAVA-042 family | host Open only; patched device install NOT tested; Genshin NOT started |
| G09 build (7dc33a83) / archive (f45e7ec8) | same component: build recipe / provenance | 13/13 rc0, baseline 51e1b525 reproduced, candidate 7c24bd11 not deployed as of receipt (the receipt's `deployment_authorized=false` is an unsigned offline field, not absence of user authorization); archive c7ad6186 remote-verified |
| G12 prep / G13 window (9084435f) | same component: install transaction | offline delivery; device phases not executed **as of** `device-window/results.json`; outer later reported a 5ea G13 window opened 17:47:10 (before rc0, control running, no apply/install yet) |
| T35 (5824a0a9, 06c26e2f) | app-specific guardian evidence, not an Android API | white screen observed; cause INFERRED; live environ not observed |
| T36 (db5ebfa0) / T37 (53e5c670, 0d251eae) | app-specific guardian candidate / review | offline only; NOT deployed; white-screen fix NOT device-verified |
| T38 (d2ff2fa9) | app-specific guardian window archive | UNVALIDATED; two safety stops; window not executed as of receipt |

Historical Boat audio reuse and earlier sound confirmations are not used as evidence for any row. No
device, REA, build, or T38 code/test was run; nothing is frozen.

All "not executed / not deployed" statements are snapshots **as of the cited receipt** at main `9084435f65`; they do not negate later live execution.

**Rule set by this card:** a draft row's status must be readable against its own results.json `status`
in the same record. A crosswalk that can only be summarised, and not re-hashed, is not a crosswalk.
