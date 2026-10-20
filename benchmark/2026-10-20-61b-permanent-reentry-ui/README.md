# Normal UI for the existing permanent 61b R2 guardian

The existing `live_tools.py launch` delegates to BMS but does not refresh awake after every `uitest`. That can leave the screen-off override at 10 seconds during navigation. This wrapper keeps the pinned original BMS `desktop_launch`, `shell`, `raw_shell` and capture functions. A thin subclass refreshes `86400000` after each successful uitest and reads back **the original Timeout plus the temporary Override**. There is no deployment, process launch helper, TERM, guardian stop, data change or crash diagnosis.

This is an operational addendum within `specs/toutiao-icon-reentry/t1-reentry.spec.md` normal manual-reentry and human screenshot boundaries. It does not claim the existing permanent R2 is newly implemented or verified. The external 0809 read showed parent6101/b16617, guardian4016/b3964, bootdcc12383 and power **Timeout30000 / Override86400000**; every real preflight reads these anew. The profile template is deliberately unusable until the fresh exact lock holder/start and evidence directory are supplied.

## Fixed boundaries

- Only serial61b, permanent `icon-manual-20261019-r2`, cfg91e31 and host UID20011206. Profile binds the current boot, parent and guardian PID/birth, exact holder/start and a single persistent state directory. Each active shell command includes the process/cfg/STOP/namespace/inode guard. The original BMS ready gate retains boot/serial checks; the subclass additionally requires the full exact holder.
- Preflight is read-only and saves the exact power pair before UI or temporary awake writes. Normal UI ends at540 seconds; the last60 are reserved for restoration. If outer recovery is late, restore alone gets a bounded emergency60 seconds under the same boot/holder. No additional UI is allowed then.
- Every successful uitest, including dumpLayout/Home/swipe and selected-icon click, is followed by awake refresh/readback. The selected icon uses the original BMS app identity `org.westlake.imehost/EntryAbility`. The final identity guard and UI command share one remote shell.
- Exclusive local launch and icon-dispatch intents precede their operations in the profile-fixed state directory. A lost marker is unknown and never automatically replayed. A later awake failure preserves an already recorded successful click. Repeating launch is refused even with a new output tag.
- Restore uses the original authority receipt and checks only same boot/serial/exact holder. It does not require a live child, parent, guardian or unchanged STOP/cfg. It writes the original Override and verifies the complete original power pair. It never stops the permanent guardian. Outer retains the board lock until restoration is proven.

## Commands (outer only; not executed in this delivery)

Copy `profile.example.json` to persistent private evidence, refresh its identities, set the exact holder/start and `state_dir`. Run from the selected repository. The tool defaults to preview; `--execute` is explicit. Keep the same profile bytes and state directory for every action.

```sh
UI=benchmark/2026-10-20-61b-permanent-reentry-ui/ui.py
python3 "$UI" preflight --execute --profile "$PROFILE" --repo "$REPO" --state "$STATE" --hdc "$HDC"
python3 "$UI" prepare --execute --profile "$PROFILE" --repo "$REPO" --state "$STATE" --hdc "$HDC"
# Read the desktop screenshot; normal Home sampling needs time, not a subsecond switch.
python3 "$UI" launch --execute --profile "$PROFILE" --repo "$REPO" --state "$STATE" --hdc "$HDC"
python3 "$UI" capture --tag after15 --execute --profile "$PROFILE" --repo "$REPO" --state "$STATE" --hdc "$HDC"
python3 "$UI" restore --execute --profile "$PROFILE" --repo "$REPO" --state "$STATE" --hdc "$HDC"
```

Preflight produces `authority.json`. Each action has its own record, raw original BMS command receipts and captures. Use a fresh capture tag, but do not replay launch. `prepare` conditionally unlocks from the actual layout, presses Home and checks launcher focus. The normal BMS launcher can then find the exact app tile. Expected current observation is seq2→seq3/new child and a human-reviewed feed screenshot; process life, old `UI_UNVERIFIED`, or a UI rc0 are not feed proof. Refresh before use; do not hardcode stale child15013.

## Local verification

`python3 benchmark/2026-10-20-61b-permanent-reentry-ui/test_ui.py --source-root <repository>` runs the actual subclass against the pinned original BMS shell/raw_shell with transport fixtures. Three tests cover timeout partial-stream preservation and six UI/recovery cases plus timeout, power parsing and zero-write preview. Cases include each-UI refresh, exactly one icon, lost marker without replay, successful click followed by awake failure, identity/holder refusal, and recovery despite process changes. No device execution occurred.

Timeout partial-stream preservation follows `benchmark/2026-10-20-t14-play-observation/observe.py`: retain the original command-N error and partial stdout/stderr, then rethrow without replay.
