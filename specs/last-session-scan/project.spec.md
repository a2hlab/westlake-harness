spec: project
name: "U7 last-session lookup impact scan"
---

## 意图

Measure session lookup failures in the accepted U7 cohort without substituting telemetry for signed screenshots.

## 约束

- Offline, own worktree only, no push or runtime changes.
- Preserve all 66 keys and signed visual categories, including missing input evidence.
- PID and queue identity control association; unknown foreground must stay unknown.

## 排除范围

- Fixing native window lookup, rerunning apps or reinterpreting screenshots.
