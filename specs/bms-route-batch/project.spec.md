spec: project
name: "OH6.1 BMS batch preparation"
---

## Intent

Prepare offline batch tooling for board item 20 while item 19 owns OH6.1 R130+R155 deployment.

## Constraints

- No real device commands during implementation; sources remain read-only.
- Runtime execution targets only the three campaign serials and requires the invoking lane's board lock.
- Preserve original APK bytes and per-key evidence. Screenshots require external visual review; never infer LIT.
- Local commit only; report any Git sandbox failure explicitly.
