# Joint production command (not executed)

Run only after the outer supplies the final consumer snapshot and reviewed pin
manifest. `CONSUMER_SNAPSHOT`, `CONSUMER_PINS`, `BRIDGE_INPUTS` and `NEW_T29_OUT`
must be absolute paths. `BRIDGE_INPUTS` is the existing ORB workspace containing
`westlake-touch21` and `out-touch21`; use the original T18 input-pins, not newly
substituted inputs. `NEW_T29_OUT` must not exist.

```sh
python3 "$T4/benchmark/2026-10-20-t29-window-observation/production/build.py" \
  --repo "$MAIN" \
  --sdk /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native \
  --bridge-inputs "$BRIDGE_INPUTS" \
  --bridge-base "$HOME/.local/share/westlake/t18-production/production-02" \
  --shim-base "$T4/benchmark/2026-10-20-t28-rgbx/.private/production-01" \
  --consumer "$CONSUMER_SNAPSHOT" --consumer-pins "$CONSUMER_PINS" \
  --out "$NEW_T29_OUT" --execute
```

Order: exact baseline relinks, new bridge, exact owner extraction, then shim.
Checkpoint02 is read-only. The known dca extraction fixture is not the source of
future bridge offsets. No device/deployment authorization follows from this build.
