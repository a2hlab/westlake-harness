# Post-reboot 61b regression driver and signoff comparison

## Evidence and limits

The offline known answers resolve **128 actual t3 outer-selected records**, including
signed retry batches. Copying their final captures gives `same=128, changed=0,
missing=0`; replacing exactly two final images gives `same=126, changed=2,
missing=0`. The real `contact_sheet.sh` invocation produces only those two tiles.
See `reboot-regression-evidence/cli-knownanswers.json` and `tests-mac.txt`.
The canonical symlink view is tested explicitly; a plain `Path.rglob` would miss
its linked key directories.

This delivery has **not run on a board**. Tests exercise preparation, refusal,
failure sequencing, and real historical evidence. They do not certify a fresh
reboot, future screenshots, the Route B foreground hook, or BoatAttack rendering.
Only the outer reviewer signs UI results. No reboot, recovery deployment,
installation, lock, or board command was performed while developing this delivery.

## Prepare one complete round offline

From the worktree containing this directory:

```sh
export WORKSPACES="$(cd .. && pwd)"
T4=benchmark/2026-10-09-demo-baseline/t4
ROUND="$WORKSPACES/westlake-inputs/demo-post-reboot-round-<unique-id>"
python3 "$T4/run_post_reboot.py" --out "$ROUND" \
  --boot-before "$PRE_REBOOT_BOOT_ID"
```

`PRE_REBOOT_BOOT_ID` must be the UUID recorded **before** a separately approved
reboot. The driver does not reboot or replay U13. Before execution, signed U13
must already be restored and all 128 pinned apps still installed. The existing
t3 install receipts are required; missing/failed receipts refuse preparation.
APK inputs are checked again before the first lock. Input availability or a
changed APK is a refusal, not permission to reinstall or repair the board.

The default inputs are `demo-manifest.json`, t3 `install-index-final.json`,
`shot-tiers.json`, and the signed U13 61b smoke specification. Preparation reuses
`prepare_t3.plans`: 128 unique packages in eight disabled windows of at most 18
keys. The capture delay is independently pinned per APK/package: **121 at 10 s,
7 at 20 s**. `--tiers` may select a separately approved exception table, e.g. the
t3 final approved table for dddmodel2. Both tables are bound by their actual SHA.
The 32 empty first screens keep `no_tap_map`; no first-screen tree or tap occurs.
Approved CircuitTraining/BeeCount ability fallbacks are copied from the t3 plans
and still validate the queried BMS ability before use.

### Execute after a separate outer authorization

```sh
python3 "$T4/run_post_reboot.py" --out "$ROUND" --execute --detach \
  --authorization '<outer ACK(91) authorizing this full regression round>'
tail -f "$ROUND/round.log"
```

This command is documentation for a future approved window, not authorization
from this offline task. It detaches the **whole** driver. Windows execute
sequentially on the full 32-character 61b key, through the existing t3 adapter and
master `board_run`: announce, lock, verify 319 U13 identities and both fingerprints,
activation smoke, launch-only captures, verify again, unlock. Each window is
bounded by 45 minutes, with no new key after 35 minutes. Mac HDC operations use an
OrbStack wrapper; no shared VM/HDC restart occurs. All windows must have one
unchanged post-reboot boot ID, different from the recorded old boot ID.

Source files, input copies and prepared plans are SHA-bound before dispatch.
A runner/identity failure stops remaining windows. A cutoff leaving missing keys
also stops with partial evidence; it never prints complete-128 success. A failed
final identity gate preserves the runner's lock for recovery. Further execution
requires fresh, externally approved plans rather than silent retries.

### Standard output and special slots

`window-*/runner/<shard>/<run-id>/<serial>/<key>/record.json` is the unchanged
capture layout. `$ROUND/final/<serial>/<key>` links only the requested ordinary
key records, excluding smoke/control runs. `$ROUND/facts.txt` is produced by the
master `run_facts.py`, including actual `alive_t10` or `alive_t20`. A successful
round's `round-complete.json` means 128 records were collected, **not** 128 lit UIs.

Toutiao and BoatAttack are separate reserved slots, not part of the 128-package
denominator (`t4/README.md` and the manifest use this same distinction).

- `round.json.special_slots.toutiao`: set `enabled=true` only with the reviewed
  **already-installed** Route B host's exact file-path/full-SHA pins in
  `identity_files`. The fixed host is `org.westlake.imehost`. Its dedicated window
  performs an actual foreground desktop click and collects t5/t20; it does not
  use direct `aa start`, install a host, or kill a Route B watchdog/spawner.
  HAP host-UID survival is marked as a proxy, not Android child survival. The
  special run has its own standard records/facts under `special-toutiao/`.
- `special_slots.boatattack`: defaults to `enabled=false`, `plan=null`. Enable
  only with an externally reviewed, SHA-bound 61b `board_run` plan (at most
  30 minutes and a final hook). The driver provides no overlay/install recipe;
  BoatAttack inputs and rollback remain that plan's responsibility.

Both enabled slots refuse before device access if their required pins are absent.
This leaves the currently unsigned overlay choices explicit rather than guessing
artifacts or silently changing the 128-app baseline.

## Compare with the exact t3 signoff

```sh
python3 "$T4/regress_vs_signoff.py" "$ROUND/final" \
  --out "$ROUND/comparison" --sheet
```

Default signoff is `../t3-outer-signoff.json`; `--baseline-t3` locates the matching
persistent t3 raw evidence. The comparator resolves the **signed batch** for each
key, including successful retry batches, and refuses unresolved/ambiguous baseline
records. Do not substitute another attempt. Large raw captures stay in persistent
storage; a clean checkout without them cannot reproduce the 128-record fixture.

`comparison.json` classifies every signed key:

| Category | Rule |
| --- | --- |
| `same` | Final scheduled image bytes and APK/package, status/error, final-shot tag, and final-slot UID survival equal the signed record. |
| `changed` | Evidence differs or existing final bytes fail their recorded SHA; this is an **outer image-review queue**, not a regression verdict. |
| `missing` | No record or promised final capture is absent; an earlier t5 never substitutes for the last scheduled slot. |

PID numbers and timestamps are ignored. Dynamic UI data, clock labels, or switching
from a signed t20 to t10 may conservatively create `changed` entries. The tool does
not infer equivalent UI from similarity or process survival. Duplicate observed
keys refuse; supply the canonical final view. Extra keys are reported separately.
Missing keys remain a separate queue and are never marked same.

`same.keys`, `changed.keys`, `missing.keys`, and `reference-index.json` retain the
per-key audit trail. With `--sheet`, `changed-contact-sheet.jpeg` contains only
changed keys, using the existing `scripts/lab/contact_sheet.sh`; its row/column
mapping is `changed-sheet-mapping.json`. A zero-changed result produces no JPEG.
A missing image in a changed tile is explicit grey rather than invented content.

## Offline verification

```sh
python3 -m unittest discover \
  -s benchmark/2026-10-09-demo-baseline/t4 \
  -p test_regress_vs_signoff.py -v
```

The actual-record tests skip explicitly if persistent t3 evidence is unavailable;
that is not a pass of the known-answer fixture. Driver tests mock subprocesses and
assert zero preparation device calls, exact 128-key coverage, SHA refusal,
authorization refusal, disabled special slots, and stopping before the next window
when a shard fails. Fresh-board acceptance remains pending a separately authorized
execution and outer screenshot review.

The existing broad t4 lifecycle was also run: exit 1, all five scenarios Skip
because `demo_baseline_stability` matches no Rust test. `lifecycle.json` preserves
that result. This offline delivery does not claim those board/human scenarios passed.
