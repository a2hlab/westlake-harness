# Exact owned-child exit and one manual icon reentry

T12 proved one START_FAILED-to-feed attempt, not a later child exit followed by a second icon launch. This delivery implements a bounded T13 validation using the existing R2 adoption branch. It has **no device result**. Feed, actual icon input, guardian cleanup and power restoration remain human review items.

The source base is MAIN commit `2a5dfd11f6`. `t12_derive.py`, `source-profile/` and `references/t12-{tool,ui}.py` are original bytes. `source-pins.json` validates the ten source members on every generation. `derive.py` adds the exact adoption branch, sequence cutoff 2, persisted adopted identity and single-use intents. The frozen owner, launch-common, readiness, real-spawn, parser and exit classifier stay byte-identical. The JIT/host_spawn wrapper differs only by the two existing T12 guards.

## Implemented boundary

- Board `5cd1e3dd00000000000000000923012c`, boot `0525bb05-f714-42ad-90f0-ecdb10356c4f`, parent `19163/7265322`, child `31210/7485570`, UID `20011300`, SceneBoard UID `20010017`. Missing/reused/foreign child refuses preflight and apply; no replacement selection or initial spawn.
- R2 `main` really adopts the existing child as seq1 and writes its instance before `adopted`. Apply becomes `ARMED_ADOPTED_CHILD` only after it reads the matching live guardian/lock/instance and rechecks the original child.
- Exit mode is fixed in the preflight receipt. Optional `term-once` uses the original `rb_signal` after the full child guard; remote `term.intent` is created with noclobber before dispatch. Loss or failure of the local receipt cannot authorize another signal. TERM success does not prove exit. Natural exit after adoption needs no signal.
- The original exit classifier accepts confirmed absence or same-birth Z; reuse/unknown refuses. The real reentry loop requires a new desktop→host edge and no old owned window. Successful real `do_one_launch` leaves child/birth/seq2 in the parent shell. Remote `spawn.intent` bounds entered spawn attempts even after a failed wrapper or lost result; unknown remains sticky hold.
- `ui.py` minimally derives the original T12 UI. Only prepare/launch/capture are available. `icon.intent` is exclusive in the new remote ROOT, not a local output directory; the adoption/deadline guard is checked again before the selected icon click. Normal desktop layout/navigation is reused. No video-specific click is added. Sampling remains 1 second and can miss an extremely fast Home→icon switch.
- 600 seconds includes normal recovery, with a 60-second guardian reserve. STOP/deadline fences remain before spawn and after JIT. Stop/restore are same-receipt recovery operations; neither controls the parent or business child. Uncertain guardian state requires outer reconciliation, retaining lock and evidence.

## Reproducible local checks

```sh
python3 benchmark/2026-10-20-5cd-owned-child-reentry/test_t13.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_5cd_owned_child_reentry
```

`tests.*` contain 19 passing Python tests; `rust.*` contain seven passing selectors. These invoke actual generated main/adoption, child ownership, original rb_signal, exit-verdict/monitor, do_one_launch/reentry and post-JIT guard suffix. Only external process/filesystem/transport boundaries are fixtures. The successful spawn test does not replace do_one_launch with mock result text: its production assignments are verified in the caller shell. Guardian cmdline/birth/lock/instance drift and lost TERM receipt are covered. Hardware capture/feed and restoration are not simulated into a pass.

## Outer command sequence

Use a fresh persistent evidence directory and fresh `icon-manual-5cd-t13-*` root. Obtain the exact lock holder and its timestamp through the existing outer process. The following are invocation templates, **not executed by this author**. Every tool command defaults to preview unless `--execute` is supplied.

```sh
T13=benchmark/2026-10-20-5cd-owned-child-reentry
python3 "$T13/tool.py" preflight --execute --repo "$REPO" --hdc "$HDC" \
  --holder "$HOLDER" --window-start "$START" --root "$T13_ROOT" \
  --exit-mode term-once --out "$EVIDENCE/preflight"
python3 "$T13/tool.py" apply --execute --repo "$REPO" --hdc "$HDC" \
  --holder "$HOLDER" --window-start "$START" --root "$T13_ROOT" \
  --exit-mode term-once --receipt "$EVIDENCE/preflight/result.json" --out "$EVIDENCE/apply"
# Only after ARMED_ADOPTED_CHILD; omit this command if natural exit has already occurred.
python3 "$T13/tool.py" term-once --execute --repo "$REPO" --hdc "$HDC" \
  --holder "$HOLDER" --window-start "$START" --root "$T13_ROOT" \
  --exit-mode term-once --receipt "$EVIDENCE/apply/result.json" --out "$EVIDENCE/term"
```

Read original `state`, `events.log`, `instance.txt`, process and WMS evidence through the existing outer read-only collector. Require confirmed exit and `AWAITING_REENTRY`. Do not infer exit from the TERM rc. For natural mode select `--exit-mode natural` in preflight/apply and never run term-once.

```sh
python3 "$T13/ui.py" prepare --execute --repo "$REPO" --hdc "$HDC" \
  --holder "$HOLDER" --start "$START" --root "$EVIDENCE/ui" --tag desktop \
  --receipt "$EVIDENCE/apply/result.json"
# Outer reviews desktop screenshot and the new t13_desktop_seen event first.
python3 "$T13/ui.py" launch --execute --repo "$REPO" --hdc "$HDC" \
  --holder "$HOLDER" --start "$START" --root "$EVIDENCE/ui" --tag icon-once \
  --receipt "$EVIDENCE/apply/result.json"
# Subsequent capture uses the same receipt, a fresh tag, and optional identity JSON.
python3 "$T13/tool.py" stop --execute --repo "$REPO" --hdc "$HDC" \
  --holder "$HOLDER" --window-start "$START" --root "$T13_ROOT" \
  --receipt "$EVIDENCE/apply/result.json" --out "$EVIDENCE/stop"
python3 "$T13/tool.py" restore --execute --repo "$REPO" --hdc "$HDC" \
  --holder "$HOLDER" --window-start "$START" --root "$T13_ROOT" \
  --receipt "$EVIDENCE/apply/result.json" --out "$EVIDENCE/restore"
```

Tool `--root` is the remote attempt root; UI `--root` is a local persistent output directory. Retain the original apply receipt for cleanup. If placement/guardian startup fails, use its latest persisted intent receipt for recovery and reconcile any missing guardian identity before claiming cleanup. No automatic retry, cfg change, app data change, runtime deployment, restart or child cleanup is provided.
