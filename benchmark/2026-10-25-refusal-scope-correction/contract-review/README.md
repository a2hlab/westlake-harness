# T130-B contract review — refusal-scope extrapolations to retract (2026-10-25)

Independent review of the global-blocking judgments around the `reasoning_extraction` refusal, from the verified input set (`.private/t130-scope-input/`, 5/5 SHA-256: project/t3/t4/t5 specs, `execution-interruption-01.json`, `official-guidance.md`). Review opinion only — outer edits the contract files. No deployment/process/controller operations, no permission changes, no stopped-object reads. **This correction does not lift the original refusal and does not claim any candidate validation completed.**

## Basis

Official guidance (checked 2026-10-25): `reasoning_extraction` concerns requests to reproduce internal reasoning; remedy is removing such output demands (ask for brief explanations/evidence summaries); if a compliant reformulation still declines, contact support with the request ID. No fallback is recommended, and **a category tag does not establish a blanket ban on device operations**. The interruption record is lane-local: one client stop in `cc-video`, offending content unavailable, no lock/write observed, "keep the stopped execution stopped; resolve through supported process; user authorization alone does not clear it."

## Three checkpoints — extrapolations to retract (keep the underlying facts)

**R1 — "受支持方式恢复执行通道" as a blanket t4 precondition.** Over-broad as written (t4 L9/L11): it converts a lane-local client stop into a project-global blocker. **Outer correction:** scope tightens to the *specific refused requests only* — those exact requests are not retried (any tool/model/entry); the lane/channel itself is **not** embargoed, demonstrated by CC normally completing the independent T129 documentation task after the stop. Other work proceeds under ordinary task preconditions. **Keep:** the concrete refusal record, no-rerouting note, and "user authorization alone does not clear it."

**R2 — "CC的reasoning_extraction停止仍有效" read as an open-ended all-CC stop.** **Outer correction:** the exact triggering request text is unknown, so it cannot be asserted that the historical request actually demanded internal-reasoning output — only the category tag is observed. Scope to the specific refused requests (not retried via other tools/models/entries); do not characterize the historical request's content beyond the tag, and do not extend the stop to unrelated CC activity. **Keep:** "不换模型或入口重试停止动作".

**R3 — t5 L17 "只有后继真实受支持恢复证据可改变执行状态" applied project-wide.** **Outer correction:** the restoration-evidence requirement applies only if the *specific stopped execution/actions* are to be resumed — not to other device work in that or any lane; CC's normal completion of T129 shows the channel is not blocked. Device-lock, rollback, and factual-acceptance work proceed under their own task preconditions. **Keep:** `product_bug_report_acknowledged` is auto-acknowledgement only and does not restore execution.

## Retained unchanged (not part of any retraction)

All `execution-interruption-01.json` facts (interrupted status, no observed lock, 0 write receipts, observation limit, board validation pending, white-screen not fixed); the no-retry-of-refused-requests rule across all specs; every t3/t4 device-lock / rollback / factual-acceptance precondition.

Machine-readable detail: `results.json`.
