# First-frame suspicion replay: evidence before a detector

## What was wrong; the rule established here

**The quoted 32/111 `present` and 2/2 `finishDrawing` counts do not measure presentation or an executed drawing-completed handshake.** On the retained T7d 5cd logs, `finishDrawing` is a method-table entry and a `class_linker` interface lookup. `present` includes JNI registration, method/type names and even `SSLContext ... provider present` / `MediaRouter ... presentationDisplayId`. PID filtering alone does not remove these false semantics.

This replay retains **78 attempts: all 66 U6 keys and all 12 T7d records (10 initial keys plus two fd-noice retries)**. It finds **no explicit executed present, finishDrawing or NotifyDrawingCompleted marker** under the documented matcher. That means **unknown coverage**, not zero displayed frames. Do not divide VSync by these zeros or infer that a handshake happened. The separate background/foreground screenshot observation remains valid evidence of a symptom; these string counts do not establish which graphics layer caused it.

Evidence examples in `evidence/observations.json` carry original line numbers and source log SHA256:

| T7d initial key / PID | Whole-log present substring | App interval present substring | finishDrawing false evidence |
|---|---:|---:|---|
| fd-noice / 5079 | 32 | 29 | L18674: `9: void ...finishDrawing(...)`; L19549: `class_linker.cc:8744` interface resolution |
| noice / 12938 | 111 | 108 | L18687: same method enumeration; L19515: same interface resolution |

After removing non-execution names, the remaining present substrings are unrelated provider/display-property text, not graphics receipts. The corrected VSync count is one successful `RequestFrame rc=0` per request, not ENTRY + calling + result + callback counted as four frames. For fd-noice/noice it is **104/23 requests**, each with 104/23 observed callbacks; wikipedia has **582/582**. Repeated fd-noice white captures have **95/95** and **98/98**. Request first/last timestamps are retained; observed log volume is not assumed to be continuous drawing until t20.

## Targets and failed negative controls

The original t20 images were inspected for five nonterminal U6 white keys and all twelve T7d attempts. U6 signed visual labels and their original review SHA are retained for all 66 keys. Image size is never a visual verdict.

**Seven N9 investigation keys** (nine white/nonterminal attempts):

| Key | Retained basis | Exploratory score | Limitation |
|---|---|---:|---|
| wikipedia | T7d initial: white, 582 requests/callbacks | 40 | Churn proxy only; no executed-present coverage |
| fd-noice | T7d initial + two white retries: 104/95/98 requests | 20 / 0 / 0 | Same symptom straddles the arbitrary count threshold |
| noice | U6 white: 49 requests | 0 | T7d same key is an own-UI control; no guaranteed repair or deterministic wall |
| fd-AppManager | U6 white: four requests | 0 | Symptom-only target, not evidence of the present-layer hypothesis |
| fd-app | U6 white: five requests | 0 | Competing earlier startup/native issues not ruled out |
| fd-shatteredpixeldungeon | U6 white: five requests | 0 | Competing earlier startup/native issues not ruled out |
| termux | U6 white: no observed VSync request | 0 | No request coverage; do not call it a demonstrated compositor stall |

`N9-TARGETS.md` contains all nine target attempts and **34 independent lit control observations**: 29 U6 own-UI observations (including the two signed flaky observations, not a new 29-stable-light claim) plus five T7d own-UI observations. **29 controls score zero; five score 40 and fail the expected-low check**:

| Lit U6 control | Successful VSync requests / callbacks |
|---|---:|
| antennapod | 1347 / 1346 |
| fd-auxio | 1328 / 1327 |
| fd-com-kunzisoft-keepass-libre | 1355 / 1354 |
| fd-filemanager | 1275 / 1274 |
| opencamera | 723 / 722 |

All five have more requests than white wikipedia. **VSync volume is not a discriminating first-frame detector.** Five of 34 lit observations give a false alarm at score >=20; seven of nine eligible white attempts score zero. This is retrospective exploratory calibration, not an independent accuracy claim. We deliberately do not suppress control scores using their screenshot label or refit thresholds until the negatives disappear.

U6 organicmaps and T7d x are white but have process-disappearance evidence and are excluded from the requested nonterminal set. For x, the later `main_threw` remains a post-capture observation; it is not backdated. U6 Seal has no usable launch/capture observation and remains missing, not a white target. Black, desktop, non-own-UI and unknown cases remain separate in `results.json`.

The frame-owner/focus check was unconfirmed in the retained target captures. They establish a white-screen symptom with a bound running app, not independently proven Surface ownership. A future N9 trace must bind window/surface ID to PID and buffer/frame ID. Different APK keys and runtime generations are not an identical-input, single-variable comparison. Preserve the fd-noice/noice build distinction and every attempt.

## Rule v1

Implementation: `scripts/lab/scan_first_frame.py` (read-only CLI and reusable functions).

1. Reuse `first_fatal.load_run` for package-launch/UID process bindings, original log SHA, crash reports and process snapshots. Require the diagnostic receipt, complete log, clicked time and one hashed t20 capture. Use board-local UTC+8 capture mtime with the existing last-millisecond convention; process snapshots named t20 are retained as stage-level disappearance observations, not exact instruction timestamps.
2. Count app-PID execution events from clicked time through the original t20 cutoff, grouped by PID. Keep whole-log substring counts only for contamination auditing. Exclude `OH_RegHook`, `-> fn=`, `class_linker.cc:` and method enumeration via the existing execution classifier.
3. VSync: exact `OH_DER_VSync` tag, successful `scheduleVsync RequestFrame rc=0`, failed nonzero rc and `onOhVsync ENTRY` separately. Present/finish/notify require explicit graphics-tagged operation receipts; an unobserved marker yields unknown observability and a null ratio.
4. **Exploratory log-only score**, declared before the U6 replay: +20 for >=100 successful requests; another +20 for >=500; +20 for >=20 requests with callbacks below half of requests; +40 for an explicit present-failure receipt. No points for absent present/finish markers. These thresholds are heuristic count bands, not probabilities or a validated diagnosis. The two latter conditions do not occur in the eligible white/control replay.
5. Separately admit a target only with a reviewed white capture, complete bound evidence and `first_fatal` status `no-observed-termination`. Ignore benign-noise filtering for graphics and termination counts; do not delete causal evidence. Signals 4/35/42 remain nonterminal under the reused classifier. A missing terminal log is not proof of health.

`results.json` publishes every attempt, scores, target eligibility, control failures, per-source hashes and exclusions. `evidence/observations.json` includes per-PID counters, examples, process-receipt hashes and termination summaries. Long messages are explicitly truncated with their full message hash; original logs remain authoritative. `evidence/review.json` binds visual labels to capture hashes. These are analysis artifacts, **not a runnable bms_batch manifest**.

## Reproduce and hand off

```sh
python3 scripts/lab/scan_first_frame.py RETAINED_APP_RUN
python3 benchmark/2026-10-01-first-frame-suspects/collect.py --workspaces WORKSPACES > /tmp/first-frame-replay.json
python3 benchmark/2026-10-01-first-frame-suspects/report.py --check
python3 benchmark/2026-10-01-first-frame-suspects/test_scan.py -v
```

Raw roots relative to `WORKSPACES`:

- `westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/{5cd,61b,5ea,5ea-resume}/`
- `westlake-harness-wiki/benchmark/2026-09-30-dex2oat-l2/runs/t6-5cd1e3dd00000000000000000923012c-20261001T042555/batch/`

Run grouping is exact and rejects a missing/extra attempt; no successful retry replaces an earlier record. The collector prints JSON and changes no source, input or device. Compact replay and synthetic adversarial tests cover foreign PID traffic, registration strings, pre/post-cutoff events, nonterminal signals, disappearance, label-independent scores and tampered capture reviews. Validation receipts and both isolated-master gates are in `validation.json`.

Outer ACK90 06:01 paused the proposed N9 damage build pending trace/provenance evidence. This target list does not override that decision and claims no expected unlock. For a later authorized trial: retain original t20, same-board controls and terminal evidence; collect real executed draw/queue/acquire/present markers linked by surface/frame ID. A diagnostic t25 background/foreground image is separate, never a replacement t20 hit. N8's new white Flutter observations are outside this requested U6/T7d replay and must be added as a separately pinned cohort, not silently mixed in.

Subsequent outer ACK80 06:05 tentatively accepted cc-t3's offscreen-window transition explanation for the new 61b wikipedia/gallery trace comparison, pending publication and hash verification of the raw traces. That is independent evidence, not a conclusion produced by this hilog score, and does not establish the cause of all seven targets. The obsolete whole-log present/finishDrawing inference stays withdrawn.

Landing uses `landing-paths.txt`, plus only this task's one root README row and one DIGEST line. Do not copy the lane's pending U8 skeleton or unrelated staged files.
