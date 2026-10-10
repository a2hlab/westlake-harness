# Route B Toutiao boot slot — inactive, offline only

## Correction and boundary

A persistent `/data` runtime is not a persistent Route B process or private mount namespace. Reboot drops its spawner, child, socket and namespace bindings; the original launcher must recreate them. Conversely, booting a second global appspawn-x or activating the legacy `wl_toutiao.cfg.disabled` would conflict with U13. This payload does neither.

**No boot-slot board action occurred.** The cfg remains `.disabled`, the prepared placement manifest has `execution_enabled=false`, and the archived acceptance plan remains disabled. This is not a boot or screenshot PASS. The separate authorized 61b recovery is reported in `../2026-10-10-61b-u13-restore/`; its daemon gate remains blocked. A working U13 base is a prerequisite, not a problem this slot silently fixes.

## Donor provenance and inventory

Use `inventory.json` for every full SHA, durable board path and restart action. The four local originals were independently hashed:

| Input | SHA prefix | Persistence / boot action |
|---|---|---|
| source-host.hap | df385638 | Install `org.westlake.imehost` once; BMS HAP and sandbox persist. No boot-time install. Require donor UID20010053. |
| tt-rt.tar | 014c566e | Extract to the exact imehost `files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d` directory. ART/runtime/spawner files persist; private binds and processes do not. |
| tt-stage.tar | 6b4c9528 | Extract to `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`; `source_app_namespace`, `host_spawn` and `request.bin` persist. |
| tt-wd.tar | 16a72b27 | Original `operator45/selfheal48` scripts and screen-gate persist; stale PID/birth and supervisor lock require the donor's existing checks. |

Master provenance: `b7574c5e02` (route choice), **`0cd47f8b6b`** (three real desktop cold starts and recovery), **`54dcb31125`** (renamed Route B spawner coexists with U13). Exact existing recipes: `benchmark/2026-10-09-demo-toutiao/spare-5cd/provision_toutiao.SAFE.sh`, `rollback_toutiao.sh`, `demo-path.md`, and archive member scripts. The old provisioning script intentionally refuses the demo61b serial; it is a donor recipe, **not an executable61b command**. Reusing its one-time placement requires a separately approved installer window. AOT files are optional historical inputs and are not introduced here.

`donor/` preserves the original script text. `run-spawner-rename.patch` is the already-proved change: copy the same `appspawn-x` bytes to `asx-spawner` inside the private runtime before exec. `watchdog-owner.patch` retains the donor state machine, profile preservation, window-id refresh, JIT preparation, screen classifier and recovery timing, changing only process discovery/signaling to the required exact ownership guard. No new renderer, ART, supervisor protocol or shared U13 payload is invented.

## Prepared boot flow

1. Existing U13 recovery finishes and publishes `sys.westlake.demo.u13.ready=true`. The slot refuses if its own DISABLED, U13 DISABLED, wrong-boot receipt, input SHA, exact host UID or private sandbox ownership gate fails.
2. Wait for the **real foreground desktop click** to create `imehost0`. Do not use background `aa start`; donor experiments returned10107101. No spawner is eagerly launched during boot.
3. Start the proven watchdog and keeper. Its `start-parent.sh` reads the current WMS window id and updates `WL_PARENT_ID`, invokes the staged `source_app_namespace` with UID20010053, then runs the renamed spawner inside its private root. `spawn.sh` uses its distinct A2HSource socket, never AppSpawnX.
4. Existing watchdog recovery is retained. Every signal candidate now needs PID/birth, all four UID fields, exact executable path **and full SHA**, and the private-root `run.sh` inode matching the exact physical sandbox. U13's root-owned `/system/bin/appspawn-x` fails the guard. The keeper/guardian use recorded PID/birth and an exact NUL-delimited script argument, not a process-name lookup.
5. Same-boot re-entry refuses (`SAME_BOOT_ALREADY_ATTEMPTED`), rather than silently treating a failed WAITING attempt as ARMED or launching a second guardian.

`ARMED` reports startup state only. Screenshots decide lighting.

## Interface with cc-wiki installer

Read-only source: `$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-10-u13-autostart/payload-61b/init/00_westlake_u13_recover.cfg`, checked at commit34509981a7. The reserved interface is exactly `ready=true` → `westlake-u13-toutiao-overlay`, once service, `/system/bin/sh /system/etc/westlake-u13-toutiao-overlay.sh`, root/root-system, sandbox0, su-domain. This payload declares that service in a **separate inactive cfg**. The legacy `wl_toutiao.cfg.disabled` stays untouched.

The existing installer supersedes any other cfg containing `westlake-u13`. Therefore **stage this additive slot only after the base installer**, and re-stage it after an explicitly approved base reinstall; do not modify cc-wiki's tree. The additional KILL capability is limited to the guarded donor cleanup. SELinux/capability admission is **unverified** until the approved board experiment; do not use setenforce or a different launcher to bypass refusal.

The worker's `/data/westlake-demo/toutiao/immutable.tsv` binds staged archives, static scripts, donor classifier and original spawner. `run.sh` is a pinned rename template; its live `WL_PARENT_ID` is intentionally dynamic and must not be frozen to the prior boot's numeric id. The one-time provisioner places that template in the exact RT directory, and places the verbatim `start-parent.sh`, `spawn.sh`, classifier at their original F paths. New scripts stay in the dedicated Toutiao root.

## Local preparation and rollback

```sh
python3 benchmark/2026-10-10-toutiao-boot-slot/prepare_payload.py \
  --inputs "$HOME/a2hlab-provision/ttbundle" \
  --out benchmark/2026-10-10-toutiao-boot-slot/.artifacts/new-payload
python3 -m unittest discover -s benchmark/2026-10-10-toutiao-boot-slot -p test_slot.py -v
```

Preparation validates all four archive SHAs and emits `placement.json`, `immutable.tsv`, inactive cfg, donor classifier and scripts. It sends nothing to a board. The large archives remain in `$HOME/a2hlab-provision/ttbundle`; the generated payload is persisted in the lane worktree `.artifacts/payload-v2`. `evidence/prepare.txt` gives the placement hash. Copy the exact `immutable.tsv` to the ROOT path as a separate declared placement; cfg activation is not generated.

`rollback_toutiao_boot_slot.sh` first disables this slot and sets donor stop files, then TERM-signals only receipt-owned guardian/keeper and drains only exact Route B processes (TERM→bounded KILL, birth rechecked). It never kills by name, changes U13 or disables its init service. HAP/data are preserved. Configuration withdrawal in a separately approved remount window removes/restores **only** the two system placements listed in placement.json; it does not rename, delete or enable the legacy disabled cfg. A missing/foreign/PID-reused process gets no signal. Failure to drain leaves the slot disabled and reports failure.

## Disabled board acceptance plan

`acceptance-plan.json` is a future proposal, not an execution authorization. Under its own declared lock/window: verify U13 identity/parent and exact donor inputs → provision additive slot → real desktop click3 cold starts, refresh and open an article with snapshots → confirm U13 parent unchanged and controls → approved reboot/power-cycle, **no Mac replay/launch**, user desktop tap → same article/refresh snapshots. Match each Route B process by ownership, verify U13 and its319 files, and record per-input SHA and boot receipt. Any refusal or UI failure uses the exact owned slot rollback and preserves evidence/lock. No reboot or config edit is part of this offline task.

## Offline answers

Mac and a2hlab VM: **8 tests each, OK** (`evidence/tests-{mac,vm}.txt`). They include owned Route B positive, U13 root-parent negative, wrong UID/executable/SHA/root-inode/stale-birth negatives, exact supervisor argument, same-boot refusal, inactive interface and all shell syntax. These are mocked ownership and static interface checks, not device signal tests or boot acceptance.
