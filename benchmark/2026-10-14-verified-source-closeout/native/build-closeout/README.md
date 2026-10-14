# Native producer build closeout — SOURCE-CLOSEOUT

## Evidence first

The earlier two restore failures were not compiler failures, and inventories were not proof of a build. The new hw248 attempt `20261014T102137Z` actually restored, compiled and strictly linked: **restore 0 / compile 0 / link 0 / runner 0**. The returned ELF independently hashes to **0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c**, **504984 bytes**, exactly the frozen REG-002/FZ-002 provider. This is a new exact rebuild, not recovery of a missing historical production log.

`evidence/outer-run.stdout` and `outer-run.stderr.txt` preserve the new execution streams byte-for-byte. The original outer rc/request/persistence files lack a final newline: their readable copies add one display newline, and adjacent `.raw.b64` files preserve exact original bytes; both identities are pinned separately. `evidence/provider/result.json` preserves the actual 51-argument compile and 54-argument link commands, tool hashes, empty compiler/linker stdout and stderr hashes and source overlay. The archive's step streams and rc copies are byte-identical. `evidence-index.json` pins every returned archive file, including the actual ELF and object, and every public copy.

The build compiles the delivered BIGSTACK `child_main_after_stock.cpp` (SHA `3fc2060ea0f705cce50555caa509b215ea64edc343a714b20c438dba505b61d8`) into a freshly restored private generation, then links locked original objects/dependencies. It does **not** rebuild all ART/OH/generation objects from source. Frozen clang15 is `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`; ld.lld is `8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4`.

## Durable returned evidence

- Local: `$WORKSPACES/_verified-source-closeout-20261014/root-hw-native/20261014T102137Z-evidence.tar.gz`.
- Remote: hw248 `/home/alvin/verified-source-closeout-native-20261014/root-20261014T102137Z/evidence.tar.gz`.
- Archive: **9a68bba7572be2f75ff6af5a7d031389189ef41219c16c2150f0ee19acfb1184**, **4256298 bytes**. Local SHA/size verified; remote equality is attributed to the outer persistence receipt, not a new inner SSH claim.
- Large 80477-target generation / 2648-target external inventories and the output ELF/object remain inside that archive. No large binary is added to Git.

Restore verified 2648 duplicates, with zero external overwrites/new targets. Its `build_executed:false` describes the restore phase only; the following provider receipt records the actual successful compile/link. `whole_generation_complete:false` and `historical_production_proven:false` are retained exactly. Two original B67 `v1-tests` links remain unresolved and were not consumed by this provider.

## Verify locally; rebuild entry already delivered

```sh
python3 benchmark/2026-10-14-verified-source-closeout/native/build-closeout/verify_build.py \
  --archive "$WORKSPACES/_verified-source-closeout-20261014/root-hw-native/20261014T102137Z-evidence.tar.gz"
```

The verifier checks the archive, all member hashes, raw/public copies, actual ELF bytes, rc values, two successful steps, and both prior frozen manifests plus 296 source/recipe/evidence members. It does not access a board or network. Fresh output is retained in `evidence/verification.stdout`, `verification.stderr.txt` and `verification.rc`: **16 archive files / 296 unchanged frozen members, rc0**. An unpinned archive is rejected with rc1 (`evidence/negative.stdout`); the active verifier user-path check has 0 violations. These are receipt-verification checks, not another remote build or device test.

For another authorized fresh build, use the unchanged delivered recipe, with explicit `LAB_HOME` rather than SSH root's `$HOME`:

```sh
export LAB_HOME=/home/alvin
bash \
  sources/api-implementations/shared-native-production/revisions/archive-merge-r2/execute-hw248-r2.sh \
  "$LAB_HOME/verified-source-closeout-native-20261014/FRESH_ATTEMPT"
```

The attempt path must not exist. Acquiring the two archives and tools uses the existing SHA-locked dependency recipe; no new dependencies or frozen expectations are introduced. The exact successful outer invocation is preserved in `evidence/outer-request.json`.

## Historical failures and remaining producers

`results.json` independently pins all three earlier attempt stdout/stderr/rc/request files in the persistent root directory. Preserve rc2 unexpected archive layout, rc2 exact duplicate rejection, and rc1 `LAB_HOME=/root` lookup failure. They are not overwritten by this success. The Mac Linux-clang `Exec format error` remains a separate earlier result.

The parent freeze `503f3acc…` and archive-merge-r2 freeze `c56649c6…` are unchanged, including their then-current pending reports. `atlas-amendments.json` updates only the REG-002/FZ-002 new-build status. FZ001 still lacks a newly executed full original BMS producer; FZ003 retains incomplete generation acquisition and original fixed-path recipe limitations. Bridge8ab and original libandroid9cc producing-source bindings remain unproven. The existing ADC 49-byte binary replay is not relabelled as C++ source closure; the unrelated `0d7b` runtime log is not reused.

No API behavior, signed artifact, device verdict, source freeze or gate is changed. Newly predicted first-fatal keys moved: **0**. This small additive landing contains no new remote or device execution.
