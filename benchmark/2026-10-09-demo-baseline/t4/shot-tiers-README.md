# Historical first-frame screenshot tiers

## Evidence first

**Stability is not startup speed.** The previous `groups.json` screenshot field
used stable/edge membership. That field is superseded; group membership and
repeat scheduling are unchanged. `shot-tiers.json` is now the capture-delay
authority for cx-t0, independently of games, empty screens and stability groups.

The audited history is the approved 219 U13 candidate records, the complete
348-record U14 candidate union (including window-6 nested candidates), plus the
manifest's original-reference and selected records. Unique physical paths are
deduplicated. Only the selected package and exact APK SHA count: old Noice is
not the selected fd-noice version. Reference/control and recovery runners outside
this explicitly pinned domain are not silently added. This is a finite historical
evidence inventory, not a claim that every unrelated benchmark has been scanned.

The maximum of **all** identified launches in **all** selected history runs is
used, including nonlit runs. A physical `APPSPAWN SPAWN_RESULT ret=0 pid=N`
starts the clock; exact-package `AppMS spawned` is a documented fallback when
the physical spawn marker was not retained. Main-package AMS/ROUTE-A/B43 binding
identifies N; delayed Java entry itself never starts the clock. The endpoint is
the first literal `activityResumed (first-frame):` **on that same PID** after
birth. `OnDrawListener attached`, compositor output and another app PID cannot
provide an endpoint. Repeated births require every episode to have an endpoint.
This measures the requested log event, not screenshot content or lighting.

Every run must have complete timing and maximum <=4000 ms for **10 seconds**.
Missing logs/birth/frame, incomplete captures or no history yield **20 seconds**;
anything >4000 ms also yields 20. Toutiao and BoatAttack remain separate reserved
20-second slots. Log SHA mismatches against diagnostics hard-reject generation.
Dates handle midnight; reversed clocks are unknown, not a wrapped fast result.

## Delivery

Initial fresh result: **128 packages; 121 at 10 seconds, 7 at 20 seconds**.
The slow keys are antennapod, cv2-com-github-dfa-diaspora-android,
cv2-org-secuso-privacyfriendlyminesweeper, fd-organicmaps, fd-tasks, vlc,
wikipedia. fd-tasks peaks at 4.060 s and wikipedia at 4.464 s; the other five
have at least one missing timing observation. There are 465 selected runs from
688 unique input records; 216 nonselected keys and 7 other/missing APK identities
are excluded. Eleven selected observations have unknown timing. These exclusions
and source hashes are machine-readable in the top-level file.

`apps[].history_evidence` binds one of two sub-1-MiB evidence shards and the key's
JSON pointer. Each run retains original record/log SHA, board serial, exact
birth/identity/first-frame file-line evidence and elapsed integer milliseconds.
No coordinate, click, runtime change or new lighting verdict is produced.

```sh
python3 benchmark/2026-10-09-demo-baseline/t4/build_shot_tiers.py
python3 benchmark/2026-10-09-demo-baseline/t4/build_shot_tiers.py \
  --out benchmark/2026-10-09-demo-baseline/t4/.artifacts/shot-tiers-second.json
cmp benchmark/2026-10-09-demo-baseline/t4/shot-tiers.json \
  benchmark/2026-10-09-demo-baseline/t4/.artifacts/shot-tiers-second.json
python3 benchmark/2026-10-09-demo-baseline/t4/test_shot_tiers.py
```

Both generations and both history shards must be byte-identical. Raw stdout/
stderr and exits are in `evidence/shot-*.txt` and `shot-validation.json`.
`shot-landing-paths.txt` deliberately excludes the unfinished stability
summarizer. Git metadata is read-only; outer landing is required. No board,
VM, SSH, lock, promotion or gate-table mutation is performed.
