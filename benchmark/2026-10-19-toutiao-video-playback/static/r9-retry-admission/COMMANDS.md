# Retry command mapping (outer execution only)

Run from `$MAIN`; use one new, never-used evidence root `$RETRY_OUT`.
Pin the unchanged executor and candidate using `source-pins.json`. The previous admission is historical; the outer records this retry lock time, source pins and bounds before executing. No binary/config modification is required.

```sh
cd "$MAIN"
EXEC=benchmark/2026-10-19-toutiao-video-playback/candidate-r9/video_guarded_window_r9.py
python3 "$EXEC" preflight --boot 4117236f-c834-4f70-82fd-c39929d76573 --parent 4995 --birth 7022 --out "$RETRY_OUT/preflight"
python3 "$EXEC" apply --boot 4117236f-c834-4f70-82fd-c39929d76573 --parent 4995 --birth 7022 --out "$RETRY_OUT/apply"
```

These baseline parameters are valid only if existing fresh guards pass. After successful placement use the existing snapshot/policy/fresh-boot/log-parameter/icon sequence; maximum five normal desktop icon attempts. Do not force-spawn, kill the parent, clear data, or extend the experiment to diagnose exits. Preserve every failed attempt. Candidate binding/video remain NOT_REACHED if their consumers are never reached.

The window clock starts at lock acquisition, including preflight/apply/reboot. At lock+20min stop attempts/observations and begin original rollback; reserve the last10min within the30min hard limit. Neither this executor nor `Board.ready()` implements that global deadline or attempt counter: outer is the enforcement owner. An earlier fatal guard also ends experimentation. No new attempt is allowed merely because a reboot reset uptime.

Use freshly read candidate boot/parent/birth for rollback, and the **new retry** apply plan:

```sh
python3 "$EXEC" rollback --boot "$CURRENT_BOOT" --parent "$CURRENT_PARENT" --birth "$CURRENT_BIRTH" --apply-plan "$RETRY_OUT/apply/plan.json" --out "$RETRY_OUT/rollback"
```

Never pass old `video-r9-apply/plan.json`. A failed apply after backup creation cannot be retried in the same boot by changing only output/tag; preserve its plan and recover. The existing original-boot backup checks, four exact run SHA set across WID changes, known media/player/compat states and adjacent CAS remain unchanged. Follow rollback with existing fresh boot, parameter106, original SHA/metadata/private-inode checks, same-plan snapshot, actual feed review and unlock. If the parent or foreign identity prevents the guarded rollback, stop and report; this review authorizes no bypass. Files restored alone are not full restoration acceptance.
