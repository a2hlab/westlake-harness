# Seal persistence handoff — local inventory complete

Previously wrong: a local CAS pathname or `archive` filename alone does not
prove off-machine persistence. No device, network, copy of large objects or
upload was performed by this lane.

## Verified local evidence

- Final source map **811/811** and Route B **487/487** match actual local SHA256.
- Source bytes: **757 unique objects / 1,215,922,955 bytes**.
- Current raw/code supplement: **17,972 files / 58,538,595 bytes**;
  combined inventory **18,729 files / 1,274,461,550 uncompressed bytes**.
- Actual r2 has **3,539 raw stdout/stderr/JSON triples + 487 placed receipts**,
  `transaction.json`, admissions and execution log. Red attempts remain separate.
- r4b directory transaction/transport/history receipts and both complete live
  selfcheck raw directories are included. Two reports say `live-readonly PASS`,
  **940 checks**, zero writes/locks; this is not an independent UI signature.
- Generated duplicate runtime bundles were excluded. The full `pack-files.csv`
  and path lists remain private local artifacts and **are not in this landing**.

## Existing remote large artifacts

`hw248:/home/alvin/westlake-t2c-runtime187-repro-20261010T1333/complete-v2/`
contains `runtime187-inputs.tar.gz` (SHA `ba5906c6…`, 465,446,236 bytes),
`cold-runs-final.tar.gz` (`63518fb4…`, 6,130,463 bytes), `input-inventory.json`
and `archive-receipt.json`. Full pins are in main
`benchmark/2026-10-10-adapter-buildchain/runtime-persistence.json`.
This lane verified local copies; **outer reports all four remote SHAs freshly
rechecked equal**. No resend of those large objects is required.

Installer51e1 historical kit location:
`hw248:/home/alvin/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz`,
SHA `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6`.
This location is recorded provenance, not a fresh remote check by this lane.
Historical bridge exact-source gaps remain; runtime187's archive is not credited
to unrelated bridge/RouteB runtime binaries.

## Outer archive handoff

Outer used this inventory and added all RUN evidence, final booklet/games/API
and two historical128 references. Outer reports **78,823 files / 32,928 distinct
contents / archive 725,732,814 bytes**, SHA
`359fd39ebef533acdbf9fe49f81e93c9cea47541798ff45b73a7a3bb5cfc9242`.
**Upload to hw248 is in progress, not yet remote-durable PASS.** Final handoff
needs only the destination path and successful remote SHA/readback receipt.
Do not confuse archive size with this inventory's uncompressed byte totals.

`results.json` records these scopes and provenance; `inventory.stdout` and
`inventory.stderr` preserve local rc0 evidence. `landing-paths.txt` is small;
no large CSV/list, raw board data, CAS payload or new framework enters Git.
