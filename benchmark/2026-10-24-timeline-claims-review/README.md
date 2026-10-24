# Timeline claims check: event-timeline-addendum + parent-log-closure

**No arithmetic errors. The core claims are supported:**
- click → `spawn_started` ≈42 s;
- click → birth ≈44 s, with birth = tick 6535369 / 100;
- untimestamped parent.log lines cannot place request arrival.

## Precise points
1. **g10-env addendum `README.md:19` and `results.json` `next_minimal_question` (inference).** These treat a host *foreground* timestamp as if it were a *request* timestamp. A foreground callback near the click does not show that the spawn request went out early; T114 recorded a host foreground about 2.9 s after a tap. The next question should ask for the request-send or accept time.
2. **g10-env addendum `README.md:3` and `results.json` conclusion (precision).** "Birth about 2–3 s after `spawn_started`" assumes the integer label is rounded. If the label is floored, the interval is 1.7–2.7 s. The `click_to_spawn_started_nominal_bounds_s` field, [41.26, 41.93], likewise treats 65351 as exact. README:15 already states the integer precision, so these are labelling issues; no conclusion changes.
3. **t4 parent-log-closure `README.md:9` (wording).** "The preceding ~44s" is the click → birth interval; the interval before `spawn_started` is ~42 s. Minor.

Per-claim arithmetic and verdicts are in `results.json`. Only the five report files were read; no device, REA or runtime/controller/watchdog/executor/env access.
