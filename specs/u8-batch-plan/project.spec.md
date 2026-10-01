spec: project
name: "U8 N10 and J8 batch intake"
---

## 意图

Replace the superseded N8-only U8 draft with a donor-first two-layer batch list before any prediction freeze.

## 约束

- Offline, own worktree, no push, no runtime build, input restoration or deployment.
- Read the three donor trees before claiming reusable fixes; source presence is not same-wall validation.
- Keep U7 frozen artifacts and signed measurements unchanged; no U8 freeze or expected-run in this task.

## 排除范围

- Implementing missing donors, bridge repair design, final sixty-six-key prediction and screenshot acceptance.
