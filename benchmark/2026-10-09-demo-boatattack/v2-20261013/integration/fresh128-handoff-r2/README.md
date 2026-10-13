# Fresh 128: complete Mac driver with Orb identity transport

The earlier handoff described manual window dispatch. That is not the complete
driver acceptance path. This independent revision supersedes that execution
guidance: prepare once, then execute/detach the entire original candidate driver.
The previous handoff and all candidate/runtime freezes remain unchanged.

The Mac controller must retain its real home directory for the existing lock
command. The candidate hook's Reader needs Linux. Only identity Python dispatch
uses `orb -m a2hlab env WORKSPACES=... MAC_HOME=... python3`; board_run remains a
Mac child. Normal HDC calls use outer's existing native Mac shim. No runtime,
proof, identity guard, board_run, adapter, or acceptance rule is modified.

## Exact delta and offline evidence

`delta.patch` is against BMS `identity-r4/run_candidate_post_reboot.py`, SHA
`4d8f3f6443828db2cc8fb044291bdecaa5bea3c4e9b5d37cdf10f44f9a272a60`.
The new driver imports that directory's original candidate hook. The changes are:

1. Explicit source directory for the unchanged BMS hook.
2. One identity transport prefix, used pre-lock and in both plan hooks (including
   the existing optional Toutiao branch).
3. The existing native Mac HDC shim, added to bindings and selected in PATH.

`test-output.txt`: **14/14 PASS**, using the actual full128 manifest, install
receipts, tiers and corrected candidate proof. Every subprocess is intercepted.
The positive test invokes real `execute`, `resolve_inputs` dispatch and `collect`
over eight simulated board_run windows, with 128 synthetic records and pending UI
verdict. It does not claim actual images, execution or Linux transport success.
Negatives cover pre-lock failure, resolution failure, missing records, smoke and
final identity failure, binding/plan drift, 127 membership, empty authorization,
unbound Boat and forbidden 5ea Toutiao. Main PATH dispatch is tested. AST checks
confirm unchanged `resolve_inputs`, `collect`, serial and special-slot validators.

T0 narrow review entry: read `delta.patch`, compare `source-pins.json`, then run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$HANDOFF/test_transport.py"
```

## Prepare offline on Mac

`WORKSPACES` must be set to the actual shared workspace root. After landing, use
the main-tree handoff below; before landing, use the same relative path in t4.
Keep the BMS original identity-r4 source closure available at its pinned paths.
Use a **new** output directory. This command only prepares disabled plans.

```sh
export PYTHONDONTWRITEBYTECODE=1
MAIN="$WORKSPACES/westlake-harness"
V2="$MAIN/benchmark/2026-10-09-demo-boatattack/v2-20261013"
HANDOFF="$V2/integration/fresh128-handoff-r2"
PROOF_DIR="$V2/outer/identity-table-correction/compiled"
OUT="$V2/outer/fresh128-r4-driver-r2"
python3 "$HANDOFF/run_candidate_post_reboot.py" \
  --out "$OUT" \
  --serial 5ea34a4500000000000000001123012c \
  --manifest "$MAIN/benchmark/2026-10-09-demo-baseline/demo-manifest.json" \
  --tiers "$MAIN/benchmark/2026-10-09-demo-baseline/t4/shot-tiers.json" \
  --install-index "$MAIN/benchmark/2026-10-09-demo-baseline/t3/install-index-final.json" \
  --smoke "$PROOF_DIR/smoke.json" \
  --boot-before d0e1f5eb-ac35-4c39-9e1a-7c40d9251220 \
  --candidate-proof "$PROOF_DIR/candidate-proof.json" \
  --candidate-proof-sha256 d8f13bf33e431bc8821e4e29c573161c41d1527e276828b8e725efad3e959b22
```

`source-pins.json` names all source bindings. `full128-members.json` and
`full128.keys` enumerate the full membership: eight windows, 18 keys each except
the final two; 121 t10 and 7 t20. Boat remains a separate special slot. The proof
retains all original319 objects (315 unchanged, four explicit replacements),
18 additional objects and serial-specific RouteB absence. No old result fills
this fresh round's denominator. Fresh round does not request another reboot.

## Outer-only execution after ten controls pass and review/authorization

Do not run this command while the ten-control task holds the board. Outer must
fill the copied `authorization.template.json` with actual approval, ten-control
evidence, round SHA, disabled plan pins, generation and window limits. The
original CLI checks only a nonempty authorization **reference**, not a signature,
expiry or this JSON's fields. This template is not authorization.

After review, set `AUTH_REF` to outer's actual approval reference and run the
whole driver on Mac:

```sh
: "${AUTH_REF:?set actual outer authorization reference}"
PATH="$V2/outer/smoke10-r4b/mac-tools:$PATH" \
  python3 "$HANDOFF/run_candidate_post_reboot.py" \
  --out "$OUT" --serial 5ea34a4500000000000000001123012c \
  --execute --detach --authorization "$AUTH_REF"
```

The child log is `round.log`. All bindings and window pins are checked before
input resolution; input resolution precedes the first lock. Each window gets an
Orb pre-lock identity check, then the unchanged Mac `demo_board_run.py` with Orb
after_lock/before_unlock hooks. The driver enables plans itself and waits for
each board_run to finish. Do not manually enable plans or dispatch eight windows.
It stops on missing records or failed window smoke/final identity, and runs
collect automatically. Do not call collect again on an existing `final/`.
`round-complete.json` remains `UI_verdict=pending_outer_review`.

Both special slots stay disabled. Enabling Boat requires the original separately
approved, SHA-bound plan and bounded window; enabling Toutiao on 5ea is refused.
Specials never substitute for any of the ordinary128 keys.

Each window retains the original 45-minute maximum and 35-minute new-test cutoff.
The cutoff is passed to the adapter; the driver has no extra 45-minute kill timer.
Outer monitors elapsed time, screenshots and existing finally/unlock behavior.
Confirmed visual regression means stop further dispatch and preserve partial
records, then follow the existing reviewed cleanup/rollback procedure. Do not
kill a device system parent or bypass a retained lock. Script success is not a
visual verdict. No old128 or ten-control result is counted as this round's result.

After full driver completion, the unchanged comparator can prepare outer review:

```sh
python3 "$MAIN/benchmark/2026-10-09-demo-baseline/t4/regress_vs_signoff.py" \
  "$OUT/final" \
  --signoff "$MAIN/benchmark/2026-10-09-demo-baseline/t3-outer-signoff.json" \
  --baseline-t3 "$MAIN/benchmark/2026-10-09-demo-baseline/t3" \
  --out "$OUT/comparison" --sheet
```

Use actual `facts.txt` and outer image verdicts. This delivery performs no device,
VM, SSH or remote operation and grants no execution approval.

## W3 archive

The unchanged earlier handoff's `archive-status-addendum.json` binds outer's
REMOTE_VERIFIED W3 receipt: 10,134,869 bytes, SHA
`fcbfc14ec090095544b10b929e92e6c2a9f04dba6f56e0e24fc420e00c21027c`.
This revision neither contacts the remote nor rewrites the old closure freeze.
