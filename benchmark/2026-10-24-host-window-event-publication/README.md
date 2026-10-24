# Ordinary host/window event publication — bounded source review

**The bound producer publishes both hilog and a last-event file; it does not maintain a persistent foreground flag or directly issue a child launch.** A later successful stage write replaces the earlier foreground snapshot. That producer fact does not explain the reported ~42-second pre-spawn interval.

Producer: `main/benchmark/2026-10-20-toutiao-launcher-page/sources/baseline/EntryAbility.js`, SHA `9dc302d9aa72eb1be8635d7bc4bc4306da76f0e45d2414d67bd96d024e2a24c6`.

| Source lines | Actual behavior |
|---|---|
| 31 → 7–16 | `onForeground()` records `foreground` with empty details. |
| 21–23 → 7–16 | `windowStageEvent` records `stage-event`, the numeric event, and current `getWindowProperties()`. |
| 8–9 | A new `{event,time:Date.now(),details}` object is logged under `WL_IME_HOST` before filesystem writing. |
| 11–13, 15 | The same `filesDir/window-state.json` is opened with CREATE/WRITE_ONLY/TRUNC, written and closed; failure logs `record failed`. This is replacement, not history or state merging. |
| 28, 32–34 | Window-ready, background and destruction events use that same writer and can also replace prior contents. |

**Binding strength:** T89 accepted exact source→compiled EntryAbility member (`bb1eccd3…`)→HAP `b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0`. T106B independently bound that HAP to `/proc/4958/root/data/storage/el1/bundle/entry.hap` with maps/stat/SHA/stat and host birth10879. Retained T123 P0 has the same boot/host/birth. This is strong historical producer binding with continuity, not a new live HAP hash. The upstream system Window implementation is not source-bound by these records; no numeric enum-name assumptions are needed.

**Verified sequence:** T114 ordinary `raw/hilog.stdout:901,904,917` records foreground → stage1 → stage2 at embedded times `1792766936912`, `…6916`, `…6920`, all PID/TID5074 and window29 for the stage events. This proves callback publication order in that historical run. It does not prove successful file writes: logging occurs first, and T114's prescribed file read itself returned missing-path diagnostics. No current file state is invented.

**What a reader actually has:** a valid `window-state.json` can supply only its latest event/time/details. There is no independent foreground boolean, retained foreground timestamp, sequence counter, boot/PID binding, or replay acknowledgement. The observed window payload has `focusable` but no `focused`/foreground-state field; `focusable` cannot be relabeled as a current-focus observation. Existing hilog retains an inspectable event sequence, but is not a proven lossless consumer event stream.

**Ordinary evidence that separates the cases:** correlate same-identity callback rows with a valid last-event snapshot and any `record failed` rows to distinguish callback arrival from file publication. A separately timestamped ordinary request/consumer record is required to connect either with `spawn_started`. This producer contains no such launch call or acknowledgement. No consumer/control code was inspected, no source changed, no mechanism proposed, and no causal candidate is established.

`results.json` contains exact SHA/line bindings and the three parsed public callback records. Zero device/REA operations.

## One falsifiable prediction for the next ordinary parent.log increment

1. **Supports late arrival at an explicitly identified request boundary:** with an unchanged boot/parent PID/birth, known click-time relation, and continuous incremental coverage starting before the click, the first existing, identity-correlated request-received/accepted record appears late after the click, followed closely by `spawn_started`. This supports delay before that logged boundary only if its producer semantics establish request arrival and timestamps are emitted there; record the actual first-visible interval separately from any embedded timestamp. No marker name or request meaning is assumed to exist.
2. **Contradicts late arrival at that boundary:** the same explicit request-arrival record appears promptly after the click, but `spawn_started` appears much later. That locates the observed gap after arrival, without identifying its cause. An early request-issued record alone establishes issuance, not parent receipt.
3. **Cannot discriminate:** only `spawn_started` appears late, or the first request-like line is obtained in a later batch with uncertain buffering/timestamp semantics, missing earlier coverage, rotation, identity change, or no cross-clock relation. A foreground/stage snapshot or absence of a marker does not prove late request arrival. Preserve the observation interval and report unknown.
