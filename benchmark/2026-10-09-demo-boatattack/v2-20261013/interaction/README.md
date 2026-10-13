# BoatAttack V2 interaction evidence entry

The old window9 WMS check selected the highest system window and could discard a real racing image. Its two injections also did not establish the contract's five-touch/LAP/HUD requirements. This entry captures first, records WMS failures, and strictly checks the Boat window immediately before input. Collection success never means touch response or UI acceptance.

`tests.stderr.txt`: **9 isolated tests pass**. `preview.stdout.txt`: no device commands. Historical actual image findings and exact source/image SHAs are in `historical-review.json` and `sources.json`. Window9 rendered with stock runtime `18763dd4`, adapter `8ab85446`, JAR `6333bcab`, and the three pinned private libraries; its HUD appears stretched compared with the original PASS. No current t2b acceptance is claimed.

## Shortest execution path

1. Root authorizes T4's `../westlake-harness-t4/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/minimal/` deployment: exact five owned binds, current v3 startup ordering and precise v1 rollback. This runner does not install, bind, reboot or implement another deployer. Runtime stays stock `18763dd4`; sandbox/APK placement belongs to that deployment, not this entry.
2. After T4's layer is active on the authorized spare board, root fills a copy of `plan.disabled.json` with full serial, current kernel boot, exact existing lock owner, installed Boat UID and explicit local HDC executable. Root sets `execution_enabled=true` and signs the full plan and current runner SHA in a separate authorization. Independent caller pins the authorization SHA. No 61b/5cd consent action is permitted.
3. The entry checks owner/boot, installed APK and UID; starts a SHA-pinned keeper in a unique 0700 `/data/local/tmp/boat-interaction-<uuid>`; launches the actual desktop icon using the rehearsal's batch donor; verifies a unique Boat child by PID/birth/PPID/parent birth/four UIDs and system-parent executable; then checks all six SHA pins through `/proc/<child>/root`.
4. JPEG shots precede WMS diagnostics at t15/t30/t45 after the actual icon click. Every touch has a before image, exact Boat-PID/package/1920x1200 window and focused-window guard, identity guard, original input command, then an after image. The five commands are accelerate/left/accelerate/right/reset. `injection_rc=0` is transport evidence only. Human review compares scene movement, steering, LAP and HUD/colour with original images.
5. Finally saves raw hilog, process table, faultlog listing and a final JPEG even after interaction expiry. Cleanup has a separate 90-second transport budget and checks only boot/lock ownership. Keeper stop is cooperative and checks this directory's inode and owner; it never signals an app or a spawner. T4/root performs exact deployment rollback separately.

Local default preview (no device access):

```sh
python3 benchmark/2026-10-09-demo-boatattack/v2-20261013/interaction/interaction_runner.py \
  --plan benchmark/2026-10-09-demo-boatattack/v2-20261013/interaction/plan.disabled.json \
  --out /tmp/boat-unused-preview
```

After separate root authorization, using fresh paths and actual pinned files:

```sh
python3 benchmark/2026-10-09-demo-boatattack/v2-20261013/interaction/interaction_runner.py \
  --plan "$SIGNED_PLAN" --out "$FRESH_OUT" --execute \
  --authorization "$AUTH" --authorization-sha256 "$AUTH_SHA256"
```

`authorization.example.json` is deliberately unsigned and unusable. Exit 0 means `CAPTURED_PENDING_HUMAN`; every record has `accepted=false`. Any identity, pin or input-focus failure exits nonzero, retains evidence and requests only its own keeper stop. A changed boot/owner refuses further cleanup on the device.

The keeper donor changes display timeout/brightness and dismisses an actually fronted keyguard; it does not launch/refocus imehost or accept privacy. Desktop launch also searches the launcher and may dismiss the known USB-function dialog. These existing UI side effects require the separate spare-board authorization. No existing keeper/stop, RouteB parent, Toutiao data, privacy choice or runtime source is touched.

## Handoff and limits

Root explicitly assigned the minimal five-bind deployment and rollback to T4. Current acceptance waits for that package and a separately authorized spare-board window, initially 5ea; this entry is executable, not a claim that the overlay is already deployed. Original window9 apply/rollback is not called because it includes broad sandbox/install/keeper operations.

The 5ea baseline `errno 13` review is independent: root's `outer/ancestor-metadata-diff.json` shows ten `750 root:root` ancestors versus normal `755` on 5cd, with labels equal. App UID traversal through `/system/android` and `lib64` is denied. The repair and original smoke belong to root; no Boat byte is changed here.
