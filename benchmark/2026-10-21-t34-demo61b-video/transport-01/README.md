# T34 exact-payload file transport

W-01 command00189 had a 76,139-byte shell argument. `swap.sh` is 76,038 bytes,
SHA `f8c0896fcb3c3405ba977853ee71af51a1bb223baa881442fd74e9f4f6b60ca6`.
The process returned 0 with empty stdout/stderr and no remote marker. This proves
missing execution evidence, **not** a specific HDC length limit or zero writes.
W-01 is retained and closed separately; this adapter is for a new reviewed window.

`file_transport.py` loads only executor d75ecd and bms_batch f41efa. It changes
`Board.raw_shell` in that single process, restoring the method in `finally`.
Arguments of at most 32,768 bytes take the original path. Longer command bodies
are saved without byte changes, sent once with existing `Board.send`, SHA-checked,
and invoked through a short `/system/bin/sh -eu FILE` command. The original
`raw_shell` adds and verifies the remote status marker. 32KiB is a conservative
transport threshold; the actual HDC limit remains unknown.

The exact executor still performs all admission/source checks, live/physical guards,
five backups plus absence marker, CAS, same-directory rename and result writing.
The adapter uses the same holder/start/boot and monotonic remaining budget, reserving
600 seconds for non-rollback operations. Every transport phase calls the executor's
exact `ready()` checks. No write is automatically retried, including a lost marker.
Its sibling `<out>.transport` retains payload bytes/SHA and attempted/unknown status.
Transport staging is a device write performed only by cc-video in the new window.

Seven tests passed with real local 76KB-plus shell payload execution (rc0 and rc37),
fault-injected lost marker, send/SHA failure, expired/foreign object refusal and
short-command bypass. No HDC or device test was performed by the author.

## W-02 use

After peer acceptance, use **new** actual holder/start/admission, output directories
and original W-02 apply plan. Recheck baseline/compat absence; do not replay W-01.
The original `COMMANDS.md` arguments are unchanged; prepend this adapter:

```sh
python3 "$T/file_transport.py" --executor "$D/executor61b.py" -- apply --execute \
  --repo "$MAIN" --data "$W/data" --inputs "$INPUTS" --hdc "$HDC" \
  --boot "$BOOT" --parent "$PARENT" --birth "$PARENT_BIRTH" \
  --holder "$HOLDER" --start "$START" --admission "$W/admission.json" \
  --out "$W/apply"
```

`T` is this landed `transport-01` directory; `D` is the unchanged deployment
directory. Preflight can use the same prefix. Recovery **also uses this prefix**,
because its rendered script may exceed the same length:

```sh
python3 "$T/file_transport.py" --executor "$D/executor61b.py" -- rollback --execute \
  --recovery-no-parent --repo "$MAIN" --data "$W/data" --inputs "$INPUTS" --hdc "$HDC" \
  --boot "$CURRENT_BOOT" --holder "$HOLDER" --start "$START" \
  --apply-plan "$W/apply/plan.json" --origin-admission "$W/admission.json" \
  --admission "$W/rollback-admission.json" --out "$W/rollback-01"
```

Normal live-parent rollback retains its original arguments instead. On any transport
failure preserve receipts, determine actual six-state/backup state, and obtain the
next recovery decision; never rerun an unknown write automatically.

Reusable source references: `bms_batch.py:412–439` already refuses write replay on
lost markers; `:471–476` implements file-send. Existing Boat interaction runner
`benchmark/2026-10-09-demo-boatattack/v2-20261013/interaction/interaction_runner.py:117–118`
uses send → SHA readback → short `sh FILE`. This adapter keeps T34 transaction
semantics and does not import the Boat background/nohup policy.
