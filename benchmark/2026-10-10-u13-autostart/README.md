# U13 boot-autostart admission — OFFLINE payload (zero board)

**Lane cc-wiki · campaign #91 demo-baseline · 2026-10-10**

Goal (outer dispatch): make the demo board come up on its own after a real power-cycle — replay the pinned **56**
U13 baseline mounts, then let init start the existing `appspawn-x` via `begetctl`, **without launching any app**, and
fold the signed-off **BoatAttack** overlay into the same autostart. Acceptance is a reboot with **no Mac attached**:
read-only verify **319** fingerprint paths + `appspawn-x` up + tap HelloWorld / ZigZag / BoatAttack lights; plus a
disable+reboot that returns to **bare `/system`**.

This deliverable is the offline payload (artifacts + installer + disable + rollback + known-answer tests), plus the
**on-board install + real-reboot result on 5cd** (2026-10-10, outer-approved) — see **`RESULT-5cd.md`**.

**Board result in one line**: the autostart MECHANISM is **proven end-to-end and autonomous** (enable→reboot→U13-prepared,
disable→reboot→bare /system, re-enable→reboot→U13-prepared; 56/56 layers, 319 fingerprint 315 exact + 2 intended overlay
+ 2 host-lib), **but apps do not render** after a bare-reboot autostart — a route-a runtime-completeness gap (`foundation`
starts stock; the 56-layer replay excludes the route-a host libs and runs after foundation is up). Needs an outer
architecture decision; details + evidence in `RESULT-5cd.md` / `evidence/5cd-autostart/`.

## Evidence first

| Fact | Value | Source |
|---|---|---|
| Baseline mounts replayed | **56** (3 dir + 53 file; 51 shared + 5 zigzag-private) | `payload/u13-recover-table.json`, `journal_sha256 f2471873…` |
| Fingerprint paths verified on board | **319** | table `expected_paths` |
| `appspawn-x` identity gate | `2a87118e…` (UID0 / PPID1) | table `host_sha256` |
| BoatAttack shared overlay | adapter `8ab85446…` over base `84695d62…`; jar `6333bcab…` over base `bbc3f530…` | validated in `../2026-10-09-demo-boatattack/spare-5cd/RESULT-route2d.md` |
| BoatAttack private libs | `libunity 1bea0fae…`, `libil2cpp f6b806b5…`, `signal_box 7a931c79…` | same |
| Known-answer tests | **22 / 22 PASS** (offline) | `tests/ka_tests.py` |
| Board touches this phase | **0** | — |

## What was wrong before (why this shape)

- **DIGEST E.7 / #63 / #71**: results that look alive aren't. A boot service that “starts” is not an autostart —
  only a screenshot after a real reboot is. So the acceptance here is explicitly a **no-Mac reboot + read-only
  fingerprint + tap-to-light**, not “the service ran”.
- **The table's `source` fields are ephemeral.** They point at `/data/local/tmp/…-generation-…/…` host dirs that
  vanish on reboot. A naïve boot replay that reads them would fail on exactly the reboot it exists for. Fix: the
  installer **snapshots the 56 live target bytes into a reboot-persistent archive** (`/data/westlake-demo/u13/
  sources`, SHA-verified) and the boot worker replays from there.
- **Donor autostart uses `setenforce 0`.** Copying the donor shape verbatim would silently drop the board to
  permissive. We keep sealed enforcement and **fail-closed** instead (see deltas).

## Rules this establishes

1. **Autostart replays from durable, SHA-pinned bytes — never from generation host paths.** The pinned table is
   immutable; per-boot receipts are separate.
2. **Sealed enforcement is non-negotiable.** No `setenforce` in any script or cfg; if a step can't run sealed, the
   worker FAILS and stops for outer review rather than making the board permissive.
3. **Runtime-up ≠ app-up.** The autostart prepares the runtime (`appspawn-x` via `begetctl`) and **stops there**;
   the demo stays tap-to-start (`activity_start=DEFERRED_TO_USER`). No `am/aa start`, no launcher, no watchdog.
4. **Every reversible step is pre-built**: a `DISABLED` toggle (reboot → bare `/system`, machinery re-armable) and a
   full rollback (restore backed-up init files, remove durable root).

## Layout

```
payload/
  init/00_westlake_u13_recover.cfg      2 jobs + 2 once-services (condition-started); minimal caps; secon u:r:su:s0; NO setenforce
  scripts/
    westlake-u13-recover.sh             boot worker: DISABLED gate → replay 56 (WAL + SHA) → begetctl start appspawn-x → verify UID0/PPID1/SHA → set sys.westlake.demo.u13.ready
    westlake-u13-boat-overlay.sh        on ready: bind C8 adapter + C9 jar (base-gated) + 3 private into BoatAttack; NO launch
    install-westlake-u13-autostart.sh   on-board installer: snapshot 56 live targets → durable archive, stage boat artifacts (SHA-gated), emit .tsv, place cfg/scripts (backup first), lock down; NO reboot
    westlake-u13-autostart-disable.sh   reversible toggle: DISABLED marker (disable|--enable|status)
    rollback-westlake-u13-autostart.sh  restore init files from backup + remove durable root → bare /system
  u13-recover-table.json                the pinned 56-layer manifest + boat overlay rows + 319 expected_paths
tests/ka_tests.py                       22 offline known-answer tests (shape + safety negatives + SHA cross-consistency)
results.json                            machine-readable summary (counts, SHAs, acceptance)
documentation.json                      file-by-file index
landing-paths.txt                       on-board destinations for every artifact
```

## How it runs (boot sequence)

```
init parses 00_westlake_u13_recover.cfg
  └ bootevent.boot.completed=true ─ start westlake-u13-recover
        replay 56 baseline binds (seq, WAL, SHA)  →  begetctl start_service appspawn-x
        verify pid UID0 / PPID1 / appspawn-x SHA 2a87118e  →  param set sys.westlake.demo.u13.ready true
  └ sys.westlake.demo.u13.ready=true ─ start westlake-u13-boat-overlay
        bind adapter 8ab85446 (base 84695d62) + jar 6333bcab (base bbc3f530) + 3 BoatAttack private libs
        (NO app launched — tap to start)
```

## Safety deltas vs the donor autostart

- **NO `setenforce 0`** — sealed SELinux enforcement preserved; fail-closed if a step can't run sealed.
- `appspawn-x` started **only** via `begetctl start_service appspawn-x` (never exec'd directly).
- **No app / ability / launcher / watchdog launch** (`activity_start=DEFERRED_TO_USER`).
- Caps minimal: `DAC_OVERRIDE/CHOWN/FOWNER/SYS_ADMIN` (no `SYS_PTRACE/SETPCAP`).
- No PR03 relabel / runtime-param change / mali chmod / boot.art link.

## Reproduce the offline checks

```sh
cd benchmark/2026-10-10-u13-autostart
python3 -m unittest -v tests.ka_tests      # 22/22, zero board
for f in payload/scripts/*.sh; do sh -n "$f"; done   # POSIX syntax (on-device /system/bin/sh)
```

## Admission mechanics (from the validated donor)

The donor `bms/src/tools/devices/install-boat-attack-autostart.sh` proves the on-board placement on these exact
boards, so the installer now uses it rather than guessing:

- **Persistence**: cfg → `/system/etc/init/00_westlake_u13_recover.cfg`, scripts → `/system/etc/`, after a root `/`
  **rw remount** (verified via `/proc/mounts`) that is **re-sealed `ro`** on exit (trap). Gated by `ALLOW_REMOUNT=1`.
- **SELinux**: cfg + scripts get the proven label `chcon u:object_r:system_etc_file:s0`, `chmod 0550`, `chown 0:0`
  (so init can read+exec them at early boot).
- **Single owner**: the installer refuses to run beside a conflicting boot worker. It backs up then removes any other
  `/system/etc/init/*.cfg` that defines a recovery / `appspawn-x` owner (and the `/system/etc/*.sh` it references),
  gated by `SUPERSEDE=1`. 5cd carried a stale orphaned `00_pr03_runtime_recovery.cfg` (+ `pr03-runtime-recover.sh`,
  data root already gone) — superseded with backup so our cfg is the sole owner (rollback restores it).

Still board-confirmed, not guessed: that the sealed caps/domain (`u:r:su:s0`, DAC_OVERRIDE/CHOWN/FOWNER/SYS_ADMIN)
actually let the mount worker run and `begetctl start_service appspawn-x` succeed. If not, the worker fails closed
(bare `/system`, recoverable) rather than making the board permissive.
