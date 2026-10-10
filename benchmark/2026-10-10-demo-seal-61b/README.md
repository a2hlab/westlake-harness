# 61b v2 seal orchestration (offline delivery)

## Evidence and correction

The previous installer archived targets while recovery binds were live. Its directory removal could destroy uncovered physical `/system/android` files even when a bound entry reported `Resource busy`. A successful reboot command, running process or completed simulator is also not a sealed demonstration verdict.

This delivery adds `scripts/lab/demo_seal_61b.sh` and its Python workflow. **21 offline known-answer tests pass** (`evidence/tests.txt`), including transport order and pre-dispatch binding refusals; shell syntax and the default preview pass. No HDC, board, VM, SSH, lock or deployment was accessed during development. The checked-in plan is disabled and has explicit unresolved bindings. No real `seal.json` or live success is claimed.

The independent installer guard reads both `/proc/self/mountinfo` and `/proc/1/mountinfo`, twice before installer dispatch. A mount at or below any of the 56 recovery targets refuses installation, regardless of its displayed source name. Empty/malformed mountinfo is not a clean result. Component boundaries and kernel octal escapes are handled. The staged installer SHA must equal the reviewed source SHA; a separate pinned outer approval must confirm its own live-bind guard and bare-boot admission. This latter guard is necessary to close the check/install race.

## Commands

Preview, including pending provider names and every step's criterion:

```sh
bash scripts/lab/demo_seal_61b.sh
bash scripts/lab/demo_seal_61b.sh --plan "$REVIEWED_PLAN" --dry-run --out "$FUTURE_OUTPUT"
python3 -m unittest discover -s benchmark/2026-10-10-demo-seal-61b -p 'test_*.py' -v
```

The preview creates no output directory, invokes no subprocess and takes no lock. It expands neither tool nor input references for dispatch. Running it is not permission to execute the plan.

Future outer execution, **only after the pending bindings below have been reviewed and supplied**:

```sh
export WORKSPACES="$HOME/orca/workspaces"
bash scripts/lab/demo_seal_61b.sh --serial 61b --execute \
  --plan "$REVIEWED_PLAN" --authorization "$OUTER_AUTHORIZATION_JSON" --out "$FRESH_OUTPUT"
```

The authorization contains `serial`, exact `plan_sha256`, `approved_by: "outer(claude)"`, nonempty `approved_at`, and `execution_authorized: true`. The reviewed plan must have `execution_enabled: true`, `pending: []`, the current `driver_sha256`, a runner window authorization reference and bounded timeouts. File pins are verified before any transport or output creation. Default output is deliberately an unusable placeholder; an actual execution requires a fresh directory. No automatic retries of writes, automatic recovery, permissive SELinux or bypass flag is offered.

## Fixed order and criteria

1. Fresh lock-conflict check, canonical initial boot UUID, exact Enforcing, all **319** signed 61b path SHAs; same boot throughout this read-only preflight.
2. Write and read back U13 `DISABLED`; `hdc -t <61b> target boot`; bounded readiness wait and a changed UUID. Confirm DISABLED survived.
3. Check shell and init mount views, check staged installer SHA, repeat the mount checks immediately before installation. Run the approved installer with `WITH_BOAT=1`, `ALLOW_REMOUNT=1`, exact `DEPLOY`; require exit0 and `INSTALL_OK`.
4. Install/enable the additive Toutiao boot slot **after** the base installer (the base supersede step otherwise removes it). Its receipt must identify the bare boot. Clear U13 DISABLED and read back absence.
5. Complete read-only pre snapshot using `snapshot-plan.json`: all 56 recovery targets plus sandbox JSONs and both durable overlay roots. Run the fresh policy/recipe gate. Prepare the simulator's eight pinned inputs and retain its prediction table.
6. Record the bare boot again, issue `target boot`, wait for another changed ready UUID. No Mac deployment, label repair, ticket replay, bundle repave or provisioning is permitted during autonomous acceptance.
7. Check Enforcing and dmesg. Require fresh outer-signed evidence for HW/ZZ t20, Boat five-touch LAP and Toutiao **foreground desktop click + refresh + article**. Never replace the latter with background `aa start`. After foreground taps, independently read back exactly one root AppSpawnX parent with PPID1, socket `660:0:6005:u:object_r:appspawn_socket:s0`, and no `invalid:appspawn-x`.
8. Complete the post snapshot on the same boot and produce the raw snapshot diff. Prepare and execute `run_post_reboot.py --serial <61b>` for all128, without reinstalling. Run `regress_vs_signoff.py` against the explicitly bound **5cd** signed reference; exact128 key membership, no missing captures and a fresh outer no-regression decision are required.
9. Verify the boot has not changed. Collect a complete live-readonly seal snapshot for that same61b boot and call `build_seal.py` with admitted **v2** Boat + Route B overlay inputs.

Any failed command/predicate stops later steps, preserves raw stdout/stderr, exit codes and their hashes, and prints recovery references. Only boot readiness has a bounded read-only retry. Simulator rc1 is a deliberately **advisory** FAIL/UNKNOWN table, recorded verbatim and never labelled safety PASS; rc2/missing prediction stops before the second reboot. This exception does not relax other gates or the outer window authorization.

## Provider interface and remaining bindings

The six provider entries are explicit, pinned command arrays, not invented CLIs or silently successful placeholders. Their scripts and referenced inputs go in `pins`; argv must contain at least one pinned program path. Each receives `DEMO_SEAL_OUT`, `DEMO_SEAL_SERIAL`, `DEMO_SEAL_BOOT_ID`, `DEMO_SEAL_PLAN_SHA`, `DEMO_SEAL_STEP`. It must write `$DEMO_SEAL_OUT/<step>.json`, identify the same serial/plan SHA and exit0. Raw command results are retained independently. The output root is fresh, preventing reuse of pre-existing receipts.

| Provider | Required output / owner responsibility |
|---|---|
| `lock_check` | `no_conflict: true`; outer/cx-t0 supplies the real held-state command and window/runner lock handoff. This tool neither takes nor steals a lock. |
| `toutiao_slot` | `enabled: true`, `boot_id` equal to bare boot; approved additive placement and activation, no application launch. |
| `reboot_inputs` | Receipt plus `reboot-inputs.json` for the landed simulator. It must use this pre snapshot, exact physical underlay/inventory, init ordering, closure and policy queries, not historical mounted-state guesses. |
| `acceptance` | Current autonomous `boot_id`, `approved_by`, `approved_at`, `no_mac_repair: true`, six `checks` from the workflow and nonempty pinned screenshot/raw `evidence`. Human taps and screenshot interpretation belong to outer; rc0 alone is insufficient. |
| `regression_review` | Same signed receipt envelope, checks `all_128_observed`, `no_regression_vs_5cd`, `identity_unchanged`; exact fresh `comparison_sha256`, `baseline_serial` equal to5cd, and pinned evidence. Comparator image triage is not an outer verdict. |
| `seal_snapshot` | Current `boot_id` receipt plus `seal-snapshot.json` in `demo-seal-snapshot/v1` format. Complete package/version/APK SHA inventory and effective runtime/boot/overlay file groups are required by the landed compiler. A board-state snapshot alone is not this package inventory. |

Three especially important execution blockers remain **explicit, not worked around**:

- cc-t3 reported the live-bind/READY guard in lane commit `c9bea54a80` at14:42. It is not automatically a reviewed bare-boot installer binding. The published donor's running recovered AppSpawnX prerequisite conflicts with bare-boot admission. Bind the final source/hash and `guard_approval` (`live_bind_fail_closed`, `bare_boot_supported`, `installer_sha256`, outer approver); do not substitute an old installer or add a Mac replay between the bare-boot check and ARCHIVE.
- The landed `run_post_reboot.py` calls `round_identity.py`, which asserts original U13's319 hashes. Boat's shared replacements change that effective inventory. Execution requires an outer-signed `regression_admission` (`overlay_aware: true`, exact `post_reboot_sha256`, `overlays_sha256`) for a reviewed v2-aware runner/hook. This delivery **does not modify or weaken that identity gate**.
- Today's healthy5cd128 comparison/signoff, Toutiao additive installer, final v2 overlay admission, physical simulator inputs, actual acceptance receipts and final seal inventory must be supplied. The initial signed319 baseline and pre-existing tools are pinned in the template only as read-only source references; they are not a claim that pending candidates are ready.

## Failure disposition

Leave the board and lock disposition intact; print the failed step and the recovery references. Recovery is separately authorized: cx-t0 obtains a **fresh61b native ticket**, or outer approves physical bundle repave on a disabled bare boot. The documented5cd ticket directory is recipe provenance only, never a reusable61b ticket. The61b armed bundle's `native/payload/android` is the full repave source, not merely its currently bound subset. No recovery command is dispatched automatically, and no seal is emitted after an unreviewed/failed step.

`plan-template.json` and `snapshot-plan.json` are offline templates, not an approval or board transaction. The transport fixtures prove workflow order and failure handling only, not reboot durability, SELinux permission, Boat playability or the128 UI regression.
