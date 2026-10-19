# Bounded 5cd existing-parent icon recovery

T11 reached `[TT-EXECUTOR] REFUSE FOREGROUND_HOST_NOT_READY` before real-spawn. T11 omitted the known awake procedure; its later screenshot was locked and the host was hidden. The exact timing/cause of which foreground check refused remains unknown. The foreground guard is retained. This package is a new candidate, not a claimed board recovery.

The fixed profile is serial5cd1e3dd00000000000000000923012c, boot0525bb05-f714-42ad-90f0-ecdb10356c4f, parent19163/birth7265322, hostUID20011300 and **SceneBoardUID20010017**. Exact cfg/run paths and complete hashes are in derive.py. `source-profile/` copies the actual repository inputs, pinned by `source-pins.json`; no old source is modified. The10-12 integration existing-parent branch is the authority pattern, not an executed61b entry. The10-19 reentry functions supply the verified desktop→host detector and ownership checks.

The derived guardian starts with child=none in AWAITING_REENTRY, emits `t12_desktop_seen` only after the verified desktop, and permits one ordinary icon-triggered spawn. It does not perform an immediate shell-triggered first launch. The original launch wrapper is unchanged except two additional STOP/deadline checks around JIT and final exec; its two foreground guards remain. Unknown spawn holds and never retries. Empty initial child is omitted from the strictly numeric owned-PID parser. Deadline and single-launch closure use only the new attempt's STOP; parent/child are never signalled. The old attempt, cfg and runtime are not written.

## CLI

All actions default to preview. Only the outer may execute while holding the exact board lock. `--window-start` must match that holder's ISO timestamp within one second. Use a fresh persistent output directory for every command. Do not unlock before STOP confirmation and power restoration. Normal actions have one600-second budget; late STOP/restore are restricted to same boot/holder/receipt, each bounded60seconds, with no further launch/UI permission.

```sh
TASK="$WORKSPACES/westlake-harness/benchmark/2026-10-20-5cd-icon-recovery"
python3 "$TASK/tool.py" preflight  # preview, device_calls=0
python3 "$TASK/tool.py" preflight --execute --hdc "$HDC" --holder "$HOLDER" \
  --repo "$WORKSPACES/westlake-harness" --window-start "$WINDOW_START" --out "$OUT/preflight"
python3 "$TASK/tool.py" apply --execute --hdc "$HDC" --holder "$HOLDER" \
  --repo "$WORKSPACES/westlake-harness" --window-start "$WINDOW_START" \
  --receipt "$OUT/preflight/result.json" --out "$OUT/apply"
# Outer: verified normal desktop; wait for t12_desktop_seen; one exact icon click.
# The reviewed outer UI adapter must restore temporary awake after EVERY uitest:
python3 "$TASK/tool.py" refresh-awake --execute --hdc "$HDC" --holder "$HOLDER" \
  --repo "$WORKSPACES/westlake-harness" --window-start "$WINDOW_START" \
  --receipt "$OUT/apply/result.json" --out "$OUT/awake-after-ui"
python3 "$TASK/tool.py" stop --execute --hdc "$HDC" --holder "$HOLDER" \
  --repo "$WORKSPACES/westlake-harness" --window-start "$WINDOW_START" \
  --receipt "$OUT/apply/result.json" --out "$OUT/stop"
python3 "$TASK/tool.py" restore --execute --hdc "$HDC" --holder "$HOLDER" \
  --repo "$WORKSPACES/westlake-harness" --window-start "$WINDOW_START" \
  --receipt "$OUT/apply/result.json" --out "$OUT/restore"
```

`apply` records its intent before awake or placement. A partial failure remains recovery-required; run restore from that intent even when apply failed. If guardian launch occurred but its exact PID/birth receipt is missing, STOP completion refuses and the outer must reconcile the new attempt before any signal. No process-group signal is issued. Recovery commands do not depend on the old parent staying alive, but require the same boot and holder. `stop` checks the new root's recorded device/inode/owner/mode and exact guardian PID/birth/argv before a scoped TERM; it never signals parent or child. Candidate directories and logs are retained.

The awake preimage is read from `power-shell dump -s`. Temporary override must read86400000 with a valid positive Timeout; no claim is made that effective Timeout stays unchanged during override. Restore uses `-o` the recorded OverrideTimeout and verifies **both** fields against the preimage. `-r` is not presumed equivalent. The outer UI adapter performs normal wake/unlock/Home/layout/icon actions; this CLI does not invent coordinates or click UI.

Seven Python offline tests run through a real Rust wrapper: source pin checks, generated-shell syntax, exact source preservation around added fences, preview, malformed power data,61b desktopUID refusal, real reentry-loop host-only/one-edge/unknown-hold cases, initial empty PID set, deadline and pre-spawn refusal. Device commands were not run by this author. Human icon/feed/video acceptance remains pending; static tests do not prove screen output or playback. `stop` and `restore` are separate receipts, neither is a complete closeout by itself.
