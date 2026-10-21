# T34-R3-CHAIN-AUDIT (2026-10-21, octoscode lane)

Read-only mechanical audit of `benchmark/2026-10-21-t34-guardian-inputs/`. Actually executed checks (this lane, this round; full machine-readable detail incl. real 64-hex SHAs in `AUDIT.json`):

## What was verified — all PASS

1. **INPUTS.sha256.json rehash**: 28/28 entries match (22 payload files + CHAIN.json + MANIFEST.sha256 + generation.json + 3 deploy-cfg files).
2. **MANIFEST.sha256 vs payload**: 22/22 entries, all match files on disk; no extra, no missing.
3. **members.tsv**: 16 rows, all SHA match payload bytes; modes 550 ×15, 440 ×1 (`decoder-probe.jpeg`); tsv SHA map is consistent with MANIFEST. (6 payload files are intentionally not tsv rows: boot-entry.sh, members.tsv itself, recovery.cfg, rollback-inert.cfg, startup.env, startup.expected.sha256.)
4. **entry.sh referenced SHAs**: pinned `watchdog.sh` ✅ and `route-b-owner.sh` ✅; decoder pair `screen-gate` == STARTUP_DECODER_SHA ✅, `decoder-probe.jpeg` == STARTUP_PROBE_SHA ✅.
5. **startup.env chain**: `startup.expected.sha256` content == SHA-256(startup.env) ✅; `STARTUP_MEMBERS_SHA` == SHA-256(members.tsv) ✅; CHAIN `cascade.members_sha_in_startup_env` and `cascade.startup_expected_eq_sha_startup_env` both consistent ✅. `STARTUP_START_PARENT_SHA` resolves to payload `real-start-parent-bounded.sh` ✅.
6. **generation.json cross-check**: `members_tsv_sha256`, `startup_env_sha256`, `startup_expected`, `candidate_watchdog_sha256` all match recomputed values ✅; payload_files=22, members=16, device_calls=0.
7. **ROOT correctness**: `/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3` confirmed in config-common.sh, CHAIN `new_root`, and generator argv; **zero** occurrences of old r2 root in any payload file. (entry.sh/startup.env/boot-entry.sh derive root via config-common.sh/`$HERE` rather than hardcoding — consistent, not an error.)
8. **deploy-cfg**: `cfg.diff` and byte comparison agree — exactly one line (19) changed: `icon-manual-20261019-r2/boot-entry.sh` → `icon-manual-20261021-r3/boot-entry.sh`; before/after file SHAs match CHAIN `live_init_cfg` pins; after-cfg SHA-256 begins `7b9f2c0e` (full value in AUDIT.json) ✅.

## Authorization scope (as required)

`STARTUP_APPROVED_BY=outer(codex)` / `STARTUP_ENABLED=1` are **content authorization only**, not device admission — consistent with CHAIN status `DEPLOY_PACKAGE_PREPARED_NOT_ADMITTED` and `device_writes=0`. Not treated as a device signature.

## Unknown / not verifiable offline

- `STARTUP_OLD_STOP_SHA`, `STARTUP_JIT_SHA`, `STARTUP_NAMESPACE_SHA`, `STARTUP_HOST_SPAWN_SHA`, `STARTUP_REQUEST_SHA` pin live-device/runtime artifacts (config-common.sh L25–33: historical stop file + exported AUTH_* runtime values) — no payload file matches them; **unknown** by design in this offline package.
- Live-device state and `$T34_RETIRE_PRIVATE` raw generator receipts: not in package, not verified.

Counts: payload 22, inputs listed 28, verified 28, manifest 22, members 16, entry pins verified 4, cfg diff lines 1.
