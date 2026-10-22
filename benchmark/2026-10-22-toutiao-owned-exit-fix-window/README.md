# T52 owned exit-fix window: fresh read-only admission and plan (for outer final review; not a write authorization)

Read-only only: no device write, no activation. Candidate SHAs are pending the outer's acceptance of T51.

## Fresh facts (boot 1b1febea, 7 s, writes 0)
- No lock holder. All 5cd checks pass:
  - 9 controls: SHA, mode and owner equal T46-P2. This observation's control bytes and metadata match the T48 final stat
    (the six files carry their T48 inodes). That does not prove the intermediate history.
  - 13 members: exact.
  - Labels: `data_file` for the six files and the ROOT dirs.
  - ready chain: cfg 897f9ca0 + `recover-v3-boat.sh` 291451a1, `ready=true`.
  - runtime124 and boot36: equal T44.
  - host: HAP b189, uid 20011300, token 537137511, datadir inodes unchanged.
  - power: 10000/10000.
  - all stops absent; 38 boot dirs.
- The T48 stage/backup (`diag-maint-t48-20261022-1748`) is still present with the same identity. It was retained by
  plan; T52 must use a new tag.

## Plan draft
- **Sequence**: T48 v3 reused, see `plan.draft.json`. M1 → R1 isolation → C1/C2 (expected last) → R2 → one normal tap,
  ≤180 s observation → M2 → R3 isolation → B1/B2 → R4 → one normal tap to verify → UNLOCK.
- **Guard**: `setopt pipefail`. Every guard/put rc is captured explicitly. A guard runs before **every** write and
  **every** `target boot`: holder, phase boot, budget, parent identity and labels.
- **Boot wait**: the rboot timer starts before `target boot`. A boot that times out is judged read-only; it is never
  resent.
- **Lessons absorbed from T48**: no write before the guard exists (M1); no guard inside a pipe (R2); click before
  waiting for events.
- **Observation**: record only events that occur naturally. No induced exit. If there is no exit, record
  "not triggered". A white screenshot is reported as white.

## Pending (filled only after T51 acceptance and a new outer signature)
- The six candidate files and six preimages with full SHAs. The watchdog is d45a8d36 and the owner fc63dae9 is
  unchanged; entry, members, env and expected are derived from the actual members table.
- The four env/expected sets, with the file SHA and the content SHA listed separately.
- The new stage/backup tag.
- The window signature.
- Values bound at window preflight.

Raw: `$HOME/.local/share/westlake/t52-readonly-admission-20261022`, MANIFEST 0378e840fd940e98… (102 files).

## Plan for final review (`plan.json`)
- Package: T51 package-01. The receipt is 2bc57323…, the source-lock 51138bd2…. Six candidate files and six rollback
  files are listed with full SHA and mode.
- env/expected sets (env SHA / expected-file SHA):

| set | env SHA | expected-file SHA |
|---|---|---|
| maint-forward | d1452d77c0bf654ca6164a3a66082cbee8467238fa430232efb484db9af72476 | d764a774a40c1e1e3a110358f037e142d79522905a6e4d563bd293ffbda9d2bf |
| candidate-enabled | 06b743715795db47a7623f624b22bf317dcf4d3f571101e78e9e5e168883140f | 64de20fe9e945a70a4d25819db60decafde02a81a4fe837d80fbe70e90a09a43 |
| maint-reverse | fac76e85403373a753a6a37cee02e4b96dae0a357f78ad6854497047faf6d600 | 50e76e69a56944c46b4a9024a786c8934ac7f09332423662b3294ccdf28c5651 |
| baseline | 44993dbc61116a4e67936ddc09af2ca7e19c9b2454599e16da7a2b907681b34a | 05c12ce34fea0a7a3746b4fe7c40b0cb676968ded8b1c21218fafca54a98b037 |

  Each expected file contains its env SHA. maint-reverse and baseline are byte-identical to the T51 package.
- New tag: `diag-maint-t52-20261022-1900`. The T48 objects are not touched.
- Preflight binding: exact SHAs of this fresh ctrl/members/labels/runtime/boot raw, plus ready chain, host, power and
  stops.
- Helper: `tools/env.sh` plus `rec.py`, `admit.py`, `ui.py`.
  - `rec` returns the real command rc.
  - `guard`, `guard4`, `mkdirs`, `put`, `put2` and `rboot` stop on any nonzero step rc.
  - Inside `put`, a second guard runs between file send and the ROOT replace.
  - `mkdirs` uses `guard4` (4 fresh-bound parents) before mkdir, then binds the 7 parents.
  - The main tree is derived from the git common dir.
- Guard scope: control-file writes, backup-directory creation and target boots. UI actions are bounded by the normal
  desktop flow inside the stage directory and do not write ROOT.
- The sequence, restore branches and stop rules are spelled out in `plan.json`.
