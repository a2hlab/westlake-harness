# base-61b — 61b board base preparation for the blocker-triage resweep (entry #9, lane oc-t0)

Date: 2026-09-28. Board: `61b0657200000000000000000324012c` (exclusive, locked for the task).
Worktree: `~/orca/workspaces/westlake-harness-t0b`, branch `feat/app-lighting-t0-base61b`.
Deliverable: `base-61b.json` (structured record) + `evidence/` (originals fetched before each disable).

## What was wrong / why this task existed

The 2026-09-28 resweep (T0 main line, now cx-t0) needs 61b as a second shard board on a base
that is **content-identical** to 5ea's `framework-2` base. But 61b still carried the
persistent-demo + toutiao-ops residents from campaign F:

- an **autostart cfg** (`/system/etc/init/wl_toutiao.cfg`) that re-launched the toutiao
  boot supervisor (`boot_toutiao.sh` → selfheal watchdog + onscreen keeper) on every boot;
- a live **onscreen keeper** (pid 3226) re-asserting screen timeout/brightness and
  dismissing the keyguard every 5 s;
- the persistent-demo **open_broker** script (found at `/data/local/tmp/persist-demo/`,
  not running at task time).

Any of these would fight a per-app sweep (auto-fronting windows, unexpected relaunches,
stolen focus), so they all had to be disabled — recording originals first.

## What was done (all evidence under `evidence/`)

1. **Autostart + residents disabled** ( originals: `wl_toutiao.cfg.orig`,
   `boot_toutiao.sh.orig`, `onscreen_keeper.sh.orig`, `open_broker.sh.orig` ):
   - `wl_toutiao.cfg` → renamed `wl_toutiao.cfg.disabled` on `/system`
     (rw remount → mv → ro remount, verified by ls).
   - `boot_toutiao.sh` → early-exit guard on line 2 (`[ -f boot.disabled ] && exit 0`)
     + `boot.disabled` marker touched. Defensive depth: even if the cfg returns, the
     script exits before launching anything.
   - `onscreen_keeper.sh` → pid 3226 killed + `keeper.stop` touched (the script honors
     the stop file). ps afterwards shows no keeper/watchdog/boot_toutiao/open_broker
     processes (kernel `watchdogd`/`watchdog_feeder` and `watchdog_service` are
     unrelated OH system processes).
   - `open_broker.sh` → renamed `open_broker.sh.disabled` (was not running; `persist-demo/`
     dir retained).
   - selfheal watchdog: **already dead** before the task (stop file present, no process);
     its only launcher was `boot_toutiao.sh`, disabled above.
2. **Framework comparison — 61b framework-1 ≡ 5ea framework-2** (details:
   `evidence/fw-compare.json`, generated on the VM from the two `device-report.json`
   files):
   - 5ea `framework-2` (`a2hlab-framework-cab462ff…`, report `passed=true`)
     vs 61b `framework-1` (`a2hlab-framework-b806febc…`, report `passed=true`);
   - `files` maps: **306 vs 306 entries, 0 hash diffs, 0 path diffs → IDENTICAL**;
   - fresh files-map digest this method: `a6ad5939…` (the outer loop's earlier
     `b071cd7a…` used a different normalization — same conclusion);
   - **consequence: 61b needs NO restage**; cx-t0 can point the sweep at the 61b
     `framework-1` device-report as-is.
3. **Deploy inventory recorded**: framework stage dir
   `/data/local/tmp/a2hlab-framework-b806febc…` (66 top-level entries, full sha256 list in
   `evidence/framework-files.sha256`); host `entry.hap` sha256 `df385638…`
   (`evidence/entry-hap.sha256`); 21 historical `a2hlab-framework-*` dirs retained;
   `/data` has **177 G free** (24 % used, `evidence/df-data.txt`).
4. **c91d26bf dirs preserved**: `/data/local/tmp/a2hlab-app-c91d26bf…` present, toutiao
   runtime source dir under the imehost bundle data intact (watchdog.sh references it).
5. **LIT control NOT run** — per entry #9 that is cx-t0's job with the fixed collection
   script.

## Rules this run set

- Disabling a boot service on these boards = **two layers**: rename the init cfg on
  `/system` AND leave an in-script early-exit marker, so neither a cfg restore nor a
  manual launch resurrects the residents accidentally.
- Framework "same base" claims must come from the device-report `files` map
  (306 path→sha256 entries), not from stage-dir names (they differ: cab462ff vs b806febc).

## R2 honesty grading

| Claim | Grade |
|---|---|
| autostart + residents disabled (no processes, cfg renamed, guards in place) | verified |
| 61b framework-1 ≡ 5ea framework-2 (306/306, zero diff) | verified |
| disable survives a reboot | partially (guards verified in-file; no reboot test — would churn the experiment boards) |
| boot image hash | unverified (partition not readable via shell path) |
