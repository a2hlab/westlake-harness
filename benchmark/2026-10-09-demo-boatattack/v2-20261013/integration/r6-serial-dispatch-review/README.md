# R6 serial dispatch narrow review

ACCEPT for the two requested offline checks. The reviewed dispatcher SHA-256 is `60f3761cdfc727814223df0441e2ad351f571642fbde8bf6b5fa250df05fb370`. Source: sibling t0 `integration/r6-serial-dispatch/serial_dispatch.py`. No running or frozen source was edited.

The request fixes handoff/events paths only. Authorization pins the request; handoff pins the actual authorization; the watch event must match the actual handoff SHA and path. This removes the circular hash dependency.

An empty held result with rc=1 selects the original recovery board_run. A retained cx-t0 lock selects direct recover-retained, original HWZZ and verify-recovered, then exact full held-line recheck and unlock. Recovery, HWZZ or verification failure prevents unlock. Foreign or ambiguous ownership refuses action.

Validation: isolated original 6/6 tests and additional 8/8 rejection cases, all subprocess transports mocked, zero device calls. Negative cases cover recovery/HWZZ/verification failures, held stderr/malformed/changed, and wrong handoff/auth pins. This is not live execution or seal acceptance. Final freeze must retain the reviewed source SHA.
