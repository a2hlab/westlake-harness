# 61b v1 seal rollback field: narrow static confirmation

## Verdict

**The existing reviewed 61b entry is sufficient for a scoped, not-yet-exercised
rollback field**, provided the final card pins its complete local recovery
closure below. Do not substitute the 5cd executor or describe complete runtime
removal. No board experiment or rollback was run by this review.

The precise meaning is **cooperatively stop recovery, restore 23 non-init
control targets, quarantine the one init CFG**; all 24 targets are in scope,
but the unsafe init preimage is deliberately not re-enabled. The 460 runtime
and three stage targets are inherited data retained read-only, not transaction
members and not deleted. Apps/user data are retained; no signals are sent.

## Actual immutable bindings checked

Root is `$WORKSPACES/westlake-harness/benchmark/2026-10-12-v1-seal-execution`.

| Object | SHA256 |
|---|---|
| capture-feed-package/executor.py | `430fbf4a6348dc12ef107c4786a16de83c06a99330cd527c5dbbbc6aca44f30a` |
| capture-feed-package/plan.enabled.json | `20acc9ac00a48bf928aa57b519f1b255fe19ee013b21c3fa0e0d12c18ab644e7` |
| capture-feed-transaction/transaction.json | `0173323800cd3e149a50e1411d40c7720a08ac35bcb39617ae568cbbc01d50ce` |
| capture-feed-package/payload/rollback-inert.cfg | `826cb3640248cc2b5c55d82e0efdbdde94843958308649ac461570d8a6191dd3` |

All **24/24** physical backup objects match their before SHA, and transaction
backup rows exactly equal the signed plan projection. All 24 beforeimages exist.
Serial is **61b0657200000000000000000324012c**; transaction origin boot is
**52533d3f-e49c-451e-a632-4902d77ffcb0**. The eight changed targets are entry,
three watchdog aliases, classifier, members, startup and startup.expected.
The runtime run.sh is not a rollback member, so the 5cd 487-member WID rollback
limit does not apply to this 24-control restoration.

## Minimum field completion

- Pin the executor **and** plan, transaction, inert CFG and 24 backup SHA table;
  retain the already-pinned package/tool dependencies needed by executor.validate.
  A lone executor path is not a complete executable recovery recipe. A small
  rollback index may carry these pins without changing any original file.
- Record `scope=61b-controls-24-init-quarantine`, `runtime_stage_action=retain`,
  `board_exercised=false` and pending current-boot authorization. Do not use a
  successful candidate/apply receipt as a successful rollback receipt.
- At execution only, obtain a fresh independently pinned outer authorization
  for current kernel boot/expiry, preserving origin52533/plan20acc9/serial61b
  and the original exact action set; hold the exclusive board lock. Do not
  reuse old boot tickets or the 5cd496fa plan, and do not fabricate one now.
- The reviewed rollback first verifies all backups/current targets, then checks
  guardian exact NUL argv, birth, UID and boot before cooperative stop. Foreign
  bytes, wrong owner or failed stop reject and retain evidence, not force repair.
  Expected terminal success is ROLLED_BACK_CONTROLS_BOOT_TRIGGER_QUARANTINED.
  NO_MEMBER_CHANGES_NO_DONOR_RESTART is a no-op, not proof of stopped recovery.
- Read back init isolation and RO root after any future authorized rollback.
  Legacy remount is not the newly fixed BASE5 function; a remount/error receipt
  does not authorize guessing system state. Retain original raw statuses.

## Source field

The proposed route-b-source.json must pin each of the **487** actual unique
targets to CAS content/provenance, not just a count. Its current run.sh complete
SHA must be backed by independent same-boot WMS/proc evidence for the single WID
assignment; this is not a file-derived WID assertion. Keep origin-template,
realization-generator and exact target SHA pins, including UID/GID and binary
request fields. The new index itself needs a final SHA on the card. It is a
source/realization inventory, not a claim that 487 targets were newly deployed
by this 24-control transaction. APK identity is separately bound by the existing
toutiao-apk-identity.json (13.9.0/13900/a1112a0c…); no new APK experiment is needed.

## Exact future rollback invocation (outer only, not executed)

```sh
python3 "$RUN/capture-feed-package/executor.py" \
  --plan "$RUN/capture-feed-package/plan.enabled.json" --execute \
  --authorization "$FRESH_61B_ROLLBACK_AUTH" \
  --authorization-sha256 "$FRESH_61B_ROLLBACK_AUTH_SHA" \
  --out "$RUN/capture-feed-transaction" --action rollback
```

This field can be filled now with the static reviewed pins and explicit
not-exercised status. A claim of actual rollback PASS still requires the future
original transaction receipt, strict readback and separate outer review.
