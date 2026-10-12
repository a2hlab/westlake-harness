# Boat v2 offline takeover — cx-bms, campaign 91

## Authority and evidence first

Canonical dispatch: **outer(codex), 2026-10-12 10:05:06 +08:00**, “cc quota
exhausted reassignment”, in `.octos/boards/app-lighting.md`. cc-t3 and cc-wiki
panes are closed. cx-t0 is the sole 61b operator continuing the existing v1
seal run; cx-bms takes only Boat v2 **offline preparation**.

**This turn: zero board/HDC/VM/SSH operations, zero builds, zero rehearsal,
zero test execution, no edits to other worktrees, no dispatch-tool replacement.**
All commands below are references or future commands, not execution receipts.
The following three conditions are cumulative and remain pending:

1. 61b **v1 seal completed and signed** (acceptance alone is insufficient).
2. An **idle-board full 128-key regression on the Boat candidate adapter/JAR**
   completed and outer-signed, not the existing v1 baseline regression.
3. Explicit **outer release of rehearsal 2**, with board, lane and time window.

No rehearsal 2, lock, reboot or board probe is authorized by this handoff.

## Reused package and resolved ownership

Source tree: `$WORKSPACES/westlake-harness-t3/benchmark/2026-10-11-boat-autostart-seal/`.
Source HEAD is `a8bb2dac4a612069695ee532f9e9d3fc2d4656cf`; the integration plan,
runner, installer and rollback bytes match that commit. The exact 25 local
reference files, sizes and SHA256 values are in `inventory.json`.

- `INTEGRATION-A-rehearsal2-plan.md`, SHA `660b6aa2…`, supersedes the old
  unresolved runtime/ownership options in `SPEC.md` and top-level `results.json`.
- `REHEARSAL-1-findings.md`, SHA `b0fd4fb2…`, records the failed first rehearsal,
  subsequent recovery report, and the fixes leading to ownership-(a).
- Ownership **(a)** is already decided, not a new open choice: install a new
  `westlake-u13-boat-overlay-v2.sh` and repoint the boat service within the
  backed-up `/system/etc/init/00_westlake_u13_recover.cfg`. Keep the existing
  recover worker and old boat worker on disk; do not run two competing overlays.
- The archived recover-v4 reference in t3's `2026-10-10-u13-autostart/payload/init/`
  and the boatv2 cfg have equal `jobs` and equal `westlake-u13-recover` service
  objects. Only the boat service script path is repointed. This proves the
  archived comparison, **not** equality with the board's current cfg.
- Runtime is **stock18763dd4**, **no Boat runtime bind**. Neither adc125f4 nor
 94718e0d belongs in this v2 overlay. The earlier runtime-port work is not the
  current Boat recipe.
- Boat toggle is `$ROOT/BOAT_DISABLED`; source archive is
  `$ROOT/sources-boat-v2`. `$ROOT/DISABLED` is the recover master switch and is
  forbidden to the Boat layer. Do not archive or replace the base 56 layers.

## Inputs: six existing files verified locally, no rebuild

| Input | Full SHA256 | Local check |
| --- | --- | --- |
| Adapter `payload/sources-boat/liboh_adapter_bridge.so` | `8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e` | Matches installer pin |
| Runtime JAR `payload/sources-boat/oh-adapter-runtime.jar` | `6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852` | Matches installer pin |
| Private `libunity.so` | `1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac` | Matches installer pin |
| Private `libil2cpp.so` | `f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746` | Matches installer pin |
| Private `libwestlake_bionic_signal_box.so` | `7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da` | Matches installer pin |
| APK `$WORKSPACES/../00.Workspace-games-ad1ab0a7/APKS/BoatAttack/dist/boat-attack-a.apk` | `8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444` | Matches runner pin |

The five overlay inputs are already staged in the t3 tree; leave them there
read-only. Large binaries are not copied into this handoff or committed anew.
`inventory.json` records durable local paths and hashes, not a new provenance
claim or fresh build receipt. Package is `com.Unity3d.BoatAttackDay`.

## Historical validation versus actual gaps

Window9's `5cd-window9-findings.md` reports stock-runtime Boat rendering at
t15/t30/t45 and interactive movement around t95, followed by cleanup. This
handoff pins that report but **does not rejudge screenshots or claim a new run**.
The canonical 2026-10-11 17:06:06 outer ACK accepted ownership-(a) and **18/18 KA**.
The current test file has 18 test methods; this turn did not rerun them. The
older `results.json` still says 15/15 in one field and retains obsolete choices;
use the integration plan and ACK, not those stale counters/options.

Rehearsal1 proved installer/init placement and boot service firing, **not**
render acceptance or successful automatic rollback. Its raw
`rehearsal/final-unified.json` has `adapter:null`, `jar:null` and
`unified_after_disable:false` (SHA `825d0aec…`). This is the failure caused by
the shared recover `DISABLED` marker. The findings and later board report say
manual recovery restored unified state; do not relabel this raw failed JSON as
a passing rollback receipt. Rehearsal2 must generate new strict restore proof.

| Gap | Existing evidence / consequence | Next action, only when dispatched |
| --- | --- | --- |
| Runner still owns the wrong lane/output | `rehearsal_runner.py:28` fixes `LANE='cc-t3'`; `:44` fixes `OUT=HERE/'rehearsal'`. Running it in t3 would write that tree and present the closed lane to lock checks. | Create an isolated **bms-owned** working copy, bind cx-bms, explicit authorized serial and fresh attempt output, before invoking any mode. No such runner copy is created/executed this turn. |
| Keeper missing at runner's expected location | `KEEPER=HERE/'onscreen_keeper.sh'` at `:33`, but that file is absent. Existing donor: t3 `2026-10-11-boat-window9/onscreen_keeper.sh`, SHA `a55ebc4c…`. | Reuse this donor in the future bms working copy; do not rebuild or touch t3. |
| Full 128 candidate regression not wired/signed | Runner `LIGHT` only contains HW/ZZ/Boat, not 128. Existing manifest, shot tiers and `t4/run_post_reboot.py` / `regress_vs_signoff.py` are available in master. | Outer must bind a complete 128 installed-key index, candidate child-view evidence, per-board smoke/base, fresh run and image signoff. Do not substitute the v1 20-key/Permissive-baseline128 result. |
| Live recover cfg reference may have advanced | The payload is based on the archived recover-v4 cfg; current board cfg/worker and boot state have not been read here. Installer only tests cfg existence. | In an authorized window, pin current cfg/worker; compare services/triggers and expected originals before backup/swap. Keep Route B wiring and the recover worker. Notify the new recover owner/cx-t0 and outer, not the closed cc-wiki pane. |
| Existing runner's verification is weaker than the intended verdict | `wait_top()` accepts any member of a broad window-name list; `light_capture()` records `app_window_top` without rejecting false. Private child hashes are recorded but not asserted; final unseal omits runtime from its failure assertion. | Before board execution, add/approve strict expected-app foreground and private/runtime/restore assertions in the bms copy. A screenshot of HW or lockscreen cannot be Boat PASS; “SEAL VERIFIED” is not image signoff. |
| Repeated installer / rollback evidence needs a fresh original | Installer copies an existing cfg into fixed `backup-boat/*.bak`; repeating after the swap can back up v2 rather than the original. Old raw rollback JSON is failed. | Bind original cfg hash and a single fresh backup per authorized attempt; verify restored cfg, stock runtime, base adapter/JAR, Boat binds absent and no deleted mounts. Never blindly repeat installer. |

## Existing next-step CLI, not executed

Offline known-answer command (future reuse; text/SHA tests, no build):

```sh
T3="$WORKSPACES/westlake-harness-t3/benchmark/2026-10-11-boat-autostart-seal"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$T3/tests" -p ka_boat_overlay.py -v
```

The existing runner supports exactly `preflight`, `seal`, `unseal`,
`--cfg-dir`, `--script-dir`. It has **no** `--lane`, `--serial`, `--out` or
`--dry-run`; do not invent those flags or run it in the read-only source tree.
On Mac it re-execs into `a2hlab`, so even `preflight` is live board access and
must not be invoked now.

After a separately approved offline runner-copy/wiring change **and all three
release conditions**, the available command shape is:

```sh
# BMS_RUN is the future reviewed bms-owned runner, NOT the t3 source path.
: "${BMS_RUN:?bind reviewed bms runner after outer release}"
PYTHONDONTWRITEBYTECODE=1 WORKSPACES="$WORKSPACES" python3 "$BMS_RUN" preflight
PYTHONDONTWRITEBYTECODE=1 WORKSPACES="$WORKSPACES" python3 "$BMS_RUN" seal \
  --cfg-dir /system/etc/init --script-dir /system/etc
# Reuse its rollback path on success/failure under the same authorized owner/window.
PYTHONDONTWRITEBYTECODE=1 WORKSPACES="$WORKSPACES" python3 "$BMS_RUN" unseal \
  --cfg-dir /system/etc/init --script-dir /system/etc
```

Before any write: announcement -> LOCK the designated **idle** board -> fresh
read-only preflight. The original reference target is5cd, not an authorization
for5cd or61b. No lock operation is performed by these printed commands here.
Require the appropriate held lane externally; the original runner is not the
window/lock allocator. Capture stdout+stderr to a fresh persistent tee receipt.

Intended authorized sequence: original-cfg backup -> install Boat APK/sandbox
once -> stage pinned5 files -> swap boat service reference -> reboot -> stock
runtime plus candidate5 child hashes -> HW/ZZ/Boat true foreground screenshots
and interaction -> `BOAT_DISABLED` + reboot -> restored unified -> restore
original cfg/uninstall Boat -> strict post-rollback proof -> UNLOCK.

**Do not execute these commands now.** No signed candidate128 run, completed
v1 seal or rehearsal2 release has been supplied to this lane. The immediate
deliverable is this offline summary; missing wiring/admissions remain explicit.

## Dispatch-tool hold

The pending lane_send receipt patch remains only in the bms worktree.
Active master `lane_send.sh` SHA is still `af48a198…`; no replacement, test
dispatch or agent input occurred. Leave it pending until the outer separately
approves landing after sealing. `landing-paths.txt` lists only this handoff.
