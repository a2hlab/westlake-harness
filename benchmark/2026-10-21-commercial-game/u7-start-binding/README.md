# G22: bind U7 start to the verified manifest

The unmodified U7 DeviceIO inherited Deployment.start without initializing `self.a` or `self.m`. Calling that exact inherited method raised `AttributeError` before any transport call. `evidence/reproduce.stderr.txt` preserves the original failure. Lane and main U7 sources were byte-identical (`53dcbc9b7cb6bdf41e54d11d5fff4d0992d33dedda6fed25701135fad3c164c0`); no main-to-lane replacement was necessary.

The only production edit is `scripts/lab/u7_executor.py`. A successful existing candidate ticket check binds the candidate package; a successful restore check binds the baseline package. This explicit choice handles identical host SHA with different manifest label targets. Binding verifies the package path, ticket manifest SHA and effective host identity. Before delegation, start rechecks the original gate ticket, disk manifest and in-memory manifest identity. Failed revalidation clears the prior context. Unbound start refuses without issuing any command; readonly DeviceIO construction remains supported.

The wrapper then calls the unchanged `Deployment.start`, which still invokes the unchanged label recipe before `begetctl start_service`, followed by the original parent SHA and socket checks. No label bypass is enabled. Transaction.apply, automatic failure rollback, explicit journal rollback and post-reboot baseline replay retain their existing state-machine calls; their existing ticket/restore checks select the correct context. No device, runtime build, G14/T38 work or deployment was performed.

## Actual offline verification

- Original inherited start reproduction: rc1 with missing `a`, no transport invoked.
- New regression: 10 tests passed. Apply, failed apply rollback, explicit rollback and baseline replay execute the real DeviceIO wrapper, real inherited start and real `apply_recipe`. Native approval itself is stubbed; original ticket hashing is real. Existing memory transport and label-shell fixtures are reused, so no hdc/orb/device shell command is sent.
- Rejection cases include missing binding; changed disk manifest, payload, sidecar or in-memory manifest; wrong host; mismatched ticket package/manifest; failed candidate/restore revalidation; and label audit failure. Each refuses before service start, and pre-start identity failures issue no shell command.
- Original U7 Python suite: 30 tests passed. Original Rust `u7_executor`: 7 passed. Original label recipe suite: 19 Python cases via its Rust target, passed. New Rust target: 1 passed. All three recorded check commands returned zero.
- The first new-test attempt failed on Python 3.9's absent `unittest.TestCase.enterContext`; its source snapshot and raw failure are retained privately. Using `contextlib.ExitStack` fixed the harness, without changing production behavior to satisfy that failure.

`run_checks.py` writes argv, stdout and stderr into a fresh persistent directory before running. `source.diff` is the exact production delta; `source-before.json` and `results.json` pin pre/post images. `evidence-index.json` records original private SHA/size and sanitized public copies. Path substitutions are explicit; originals are unchanged. Historical U7 board-evidence test output is historical evidence only, not a new device run.

`landing-paths.txt` is the fixed handoff; shared Git/board writes were not retried. The G21 outer holder must perform a new original preflight with the landed tool binding before any future window. This card changes neither G21 authorization nor native approvals.
