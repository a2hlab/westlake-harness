# T10 exact frozen release review

## Evidence and decision

**Exact offline accept** commit `2bd46ecf781be2116863061015b14a6c3a349a58`, pending the separately reviewed t11 classifier and outer's fresh combined production binding. Do not deploy a half-fixed package or infer seal/UI acceptance from this review.

All 26 landing files exist in that immutable Git object. All 23 checkpoint SHA/size entries and the separate Rust-selector SHA match. Watchdog `2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a` is byte-identical to the source independently reviewed at 23:04:58; **zero behavior tests were repeated**.

The earlier independent changed-path replay accepted the original directory and rejected a same-path/mode/copied-owner replacement with exit5, `capture_directory_identity_changed`, preserving its owner. This closes the pre-freeze rejection; it does not add a new identity or retry exception. The historical red evidence remains intact.

## Binding closure

- Checkpoint SHA: `5ce926bfbe05e77e3a5166f512f4c86e6ed2d0b2d1cafd98d1b6137e62920e4b`.
- Entry SHA: `81dd055764b0737f497d1dd9fb8358dd42521360bc6e359c9428c9b2ac8b21a1` pins the exact watchdog and unchanged r3 helper.
- Thirteen boot-member digests resolve to exact Git bytes, including the unchanged r3 worker. Members SHA: `e1c4fb2ba4b757b13c7c695d09438542c8985b36224e36c9d37b7d359eaba233`.
- Startup SHA `0f289cd6b8e280ad10c5e86911087ff9fcc1e0aa28dd07f71622632659854ffa` binds members; expected-startup hash matches. Startup remains disabled/PENDING. Outer must preserve actual configuration when composing the combined t10/t11 package rather than deploying this template.

## Test receipt limits

Author Python6 and Rust3 receipts exit0. The separate author lifecycle attempt exits1 with three skipped scenarios; this is explicitly **not lifecycle PASS**. Its results already identify direct Cargo selectors as the authoritative executed checks. This independent final pass is Git/hash/closure verification and same-byte transfer of our previous negative replay, not a rerun or a new lifecycle claim.

V5 clean-copy closure is accepted by citation to main `34e9018091` and outer's `v5-clean-review-febf975a2fa248079bdf9fe0ce23cafa/report.json`: fresh rebuilt manifest `0c5da8dadaec9e6fc4969d06f884b6204ce5601297f18f76b25fc0407f0d8ab5`, 486 files, eight tests, zero failures/errors, no transaction-matrix rerun. It does not authorize a derived seal or spare-board write.

Exact candidate sources and checkpoint metadata are archived in `.artifacts/t10-2bd4/`; formal small outputs are in the adjacent landing list. No board, VM, remote, signal, candidate edit, permission change, or signature was performed.
