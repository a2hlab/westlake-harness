# U8 flaky keys: zero-variable repeat on 61b (2026-10-01)

**What was wrong before.** The U8 sweep sign-off (99/166, `benchmark/2026-10-01-u8-sweep/outer-signoff.json`) counted
wikipedia as lit and fd-uhabits / fd-noice by a single run each. All three are two-Activity / Compose-route keys that
flip between lit and a blank white window on the same state, so a single run says nothing about a fix.

**What was run.** Same board (61b), same state (RUNTIME `e953c0921536`, BOOTIMAGE `4db882a81732`), no variable changed,
`board_run.py` (U8 controls smoke PASS first), each round `--reinstall --hilog --shots 5,20`. Round r2 was cut short:
the lane ran board_run in the foreground of an agent tool call and the 6-minute tool timeout killed it after
fd-uhabits was installed (r2's fd-uhabits is void); the outer loop continued r2b–r5 with `board_run.py --detach`.

**Result (outer read of every t20 screenshot; contact sheets in this directory).**

| key | r1 | r2 | r2b | r3 | r4 | r5 | t20 lit rate |
|---|---|---|---|---|---|---|---|
| fd-noice | lit | white | white | lit | lit | white | **3/6** |
| wikipedia | lit | white | lit | lit | white | white | **3/6** |
| fd-uhabits | white | void | white | lit | white | lit | **2/5** |

Every run's facts.txt: `alive_t5=3 alive_t20=3`, every key `foreground_unconfirmed` — alive and the focus flag do not
separate lit from white; only the screenshot does.

**Rule.** These three keys are flaky on U8 (about half the time). A fix that targets them is judged by a rate over
≥ 3 repeats against this baseline, never by one run; wikipedia is added to `knowledge/gates/flaky-keys.json`.
