# Exact-seal restoration versus spare realization

## Evidence first

**A 61b seal cannot be restored to UID20011300 by changing only its serial.**
There is no current canonical/template or per-board realization mechanism in
the exact-seal toolchain. This is an integration blocker, not a transport issue.

- `benchmark/2026-10-09-demo-baseline/t5/restore.py:60`: target coverage must
  equal every sealed file and APK; at line 67 every source SHA must equal the
  sealed SHA. At line 249 the rehearsal projection changes **only serial**.
- `restore.py:210`: the final selfcheck must pass against that same effective
  seal. A derived script cannot be accepted merely because its provider exited 0.
- Frozen `toutiao_provider.py` additionally requires every compiled plan member
  to appear with its exact SHA in the seal. Its new controls cannot simply be
  omitted from `seal.files.overlays` to avoid the mismatch.
- `build_seal.py:137` compares observed overlay bytes to the exact declared
  overlay map. `scripts/lab/demo_selfcheck.sh` uses SHA comparisons, not a
  canonical template digest.

Current material is not a completed 61b seal: the v1 execution README says
not sealed; `t5/overlay-inputs.json` still has a pending Route B slot and empty
files. The 319-member `archive-1950` and 221-member `runtime-archive-2016` have
zero new recovery-control entries. The runtime archive does contain `run.sh`;
the 257e compiler derives its UID/path/WID fields. A future accepted inventory
must explicitly add the controls and actual final derived bytes.

The older `boot-slot-uid-dynamic` branch excludes six reconciled files from
its own `immutable.tsv` and checks their fields during reconciliation. That
is **not** an exception in `build_seal`, `restore.validate` or demo selfcheck.
It cannot be imported implicitly to exempt these files from exact-seal checks.

## Smallest explicit integration choice

Preserve the original seal and all exact-SHA gates. Add a separately approved
**spare realization** binding, not a falsely serial-projected or signed 5cd seal:

1. Bind the origin 61b seal SHA, target serial, measured installed UID, profile,
   current placement boot, compiler SHA and all derivation input SHAs.
2. Enumerate every permitted old target/SHA to new target/SHA transformation.
   UID, `STARTUP_SERIAL`, attempt root and the coupled manifests are explicit.
   Keep unchanged U13/APK bytes exact; reject unrelated differences.
3. Outer reviews the deterministic effective 5cd file map and authorizes that
   specific realization. Independently pin both origin and effective documents.
4. Validation and post-replay selfcheck use the exact effective map. The final
   report names origin SHA, realization SHA and actual checked target map.
5. Call the outcome **derived-spare-realization / equivalence rehearsal**,
   never original-61b byte-identical restoration or a new signed seal.

The existing CLI has no such path. An explicit realization admission/dispatch
seam and negative tests are required: wrong origin, unauthorized UID/target,
extra changed byte, missing transformed member and changed effective map must
all reject before writes. No fuzzy template match or global SHA relaxation.

Alternatively, execute only the independent Route B derivative transaction
under its separately approved ticket, and explicitly leave the original exact
seal rehearsal blocked. Neither choice is authorized by this review. The outer
owner must select the intended acceptance claim before any spare-board write.

## Scope

Read-only local analysis. No seal, approval, provider or contract was modified;
no board, VM or remote command ran. cx-seal now owns the new compiler revision;
the 257e and b5904 conclusions remain tied to those historical frozen bytes.
