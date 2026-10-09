# Demo baseline: verified APK inventory (cx-bms t1)

## Evidence first

The previous lighting total was not a first-content total: the leadership gallery
contains **129 signed keys / 128 packages**, but only **94 content-bearing package
cards**, **32 empty/loading cards**, and **2 error-dialog cards**. Installing 128
packages does not satisfy the campaign's 100-content-package gate.

`demo-manifest.json` is an **offline, disabled inventory**, not a board sign-off.
All 129 local APKs were freshly hashed and their binary AndroidManifest package
was read with androguard 4.1.4. SHA/package/key must agree with the signed metadata
and its hash-pinned source `record.json`. The gallery-selected screenshot's own
record must independently agree; its screenshot SHA must match that run receipt.
`identity-checks.json` preserves the verification for both Noice versions.

The scope is checked against the actual 126 `verdict=lit` reference keys plus the
three U14 window-1 signed gains, not just against a copied count. Each selected
row cites its source/sign-off, selected run record and screenshot hashes. Existing
Chinese labels, versions and purposes come from the 10-08 metadata for these exact
APK bytes. No new board access, VM, SSH, installation or screenshot was performed.

## Selection and downstream interface

- `apps`: 128 distinct-package installation rows. `key`, `package`, `apk`,
  `apk_sha256`, `version`, `name_zh`, `category`, `is_game`, `install` and
  `demo_order` are the runner-facing fields; `native_sidecars` comes from the
  selected run receipt, not an inferred directory glob. Sidecars are receipt
  identities, **not a fresh sidecar-validation claim**; resolve them before install.
- Noice: install **fd-noice 2.5.7** once, following the gallery's selected card.
  `noice` 2.5.1 remains a signed alias with its independently verified APK identity,
  but is not a second install. The different APK hashes are explicit selection,
  not equivalence or a silently ignored conflict.
- All **12 signed games** are mandatory installs, including Luanti (`fd-minetest`,
  empty first screen) and SuperTuxKart (`fd-stk`, SDL error). Neither is counted
  as first content. Game/tool/benchmark entries from the nonlit corpus are listed
  separately with real-run first-fatal evidence, or explicit unknown.
- All 32 empty/loading candidates have `needs_first_tap=true`: a recorded first
  interaction is needed for assessment, **not a claim that one click succeeds**.
  Every proposed coordinate has `coordinate_status=unverified`, requires layout
  confirmation, and is never an executable blind-tap instruction. The per-row
  oc-t4 table has 26 likely and 6 uncertain proposals; its overlapping 24/5/3
  header groups are not a disjoint count. Text input/drawing suggestions explicitly
  set `requires_more_than_tap=true`. No proposal joins the 94 content selections.
- The two errors (SuperTuxKart and Termux) remain separate from empty/loading rows.
- `special_apps` records cc-t3's selected Toutiao Route B and its pending
  coexistence/acceptance gates; BoatAttack remains cc-wiki/t2b pending. Neither
  inflates the verified installation/content counts.
- `board_choice` consumes cx-t0's report and outer's 20:52 selection of **61b**;
  it is not a new board probe, promotion or sealing. The selected
  APKs total **1,756,238,122 bytes**; APK-size-times-three storage estimate is
  **5,268,714,366 bytes**. No free-space/fingerprint result is invented.

Empty/loading keys and per-key assessment fields are in the manifest. The received
oc-t4 handoff is
`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-09-demo-baseline/first-tap-candidates.md`.
Its exact bytes and hash are retained under `evidence/first-tap-candidates.md`
and `first-tap-assessments.json`; outer's 20:58 partial approval explicitly excludes
coordinate validity. Per-row no-window notes conflict with the source's global
fullscreen summary; this lane imports proposals, not that universal causal claim.
At least six additional packages still need
actual content verification to reach 100; a predicted click is not that verification.

## Games without a new U14 observation

`unlit_games_and_tools` includes Unciv, Shattered Pixel Dungeon, Mindustry, PPSSPP,
Subway Surfers, Flowit!, Chess Clock and glmark2. The existing U14 cluster table
has no U14 observation for these entries; replayed first-fatal evidence is explicitly
version-tagged **U10.1-T8**, not presented as a current U14 conclusion. White-window
runs with no terminal and disappearance without a linked cause remain unknown.
The manifest retains the actual hilog/record hashes and PID-filtered terminal/root
line numbers; no fix is attempted.

## Reproduction and rejection tests

```sh
"$WORKSPACES/westlake-inputs/venv/bin/python" \
  benchmark/2026-10-09-demo-baseline/build_manifest.py
python3 benchmark/2026-10-09-demo-baseline/test_manifest.py
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test \
  --manifest-path tools/spec-checks/Cargo.toml --test demo_baseline demo_baseline_manifest
```

The builder checks all inputs before replacing the manifest. Missing/corrupted
APKs, a wrong package, changed source record, conflicting package selection or
incorrect signed coverage rejects with the offending key; no new manifest is
written. Eleven tests cover identity rejection, no-output-on-SHA-failure, 128/129
coverage, all twelve games, explicit Noice deduplication and empty/error exclusion.
The already-landed cx-t0 `demo_baseline_board_choice` selector is preserved
unchanged alongside the new inventory selector. Its helper/evidence remain
cx-t0's master files; they are not overwritten by this landing. The shared
`README.md` is likewise retained: this inventory documents itself separately.
The scoped local cargo run only selects `demo_baseline_manifest`, since Git
permissions prevented importing cx-t0's other master files into this worktree.

## Integration status

The requested merge of master `aa6c584bf2` was blocked by read-only Git worktree
metadata (`ORIG_HEAD.lock`, permission denied). The approved master contracts and
sources were read directly. Changes remain in this worktree for outer landing;
no push, forced checkout, index repair or unrelated cleanup was attempted.

Use `landing-paths.txt` with the master `land.py --preflight`. Raw build/test
outputs and their exit codes are retained under `evidence/` and `validation.json`.
