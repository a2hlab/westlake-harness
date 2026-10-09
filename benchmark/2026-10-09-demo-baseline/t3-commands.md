# t3 command preparation — disabled, no device execution in this delivery

## Input agreement with cx-bms

`prepare_t3.py` consumes `demo-manifest.json` as an `apps` list with
`key`, `package`, full `apk_sha256`, optional `install:false`, and optional
`needs_first_tap:true` plus `first_tap` or `tap_instruction`. Other demo metadata
is retained. Exactly one key per distinct package; duplicate Noice aliases reject.
Order follows the list (cx-bms should sort it by demo order). Unknown/custom input
layouts must declare `input_root`; conventional original and `cv2-*` roots use
the existing VM original/corpus-v2 directories. This is an explicit interface,
not a claim that the still-pending manifest was received or validated.

Only local output is produced: a compatible `batch-apps.json`, singleton key
files and ordered `board_run` windows of at most12 keys. Window45min/cutoff35min,
fresh output root, **execution_enabled=false**. No native/JAR/boot deployment,
no automatic restoration to another generation, no other board in any plan.
`after_lock` and `before_unlock` remain unset until a read-only effective identity
verification hook is supplied; this is a documented preparation dependency,
not a hidden no-op verification. Manifest arrival does not enable a plan.

## Offline commands (safe now, no LOCK)

Set WORKSPACES using `scripts/lab/lab_paths.sh`; R is this delivery after landing.
Run preparation **in the VM** so `$HOME` is the original APK input home:

```bash
R="$WORKSPACES/westlake-harness"
D="$R/benchmark/2026-10-09-demo-baseline"
P="$WORKSPACES/westlake-inputs/reports/demo-t3-$(date -u +%Y%m%dT%H%M%SZ)"
orb -m a2hlab env WORKSPACES="$WORKSPACES" python3 "$D/prepare_t3.py" \
  --manifest "$D/demo-manifest.json" --out "$P" \
  --smoke "$R/benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json"
python3 "$R/scripts/lab/board_run.py" "$P/window-01/plan.json" --dispatch
```

Run **without --execute**, for every shard/input_root in the generated plan,
and save its stdout. Real bms_batch input resolution rejects missing input,
wrong package/SHA, sidecar discrepancies or unknown key before any board access:

```bash
orb -m a2hlab env WORKSPACES="$WORKSPACES" python3 \
  "$R/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py" \
  --manifest "$P/batch-apps.json" --input-root '<that shard input_root expanded in VM>' \
  --keys '<that shard singleton key>' --resolve-inputs
```

Recompute final manifest APK-size×3, include Toutiao/BoatAttack extras, compare
with fresh read-only /data space. Verify all pinned packages against cx-bms's
signed record identities. No execution until these checks and outer scheduling
are complete. If t2/t2b changes effective runtime, bind a fresh smoke spec to that
state; do not use the U13 example blindly. A reboot/self-start solution belongs
to t4/t5, not this install-only command preparation.

## Future authorized execution (not run here)

The master `board_run.py` starts a Mac supervisor and invokes the existing
master bms_batch with default Mac HDC from env-mac. It provides held lock checks,
boot guard, hilog/settings preflight, install, launch and focus evidence. As in
the accepted production dispatches, use master and `--detach`:

```bash
source "$WORKSPACES/westlake-inputs/env-mac.sh"
python3 "$WORKSPACES/westlake-harness/scripts/lab/board_run.py" \
  "$P/window-01/plan.json" --detach
```

Before this command: announce91 board use, fresh orb/USB/bind/vmgr preflight,
outer approval, set execution_enabled=true **only for the scheduled window**,
fill after_lock/before_unlock with current-state read-only identity checks,
and make a fresh output directory. Each plan targets only full61b serial.
Do not start two windows together on the same board. Read the detached logfile;
finish the current key by45min, no new key after35min, unlock between windows.
Next window contains only keys without a completed record. Runner's captured
rc1/foreground_unconfirmed is not an image verdict; rc≥2/incomplete records
stop the remaining shards and go through before_unlock. Preserve all evidence.

The runner's standard singleton command has `--execute --reinstall --hilog
--shots 5,20`; screenshots are click-relative. For explicit direct diagnostic
reproduction under an already authorized held lock only, bms_batch additionally
accepts `--wait 20 --hilog 20 --shots 5,20 --focus-check`, full serial and lane;
this direct form is not the orchestration path for t3.

## First interaction and accounting

The existing generic board_run does **not** consume demo `needs_first_tap`.
`first-tap-pending.json` lists the exact pending instructions. Keep the initial
capture; on the same install, record tap target/coordinates/time and take an
additional `snapshot_display` image as an authorized t3 interaction. Do not
claim the pre-tap image was post-tap or reinstall and lose the first interaction.
Coordinate that operator step when cx-bms/oc-t4 deliver the actual instructions;
this delivery does not invent tap locations or add input automation.

After each window:

```bash
python3 "$WORKSPACES/westlake-harness/scripts/lab/run_facts.py" '<runner directory>'
```

Paste actual facts verbatim. Hand all t20/post-tap images to outer with key,
package, image SHA/path and first fatal or unknown. Sign three statuses:
own-content lit / empty-loading-error partial / not lit. Missing capture=unknown.
Only distinct packages signed own-content count toward100. Machine capture and
alive totals cannot compute that human content verdict.
