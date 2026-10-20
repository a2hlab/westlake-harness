# T34 UI-only commands — review before a future window

Do not use this new helper in W02. CC remains the sole device executor. These commands were not executed on a device by this lane.

Set `MAIN` to the actual primary repository, `W` to the existing new window, `S` to a fresh session JSON, and `HDC` to the existing authorized HDC executable. The JSON must contain actual `serial`, `boot`, complete `holder`, and epoch `start`. Serial is fixed to 61b0657200000000000000000324012c; holder actor must be `inner(cc-video)` and start must match its ISO timestamp. After reboot replace only the session input with a freshly observed boot; never reuse the old apply boot. No session values are fabricated by this helper.

```sh
UI="$MAIN/benchmark/2026-10-21-t34-demo61b-video/ui-01/ui.py"
python3 "$UI" --repo "$MAIN" --window "$W" --session "$S" \
  --tag icon-01 --observe-seconds 90 launch
```

`launch` uses the pinned BMS `desktop_launch`: current desktop layout, exact `org.westlake.imehost.EntryAbility` icon, bounded page search. It does not reuse old icon coordinates. All uitest calls restore override86400000 and read it back in the same remote dispatch. Captures at requested offsets 0/5/10/20/30/45/60/75/90 are evidence, not an automatic feed verdict or exact first-frame time; command latency can delay each capture. Each capture records actual time/SHA. No click follows the capture schedule.

Root must read an actual image before supplying any content coordinates. A gray host page is not a video target. These example coordinates are variables supplied from that review:

```sh
python3 "$UI" --repo "$MAIN" --window "$W" --session "$S" \
  --tag reviewed-tap-01 --x "$X" --y "$Y" --observe-seconds 20 tap
python3 "$UI" --repo "$MAIN" --window "$W" --session "$S" \
  --tag reviewed-back-01 --observe-seconds 20 back
python3 "$UI" --repo "$MAIN" --window "$W" --session "$S" \
  --tag check-01 capture
```

Every tag is exclusive and creates an intent before dispatch. Marker loss leaves `intent_unknown`; no write retry. A completed UI action followed by awake failure retains its UI rc separately from the combined command rc. Do not retry under a new tag merely because the response was unknown; reconcile first.

Experiment commands refuse at elapsed1200s. Explicit recovery mode extends only normal launch/capture/power to elapsed1800s; no recovery taps/back, installation, reboot, transaction rollback or lock management exists here:

```sh
python3 "$UI" --repo "$MAIN" --window "$W" --session "$S" \
  --recovery --tag restored-icon-01 --observe-seconds 90 launch
python3 "$UI" --repo "$MAIN" --window "$W" --session "$S" \
  --recovery --tag original-power --power original power
```

61b's original power is Timeout30000/Override86400000. `power` sets only the override and verifies both values; it does not replace the original base timeout. If the base timeout has drifted it refuses, leaving correction to the reviewed recovery procedure. Recovery transaction/reboot/unlock remain the existing executor's responsibility.

Offline check, with no device calls:

```sh
T34_MAIN="$MAIN" python3 "$MAIN/benchmark/2026-10-21-t34-demo61b-video/ui-01/test_ui.py" -v
```
