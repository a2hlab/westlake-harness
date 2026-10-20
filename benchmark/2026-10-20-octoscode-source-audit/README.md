# d4fa source/build/API reference closure audit (2026-10-20)

Finite, explicitly authorized read-only audit (outer task #1, branch `analysis/outer-t16-t17-api-20261020`). No rebuild, no device calls, no new implementation or spec. This README is evidence-first; every claim below names the file and field it was read from. Receipts are as-of the frozen inputs supplied on 2026-10-20 and are not assertions about parent current live work.

## Provenance (outer-supplied, not independently verified)

- Snapshot tree commit `9df9bf380` — outer-supplied provenance. Git metadata access was denied by the sandbox in this session (`git rev-parse HEAD` → not a git repository / Operation not permitted), so HEAD was **not** independently verified. Recorded as GAP-05; no sandbox repair attempted per outer addendum.
- MAIN HEAD `2aeb45641a3bfbc19a95f681e58ea4b83e29f9df` — outer-supplied via `.octos/source-audit-main-inputs/origin.json` (exact `git show` bytes copied by outer). Sibling MAIN direct reads were denied (`Operation not permitted`); the supplied copies are the MAIN source root for this audit.
- `snapshot.json` internally records `main_audited_commit` `499c42493847423331eed2512975d115d4055c26`.

## What was independently verified in this lane (2026-10-20)

| Check | Result | Evidence |
|---|---|---|
| Snapshot payload integrity | **138/138** SHA-256 recomputed and match `snapshot.json`; byte sizes 138/138 match | `sources/api-implementations/bridge-d4fa-source-snapshot/snapshot.json` → `files[]` |
| Outer MAIN input copies | **60/60** SHA-256 match `origin.json` recorded hashes | `.octos/source-audit-main-inputs/origin.json` |
| T18 production source-index | **21/21** SHA-256 match | `…/2026-10-20-t18-audiotrack-production/source-index.json` |
| T18 size source-index | **25/25** SHA-256 match | `…/2026-10-20-t18-audiotrack-size/source-index.json` |
| Base-50 accounting | **50/50, zero unaccounted**: 38 retained original `out-touch21/fd/bridge15` objects (name-mapping verified here), 9 focus34 later-layer objects (author-recorded keys, see below), 3 mc46/ability38 replacements (replacement source SHA verified here) | `recipe.json` link list vs `snapshot.json` `base_source_coverage` |
| T18 recipe shape | 52 link `.o` (38 touch21 + 9 focus34 + 1 mc46 + 2 ability38 + 2 CRT), exactly 1 compile (`oh_audiotrack_shim.cpp` → `audio.o`), 720 input pins | `…/t18-audiotrack-production/recipe.json`, `input-pins.json` |
| API33 canonical landed state | **5/5** canonical target copies SHA-256 match delivery.json's recorded **new** hashes and correctly do **not** match `expected_target_before_sha256` — the update landed | `…/t17-t18-api-update/delivery.json` → `canonical_updates[]` vs `…/2026-10-19-api-progress-update/*` |

## What was inherited (not recomputed here)

- **focus34 key verification (9/9 `key_match=true`)** is inherited from the source snapshot authors' verification recorded in `snapshot.json` → `focus34_object_dependency_keys[]`. This lane did **not** re-run object identity/key verification (out of scope; no repeated object verification was requested). Verified here only: all 9 focus34 object paths appear in the T18 link inputs.
- **52 link object hashes were not re-verified** against `input-pins.json` — the supplied pins carry full SHA-256 per pin, but object bytes were not in scope for this lane.

## The three base-object replacements (documented, not missing)

| Base object (not in link) | Link object used | Replacement source (SHA-256 verified here) |
|---|---|---|
| `…_oh_mediacodec_shim.cpp.o` | `$INPUTS/out-mc46/patched/oh_mediacodec_shim.cpp.o` | `mc46/framework/core/jni/oh_mediacodec_shim.cpp` |
| `…_oh_window_manager_client.cpp.o` | `$INPUTS/out-ability38/native-policy/oh_window_manager_client.o` | `ability38/framework/window/jni/oh_window_manager_client.cpp` |
| `…_oh_input_bridge.cpp.o` | `$INPUTS/out-ability38/native-stack/oh_input_bridge.cpp.o` | `ability38/framework/window/jni/oh_input_bridge.cpp` |

SDK/toolchain/external pins (10 `$SDK`, 57 libs, 544 headers, 60 toolchain files of 720 pins) are external dependency pins, not absent project implementation.

## Gaps (details in `gaps.json`, severities as-of frozen 2026-10-20 receipts)

- **GAP-01 (medium)** — original mc46 final compile/link stdout+stderr+rc **NOT_LOCATED** (`build-entry.json`, closure `remaining_gaps[0]`). New exact Mac relink receipts exist (rc=0) but are new receipts, not historical replacements.
- **GAP-02 (medium)** — external durable archive `REQUESTED_FROM_CX_SEAL_NOT_YET_RECEIPTED` (`snapshot.json` `external_archive_status`); input chain remains in mounted Orb storage.
- **GAP-03 (low)** — T18 device registration/audio playback **UNVERIFIED** (`results.json` `runtime_registration`/`audio_output` = unknown, `device_calls=0`); static candidate only.
- **GAP-04 (low)** — API33 remote publication **NOT_VERIFIED** (`observations.json` `remote_publication_verified=false`; delivery `main_written=false`).
- **GAP-05 (info)** — both tree HEADs are outer-supplied provenance (sandbox git denial recorded, not repaired).
- **GAP-06 (info)** — T18 entry is incremental relink + one owner compile (`complete_source_rebuild_of_all_bridge_objects=false`); not a whole-source rebuild and not audited as one.

## Deliverables

`README.md`, `gaps.json`, `results.json`, `landing-paths.txt` in this directory. See `results.json` for machine-readable check counts and limitations.
