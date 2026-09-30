# Replay the unified J2 + J3 state after reconnection

Reboot removes temporary JAR bind mounts. A package ledger alone cannot prove that the daemon sees the same runtime as the shell. This delivery verifies the **N2 51a78bde live identity + FZ-001 installer in both views**, then replays the **J2 0715c964 → J3 75c2068c** layers. **17 offline tests and 19 existing shard tests pass; 3/3 contract selectors pass, lint 100%. No real device command ran.** This tool does not provision N2 on a board whose native mounts have also disappeared.

The executable is `scripts/lab/replay_unified_state.sh <serial>`. Local input audit, safe while boards remain offline:

```sh
bash scripts/lab/replay_unified_state.sh --check-inputs
```

It requires `$WORKSPACES/westlake-generation-n2-51a78bde/package.json` (full SHA `51a78bde7075305758bd40b0af3169753dc4be343509e8a8e3d8909fb5d9df09`), `$WORKSPACES/vm-copies/{j2-0715c964,j3-75c2068c}/oh-adapter-runtime.jar`, the main checkout's frozen registry/board whitelist, and `westlake-inputs/tools/board_note.sh`. `lab_paths` resolves WORKSPACES from the environment or neighboring checkouts. No operator-specific absolute paths are embedded. Missing or altered inputs fail with the exact component/path; local audit needs no hdc.

After the outer loop authorizes a board window and its owner has acquired the board lock:

```sh
# SERIAL is a full whitelisted OH connect-key; LANE must already hold its lock.
REPLAY_LANE="$LANE" bash scripts/lab/replay_unified_state.sh "$SERIAL" --out "$RUN_DIR"
```

`--lane`, `--hdc` (or HDC) and `--out` are supported. Default lane is cx-bms; default output is a fresh host temporary directory printed in the one-line JSON status. The tool does not acquire/release a board lock: the window owner manages it using board_note.sh. The full command journal and receipt.json remain in the output directory. Existing receipts are never overwritten. Successful statuses are `replayed` and `already_unified`; any error returns nonzero and `status=failed` with a reason. `inputs_verified` is **local-only**, not a board success.

The preflight reads **38 N2 live paths excluding the replaceable JAR, one prerequisite, and two FZ-001 installer files: 41 paths per view**. It checks both the shell and `/proc/<daemon>/root`, plus local input SHA and the existing frozen-registry validator/artifact checks. The daemon must be the single root appspawn-x with PPID 1; children with NAME appspawn-x do not qualify. Boot, board-lock owner and PID/starttime are checked across the operation.

Only these starting states are accepted: the exact N2 base JAR with zero file overlays; the known J2 layer; or the complete J2+J3 stack. Unknown layers, changed sources, different shell/daemon stacks, or a native/installer mismatch stop. Native and installer files are never written. Needed JARs are sent to a fresh staging directory, SHA checked, then bound in order; both roots and topology are checked after each bind. An existing complete stack causes no writes. The shell and daemon must finish at full J3 SHA `75c2068ca9818ea8a61cd2d7e258ef70b36fb426c87036f2f8e2c472d47e6697`.

If a step fails, the tool removes only mounts introduced by this invocation, and verifies the original stack/JAR in both roots. A lost connection, reboot, daemon change or foreign stack change prevents a trusted rollback: the receipt explicitly says `rollback=unverified`, never success. Staged sources are retained, since a lost reply may hide a successful mount. No process is killed or restarted. Native state must first be restored separately if its own bind mounts were lost. The check is file identity/mount visibility, not a proof that an already-running app reloaded classes or that any app is lit.

Source reuse is pinned in [sources.json](sources.json): cx-t0 `jar_overlay.py` and `identity.py` at **511d5797e**, with the actual two-layer mount topology at `before/mountinfo.txt:101–102` reproduced in [mount-stack-evidence.json](mount-stack-evidence.json). Transport/remote return-code/lock/boot logic comes from bms_batch.Board; portable lab_paths and check_frozen are copied byte-for-byte from master commits **0c04dffcf / df560853f**. The new helper adds explicit two-root preflight, idempotence and failure handling.

Tests cover base/J2/J3 states, foreign or divergent overlays, native and installer mismatches, missing/altered inputs, corrupt transfer, second-bind failure, a bind applied before a lost status reply, boot/PID change, lock/target/status-marker failure, and local-only CLI output with stale-receipt refusal. Four-shard coverage and identity are tested too. Run:

```sh
python3 benchmark/2026-09-30-unified-replay/test_replay.py -v
agent-spec lifecycle specs/unified-replay/t1-tool.spec.md --code tools/spec-checks --layers lint,test
```

The [four shard files](../2026-09-30-round1-plan/four-board-v1/README.md) cover 66 keys exactly once. The whitelist currently has **three OH boards plus one Android reference**, so the fourth OH slot remains **unassigned**, rather than sending OH commands to the Android phone. R2: local inputs and FakeBoard behavior verified; actual replay, survival and screenshots unknown.
