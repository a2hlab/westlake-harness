# T13 bounded adoption wait: independent delta review

**Accept final wait-only delta; no blocker found.** Reviewed producer commit `aafe5ac2a851dee233797f7edb5fbdd6c7f6deda`, tool SHA-256 `5e842df50593afa33c6e5bd69f96f34bc99a7c002e70362821e9e74e16916323`. No device calls or producer edits. This is not T13 UI/reentry acceptance.

| Check | Source / result |
|---|---|
| Unique start | tool.py161 remains the only `nohup`; adoption_wait32–59 contains no spawn or signal. A timeout raises into recovery-required; it does not restart guardian or resend TERM. Existing source/receipt binding remains. |
| Identity per poll |37–48: same recorded PID/birth, UID0 quadruplet, shell exe and exact entry/watchdog cmdline, then repeat birth; existing launch guard retains boot/STOP/deadline. Adopted file must not be a symlink; original full adoption guard checks owner/sequence/instance before exact guardian tuple acceptance. Identity mismatch fails under remote `set -eu`. |
| Deadline |26–30 selects min(30, floor(remaining−60−5)), refuses budget<1; remote uses budget+5 timeout capped by remaining−60. Existing600-second window and device uptime deadline are unchanged. |
| Recovery reserve closed | Initial2df595a left the final child proof at reserve0. Successor aafe5ac2a changes only that call to reserve60; independently checked. Both adoption and final child proof now preserve the60-second reserve. Original600-second window/device deadline remain unchanged. |
| Independent tests |Actual generated local shell wait:4 tests rc0,6.503seconds on the final SHA. Adoption after more than6seconds succeeds; changed birth and foreign cmdline reject at2ticks; absent adoption expires at30simulated ticks rc2. Extracted actual transport run produces timeouts15/35/20. Simulated30ticks are not a real30second device experiment. |
| Original field evidence |Private BASE20/t13-5cd-window-01/apply-readonly rc0 READ_COMPLETE shows guardian11520/b7647948, child31210/b7485570, adopted event76490; adoption-guard-trace rc0 GUARD_OK binds that same instance. Birth76479.48→event76490 is approximately10.52seconds, consistent with the reported~11seconds. Original5-second refusal remains a failed receipt; later adoption does not rewrite it into a successful apply. |

Author fixture results agree with this independent run. No new broad framework, payload, signal path, claim of screen success or crash repair is introduced by this delta.
