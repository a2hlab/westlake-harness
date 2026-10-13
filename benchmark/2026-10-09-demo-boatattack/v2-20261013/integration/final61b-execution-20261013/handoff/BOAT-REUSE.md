# Shortest evidence reuse: actual f28 GAME_PASS →61b

The successful f28 source is `outer/r6-interactive-main/interaction_steps.py`, not the older automatic accelerate-first runner. Its actual record and GAME_PASS review show five actions: **left, right, right, accelerate, reset**. Same child PID5158/birth7195 remained through images; LAP0/3→1/3 was visible by step2. This is source evidence only, not a61b result.

`boat61b/interaction_steps.py` is an exact one-line serial whitelist derivation (5ea→61b); source/derived SHA and successful record/review pins are in `boat61b/source.json`. All7asset pins, fixedAPK, live BMS UID, child/parent PID+birth, geometry, desktop launch, original3+6+6+15 cadence, root-stepped input and bounded cleanup remain byte-identical. Actual61b UID20011207 comes from new complete postinstall capture. Newboot is deliberately null pending observation. Preview rc0/device commands0 is in `boat61b/preview.json`.

Derived runner SHA: `4d6598b4bd24c0c4f9cc273a4a2e0ce628fbfe089b2c476276e97966950612bf`.

Root should only start a game window with enough time for240sec execution plus90sec cleanup. Do not squeeze this into an expiring deployment window, extend that window silently, or add another coldboot solely for UI evidence. Preserve successful placement/currentboot and take the next authorized bounded validation window if needed.

## Existing invocation

Root makes a new plan from plan.disabled.json: execution_enabled=true, boot_id=actual newboot, remaining fields unchanged. Root authorization fields:

- approved_by=outer(codex), action=boat-interaction
- plan_sha256=SHA of enabled plan; runner_sha256=derived runnerSHA above
- serial=61b0657200000000000000000324012c, owner=outer(codex), boot_id=actualnewboot
- expires_epoch=no later than the current window execution cutoff
- spare_board_authorized=true (legacy runner field for an independently authorized experimental window; the user authorization now explicitly includes61b, not a claim that61b has no V1 history)
- append user_authorization typed pin for the real current approval record; no new permission request.

```sh
python3 "$RUNNER" --plan "$GAME_PLAN" --out "$GAME_OUT" \
 --authorization "$GAME_AUTH" --authorization-sha256 "$GAME_AUTH_SHA" --execute
```

Use the existing root process recorder/background launch so root can read newly saved images and supply local step files. When record.status=WAITING_FOR_ROOT_STEP, submit `steps/step-001.json` etc through an atomic local rename, with:

```json
{"approved_by":"outer(codex)","boot_id":"ACTUAL_NEW_BOOT","child":"COPY THE COMPLETE ACTUAL record.child OBJECT","action":"left"}
```

The child value must be the JSON object (pid,birth,ppid,parent_birth,uid), not the example string. Derive it from the current record; never copy5ea identity. Each step rechecks PID/UID/parent/birth, all7child-root SHA and the owned1920x1200 window before input, then saves the after image. Read each actual image before the next action. Reuse the successful sequence left→right→right→accelerate→reset when current images support continuing; do not assume the same starting heading guarantees a result. Finish with action=finish, disposition=retain or rollback under root's current authority. Finish does not itself deploy, retain authority, rollback sources or cold_stop a parent; those remain outer responsibilities.

Exact existing commands (no guessed coordinates):

1. left: `uinput -T -m 154 1046 49 1046 -k 5000 700`
2. right: `uinput -T -m 154 1046 259 1046 -k 5000 700`
3. right: same as2
4. accelerate: `uinput -T -d 1794 1074 -i 9000 -u 1794 1074`
5. reset: `uinput -T -c 1584 1074 200` (only reset waits2sec)

Require actual buffers/default-size/bounds1920x1200, normal circular HUD/colors, samePID left/right visible heading response, forward response and LAP0→1/3 evidence. No water-facing-course precondition is added. WMS focus/zorder remain recorded advisory for the embedded child. Natural boat movement alone is not a steering response. Reset is useful recovery evidence, not a newly invented t2b hard gate. Keep every partial group; no automated GAME_PASS, no claiming a full lap circuit, no repeat same-failed recipe without new evidence. The runner does not rebuild or alter runtime/cfg, clear data, or kill the system parent.
