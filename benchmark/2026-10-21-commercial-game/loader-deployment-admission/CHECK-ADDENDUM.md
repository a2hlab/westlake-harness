# G19 executable-check addendum

The first 87-path delivery omitted the contract's Rust selector and had no persistent reproduction of validation.json. This increment supplies both; the earlier handoff was incomplete on that criterion.

Run from any directory:

```sh
python3 /path/to/repo/benchmark/2026-10-21-commercial-game/loader-deployment-admission/check.py
```

Or from the repository root:

```sh
cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test commercial_game_loader_deployment_admission commercial_game_loader_deployment_admission -- --exact --nocapture
```

Both commands were executed with rc=0. The Rust selector passed 1/1; it invokes the same persistent checker. The positive archived admission passed and all six mutations were rejected: missing alias, old boot plus fake ready, old boot alone, fake ready alone, candidate SHA drift, and mount-source drift. The combined boot/ready case requires both rejection reasons, so one condition cannot mask the other.

The checker verifies archived source-index hashes, command-stream hashes/rc, both loader aliases and observed mount roots, baseline/candidate artifact receipt pins, native manifest source pins, all four archived before/after boot observations, and the undeployed status. `--admission PATH` accepts another admission JSON for independent negative reproduction. It reads no device/private receipt, imports no deployment source, and needs no sibling worktree or large binary. Fresh means the archived G19 observation, not a new window authorization. The 285-target observation remains explicitly attributed to outer; no G20 work is repeated.

`validation.json` now contains actual checker output rather than a manually asserted PASS. `check-01/commands.json` records argv, UTC times, rc and original/portable stream hashes; raw output is in the adjacent stdout/stderr files, with only local path prefixes normalized. This is evidence validation, not a U7 preflight, deployment approval or game acceptance.

Apply `landing-increment-01.txt` on top of the original 87-path delivery. The original landing list stays unchanged; the replacement `SHA256SUMS` refreshes the original entries, including validation.json. `SHA256SUMS-increment-01` binds the added and changed payloads plus the Rust bridge using repository-relative paths. No author source, device, G20 files, previous T37/T38 pins or git state was changed.
