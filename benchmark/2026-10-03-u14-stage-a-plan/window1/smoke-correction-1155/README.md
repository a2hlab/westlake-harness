# U14 11:55 smoke-spec correction (pending outer review)

The r2 gate falsely rejected a nonzero Flutter surface because its regex required a `0x` prefix. All three real LocalSend logs contain a nonzero uppercase, zero-padded address without that prefix. The second rejection required a conditional finishing-token M6 marker in `fd-app`, a different key from the source prediction's `fd-AppManager`.

Only two activation criteria change: accept the outer-provided nonzero surface regex, and remove M6 from mandatory activation markers. All groups, control AEAD/selftests, fingerprint checks, member SHA checks, loaded-instance limits, M5 and bind-order criteria remain byte-for-byte identical. Payload and bundle SHA do not change. The running executed specs and recovery specs have not been modified.

`executed-smoke-*.json` preserve the r2 specifications. The three proposal files remain pending outer review; `smoke-*.diff` give the exact changes. `replay-*.json` contain the actual r2 fingerprints/maps/view checks and selected real marker lines, linked to the original report SHA. Replaying the proposals passes for all three boards. This is an offline activation decision, not a screen verdict or a claim that Flutter's subsequent raster crash was fixed.

The source's M6 paths are `fd-AppManager` (KeyStoreActivity) and `termux`. Current accepted v5 schedules `termux` on 5cd; `fd-AppManager` is not scheduled. No extra key has been added. `m6-stage-a-observation.json` defines record-only observation of that finishing-token marker and subsequent background/terminate transitions. Marker absence means untriggered/unknown and cannot veto smoke. The source predicts this path; this report does not invent an observed M6 success line. Read the existing termux Stage A hilog for its actual occurrence and submit its t20 screenshot for outer judgement.

Mac and actual a2hlab production PATH: 27 known-answer tests PASS on each. These include the three actual LocalSend lines, optional prefix/nonzero success, zero/nil rejection, unchanged strict fields, missing M5 rejection, crypto failure rejection, incorrect fingerprint rejection, and excessive ART/bridge copies rejection. Original `fd-app` M6 zero matches do not participate in the revised smoke verdict.

Do not install these proposals or reopen a board window before outer review and all three U13 recoveries/final identity checks/unlocks.
