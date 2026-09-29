spec: project
name: "White startup window offline evidence"
---

## Intent
Analyze campaign item 61 against the successful HelloWorld first-frame log, to inform item 60.

## Constraints
- Read existing evidence only; no board commands, VM writes, restarts, deployment, commit or push.
- A missing log is unavailable evidence, not an absent runtime stage. A missing marker alone does not prove a causal stall.
- Keep original source line numbers and hashes. Do not turn process liveness or first-frame callbacks into visual success.
