# T31 durable recovery: bounded peer design review

The previous T30 rollback could only use the original holder/start and its 1800-second window. T31 separates a new recovery window from immutable original deployment provenance. This is a read-only review of an in-progress source snapshot, not implementation admission or device verification.

The narrow design is acceptable. Require the actual retained apply transaction, all five original backups and the ABSENT marker, exact known artifact states and metadata, current identity guards, and adjacent per-target CAS. The old executor remains unchanged.

Deployment still requires fresh WID29. Recovery alone permits a different numeric WID when raw run.sh, WMS and parent environment agree and normalization reproduces the exact original template. Do not merge those two rules.

A bounded retry limitation needs an explicit test: with live WID41, recovery restores run.sh to original WID29. If a later step fails before reboot, a second attempt sees run29 versus live41 and correctly refuses. State this fail-closed limitation or narrow the supported recovery scope; do not describe every partial state as automatically retryable. The successor also requires a live parent and host.

See `design-review.json` for exact source snapshot hashes and the suggested minimal adversarial matrix. No host tests, device commands or new REA analysis were run in this review.
