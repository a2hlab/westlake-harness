# 5cd on-board result — U13 autostart install + real reboot (2026-10-10)

Outer-approved board step (ACK(91) 05:30). Announce→LOCK→install→reboot→verify→disable/reboot→re-enable→UNLOCK, on
5cd (`5cd1e3dd…`). Board left **U13-prepared + autostart ENABLED**. Fingerprint/process counts below are read straight
off the board.

## Verdict

**The autostart MECHANISM is proven end-to-end and autonomous** (replay 56 + boat overlay + preserve the ondemand
appspawn-x listener + ready, with a working disable/enable kill switch). **Apps do NOT render** after a bare-reboot
autostart — a route-a *runtime-completeness* gap, not an autostart-mechanism bug (root cause below). This needs an
outer decision before the demo can self-boot to lit apps.

## What passed (autonomous, no Mac interaction post-reboot)

| Check | Result |
|---|---|
| Install (snapshot 56 live targets + SHA-verify, stage 5 boat, emit tsv, place cfg/scripts, supersede stale pr03) | `INSTALL_OK`, **56/56** layers SHA-verified |
| Superseded conflicting owner | `00_pr03_runtime_recovery.cfg` + `pr03-runtime-recover.sh` backed up + removed (orphaned; data root gone) |
| cfg SELinux label | `u:object_r:system_etc_file:s0` (proven donor label) |
| **Reboot → autonomous recover** | `state=READY`, `layers=56`, replayed 56/56 (recover-latest.log) |
| ondemand appspawn-x listener preserved | `/dev/unix/socket/AppSpawnX` present, flags `00010000`, identity `660:0:6005:…appspawn_socket` |
| boat overlay applied by chained service | adapter `8ab85446` ✓, jar `6333bcab` ✓, 3 private ✓, **no app launched** |
| ready param | `sys.westlake.demo.u13.ready=true` |
| **319 fingerprint** | **315/319 exact, 0 absent**; 2 = intended boat overlay (adapter+jar); 2 = `libinstalls.z.so` host-lib gap (see root cause) |
| **Disable + reboot → bare /system** | recover log "DISABLED present -> no recovery", bind_count=0, no appspawn-x/adapter/jar, ready unset |
| **Re-enable + reboot → U13-prepared** | `state=READY`, overlay `8ab85446`/`6333bcab`, listener present, appspawn-x `2a87118e` |
| Fail-closed (first boot, pre-fix) | `state=FAILED APPSPAWN_NOT_UP` → safe bare-ish state, no permissive, recoverable |

## What did NOT pass: apps do not render (HelloWorld/ZigZag white, BoatAttack not installed)

`aa start` returns "start ability successfully" but the screen is white and **no `appspawn-x` daemon spawns**
(`evidence/5cd-autostart/as-helloworld.jpeg`, `as-zigzag.jpeg`). BoatAttack is not even bm-registered after reboot
(`bm dump -n com.Unity3d.BoatAttackDay` errors) — its app dir + private libs exist but the bundle install is gone.

### Root cause (on-board, evidenced — not a static guess)

The 56-layer baseline replay restores the route-a **files** but cannot make the already-running OH services route-a
aware:

- `foundation` (pid 922) maps **stock `libbms.z.so` and 0 route-a libs** (`liboh_adapter_bridge`/`libandroid`/
  `oh-adapter-runtime` count = 0 in `/proc/922/maps`).
- live `/system/lib64/libinstalls.z.so` = **stock `2c9a5294`**, not the route-a `51e1b525` the 319-set expects (this is
  the bms installer that marks apps "anco"/route-a). Two of the 4 fingerprint "mismatches" are exactly this host lib.
- route-a AMS params are already correct (`persist.sys.abilityms.support_anco_app=true`, `prefork=false`, mali 0666) —
  so params are **not** the gap.
- `begetctl` here lacks nothing (`start_service`/`service_control` exist), but appspawn-x is ondemand and AMS never
  connects to its socket because stock bms/foundation don't treat these apps as anco.

So: the route-a **host libs** (`libbms`/`libinstalls`/`libappms`/`libappspawn_client`/`libwestlake_hap_domain_wrapper`)
are **not in the 56 baseline rows**, and even if bound they'd need to be in place **before `foundation` starts** (our
hook runs at `boot.completed`, after foundation is already up with stock libs). The Mac-driven `deploy_generation`
establishes route-a by overlaying host libs with/before a foundation (re)start — which an at-`boot.completed` hook cannot.
Route-2d lit apps earlier **only because 5cd was already in a Mac-deployed route-a state** (appspawn-x running,
foundation route-a-aware); it inherited the runtime, it did not establish it from a bare boot.

### Recommendation (for the outer)

The autostart payload is correct for "restore runtime files + overlay + ondemand listener autonomously". To reach
lit apps from a bare reboot, the route-a host-lib integration must happen before/with foundation start. Options:
1. Add the route-a host libs to the recovery set **and** restart `foundation` after the replay (heavier; the plan
   flagged broad changes as non-portable — needs approval).
2. Move the hook earlier than `boot.completed` (a boot-stage that precedes foundation), binding host libs first.
3. Bake the route-a host libs persistently into `/system` so foundation loads them at boot with no hook.
4. Keep Mac-driven `deploy_generation` for the demo bring-up; use this autostart only for the file/overlay layer.

## Safety / discipline

No `setenforce` (sealed enforcement preserved throughout; `/` remounted rw only for placement, re-sealed ro). Only the
whitelisted serial `5cd1e3dd…` was touched. Superseded pr03 cfg/script backed up (`/data/westlake-demo/u13/backup/`,
rollback restores). Board came back from every reboot on its own (no USB re-plug needed this run). Not pushed.
