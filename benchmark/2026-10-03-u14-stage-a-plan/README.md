# U14 Stage A disabled plans on retained U13

The previous preparation used unarmed U13 metadata. This packet binds the
actual retained bases: common `2abe4a49`, 61b `0a31ad35`. It does not borrow a
T8 restoration target or claim the U14 production gate passed. cx-bms's fresh
armed-BASE replay selects U14 `12d30eb0` / `b0f74132`, native manifest
`3460435a`, inputs `11001e6e`. Both executors still return 2: required G2
has no executable oatdump. Outer production replay and admission are pending.

## Accepted inputs and coverage

The key-table source is master `07066b4e05`, oc-t4 v4 (`c5ec9c4b...`).
The 107 unique lit-regression keys, six registry-evidenced lottery keys and
13 lit movers are disjoint and cover exactly the 126 signed U14 reference
keys on their reference boards. Movers and lottery trials count as their
protection runs. Every key occurs in exactly one shard category.
Each lottery key has six consecutive single-key shards; white-window keys
without signed flaky evidence have one observation, not an invented k/n.

| Board | Runs | Protected unique keys | Restored runtime | Restored boot |
|---|---:|---:|---|---|
| 5ea | 54 | 42 | 821de739cf81 | ee927db88a67 |
| 5cd | 57 | 39 | 821de739cf81 | ee927db88a67 |
| 61b | 58 | 45 | 452447a4a0ba | ee927db88a67 |

Priority preserves the accepted table: movers, white-watch, lottery, then
lit-regression. One key per shard makes continuation exact across both
original and corpus-v2 manifests. Future windows run only unfinished trials
on the same board and bytes, with fresh output directories. The table's
three-window estimate is not an execution promise: no new key starts after
minute 35 and each window stops by minute 45. Unmeasured keys remain unknown.

## Safety and production wiring slots

Every plan has `execution_enabled=false`. board_run rejects before taking a
lock; the apply/finish draft guard additionally exits 78 without any device
imports. Smoke slots are explicitly incomplete. **Do not flip one boolean**:
replace the guard only after reviewed transaction wiring, candidate identity,
live markers/probe.files, fresh Mac+VM G2 and exact outer admission are ready.
No candidate was armed, no lock acquired and no device command issued here.

The restore snapshots are the retained StageB **321 assertions / 319 unique
paths**, with per-board installation-chain bytes preserved. Future finish
must unconditionally restore **U13**, verify those SHA identities and both
fingerprints, run fresh HW/ZZ recovery smoke and a final identity check before
unlocking. A failed recovery retains the lock. OrganicMaps UID drain/retry
must remain wired; don't change installer bytes or restart foundation.

Per-shard crypto observation reuses the landed U13 schema2 assessment hook.
It records and ACKs `selftest_error`, `badtag`, `probe_error`, and unknown without
stopping Stage A for the crypto verdict. All three failure classes veto
promotion; only unknown can receive exact individual outer explanations.
Visual verdicts require outer t20 review, never alive/READY alone. Confirmed
regressions allowed: zero. Six lottery keys retain their full signed k/n.

Before any future lock: record vmgr RSS and orb latency; preventive OrbStack
restart above 3 GiB only with all boards unlocked and no VM jobs. Run fresh
Mac+VM production gates and orb/HDC/bind/tool preflight; verify signed U13
baseline bytes rather than inode and stop receipt-owned stale children.
Record the same infrastructure metrics after recovery.

## Rebuild and checks (offline only)

```sh
python3 benchmark/2026-10-03-u14-stage-a-plan/build_plans.py
python3 -m unittest discover -s benchmark/2026-10-03-u14-stage-a-plan -p test_plans.py -v
```

`inputs/bindings.json` records selected persistent package paths/full SHAs.
`inputs/recovery-*.json` are the retained U13 identities, not historical T8
baselines. Small copies are review inputs; big candidate/base packages remain
at their recorded westlake-inputs and cx-bms persistent paths. Gates run by
this packet validate plan bindings and refusal only, not G2 or on-board UI.

Verification: Mac7/7 PASS; VM unit replay did not reach Python because OrbStack
reported `sconrpc ready event fired but socket was not connectible`. A separate
12-second `orb -m a2hlab true` readiness probe timed out. No VM PASS is claimed;
no VM restart, board command or lock was attempted. Rerun after infrastructure
recovery, independently of outer G2 replay.

V4 refresh: adopted master07066b4e05, key JSON full SHA
`c5ec9c4bf9f2deb24bdd31d527f6817bd3fd1e44bacd7f63aad4e8164f9c036b`.
The added mover/regression overlap test rejects the v3 duplication. Mac7/7
PASS; fresh VM v4 replay timed out after25s without established test completion.
The earlier VM infrastructure evidence is preserved separately.

After outer restored OrbStack at10:04, the fresh VM v4 unit replay passed
7/7, exit0 in0.442s (`evidence/test-vm-v4-recovered.txt`). Earlier failures
remain historical evidence. Outer reports both Mac production variants
G1/G2 true and executor rc0; outer VM production replay and window authorization
remain separate from this unit-test result. Plans remain disabled.
