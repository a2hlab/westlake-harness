# R6 actual-image and source review

## Evidence first

The original R6 five-touch group did **not** establish steering or LAP advancement. Ten Boat frames were personally read: normal colors and round HUD; touch1 moved onto the beach, touch2-4 remained effectively stranded with LAP0/3, and touch5/final visibly returned to water. Five injection rc0 values are not playable acceptance. This is not an app-crash verdict.

All five popup t20 frames retain their required controls (DropCount, Seal, StudyTracker, ClipboardEditor, LifeCounter). Raw facts report15/15 captures and5/5 live t20; every raw record still says `foreground_unconfirmed`. Existing right-edge clipping is not relabelled a new regression. Reviewer observations do not replace root human signoff.

## Initial conditions and source

Historical R4/W3 has a `t30.jpeg` start, not a `ready.jpeg`. Its TIME00:12.243 frame faces the water/buoy corridor; R6 ready TIME00:32.276 (52.674seconds after icon) faces houses/beach. They are not the same initial condition. Historical original-coordinate controls differ from the newer source-derived centers; historical supplemented success cannot transfer as unmodified current-five success.

`HumanController` independently latches throttle and steering; `Engine` gates both on `_yHeight > -0.1`. `Boat.ResetPosition` selects the nearest waypoint, clears linear/angular velocity and sets waypoint rotation. It does not restart the process or reset LAP. The exact source pins/line ranges and actual-image hashes are in the two JSON files. Shore collision/height gating remains a hypothesis: no live `_yHeight` or delivered input-state value was measured.

## Minimum supplemental boundary

A root-authorized new-window package may keep the same f28 candidate and seven pins, first reset with source center1584,1074 and capture an actual water/waypoint-heading baseline, then immediately repeat the same source-derived five controls. Do not rerun the startup wait before the controls. Keep one PID/birth/UID within this separate sequence; no new parent, signal, app restart or physics tweak. Each turn needs visible heading change; LAP advancement remains required. Preserve the original failed-to-establish group and its hashes: supplementary evidence is not retroactive original-cadence PASS.

Current R6 is already UNLOCKED. A new boot needs fresh authorization/preimages and tuple binding, not copied db4296/5117. No device commands, builds, hook edits or signoffs were performed by this reviewer. Next T4 follow-up is independently reviewed as a new immutable object; rendering/popup success alone never transfers gameplay acceptance.
