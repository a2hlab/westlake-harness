# Root-only T33 commands

Run from MAIN after copying the listed files. `MAIN`, `BASE`, and `CANDIDATE` below are operator paths; no old window context is reused.

```sh
MAIN="$WORKSPACES/westlake-harness"
BASE="$HOME/.local/share/westlake/t33-demo-host-61b"
W="$BASE/window-01"
H="$MAIN/benchmark/2026-10-20-t33-demo61b-host/static/window_ops.py"
CANDIDATE="$WORKSPACES/westlake-harness-t4/benchmark/2026-10-20-toutiao-launcher-page/.private/production-01/candidate-signed.hap"
python3 "$H" --repo "$MAIN" --window "$W" lock
python3 "$H" --repo "$MAIN" --window "$W" intake
python3 "$H" --repo "$MAIN" --window "$W" install "$CANDIDATE"
python3 "$H" --repo "$MAIN" --window "$W" reboot
# PREVIOUS_BOOT is the actual pre-reboot boot from this window, never copied from this card.
python3 "$H" --repo "$MAIN" --window "$W" wait "$PREVIOUS_BOOT"
python3 "$H" --repo "$MAIN" --window "$W" launch
python3 "$H" --repo "$MAIN" --window "$W" capture
python3 "$H" --repo "$MAIN" --window "$W" read
python3 "$H" --repo "$MAIN" --window "$W" power
```

Root reads the early/final images: no development title/input and actual feed. Waiting is not faster-start proof; no video repair is claimed. Retain or start recovery before1200s; finish within1800s. `launch` has a per-boot exclusive intent marker and is never blindly replayed. `wait` timeout preserves evidence; it does not authorize another reboot. After actual review/root decision:

```sh
python3 "$H" --repo "$MAIN" --window "$W" unlock
```

If replacement fails visual/identity acceptance, use the exact original from this61b intake; root keeps the lock:

```sh
python3 "$H" --repo "$MAIN" --window "$W" rollback "$BASE/intake-01/installed-entry.hap"
python3 "$H" --repo "$MAIN" --window "$W" reboot
python3 "$H" --repo "$MAIN" --window "$W" wait "$PREVIOUS_BOOT"
python3 "$H" --repo "$MAIN" --window "$W" launch
python3 "$H" --repo "$MAIN" --window "$W" capture
python3 "$H" --repo "$MAIN" --window "$W" read
python3 "$H" --repo "$MAIN" --window "$W" power
python3 "$H" --repo "$MAIN" --window "$W" unlock
```

Set PREVIOUS_BOOT separately to the actual boot immediately preceding each reboot. The original power check is30000/86400000 (not5cd10000). Capture final guardian state/package-list/held-after through root's existing read-only channel; this minimal helper does not synthesize that evidence. Never treat close.json as signed retention or screenshot acceptance.
