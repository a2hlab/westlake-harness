# Actual61b full128 binding review

**Verdict: ACCEPT_ACTUAL61B_FULL128_BINDING_AFTER_GAME_UNLOCK.** Producer `b583278bd` binds the real candidate boot `086db6c7-a7e7-40ce-a336-9608adc05afc`, not the original boot or a spare-board run. The original identity consumer's `load_proof` and `validate_round_bindings` both pass without any transport call.

The generated954 target/SHA pairs equal all954 actual live-check results. The proof retains507 metadata objects and5 directories, actual Boat UID20011207, the independent current-boot/WMS parameter observation, and the original postinstall940 as its base. The actual user authorization content and SHA were independently checked; another user confirmation is not required.

All128 original install records are admitted by the original consumer. The eight disabled plans contain18×7+2 keys in canonical order, preserve121t10+7t20, and retain45-minute windows with35-minute new-test cutoff. Every original runner/input/window pin matches. The159-entry landing list is exactly157 frozen members plus its freeze and listing files; both administrative file SHAs are recorded in `results.json`.

## Original executable command

Run only after the active game window has completed its final hook and actually released its lock. From MAIN:

```sh
export WORKSPACES="$(dirname "$PWD")"
B=benchmark/2026-10-09-demo-boatattack/v2-20261013
ROUND="$WORKSPACES/westlake-harness-t0/benchmark/2026-10-14-final61b-next-binding/actual-running-086db6c7/identity128/round"
python3 "$B/integration/final-v2-identity-f28-61b/run_candidate_post_reboot.py" \
  --out "$ROUND" --execute --detach \
  --serial 61b0657200000000000000000324012c \
  --authorization "$WORKSPACES/westlake-harness/$B/outer/final61b-user-authorization.json"
```

`--detach` is the original whole-round driver option; it returns a PID and retains output in `round.log`. The original runner validates all pins, resolves original inputs, performs pre-lock identity, enables each window itself, and checks after-lock/before-unlock identity and records. Do not manually alter pinned plans or start concurrent recovery. The generated lane label `cx-t0` is historical runner metadata; root remains the sole executing writer.

The command uses the exact producer output paths. If MAIN output is preferred, regenerate a fresh round with the original prepare helper and recheck the resulting path/pin bindings rather than editing JSON by hand. Keep the admitted generation and current candidate boot unchanged. This review did not poll live lock state or HDC; current availability remains the root's original preflight responsibility.

The runner only requires a nonempty authorization reference; this review separately verifies the referenced real user authorization and same61b128 scope. Its existence does not waive any runtime identity guard.

No actual full128 execution or UI acceptance is claimed by this review. A root wait timeout is not evidence that the game failed. Actual records, screenshots, and final signoff remain subsequent work. No board locks, HDC, runner edits, commits, or pushes were performed.
