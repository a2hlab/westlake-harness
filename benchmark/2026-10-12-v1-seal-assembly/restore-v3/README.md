# Actual 5cd disabled restoration binding and v3 transaction

The v2 81af19 candidate compiled the real 5cd binding, but its inherited rollback
assumed an existing CFG preimage. The actual target CFG is absent. Directory
cleanup also needed proof that a directory was created by this transaction.
This independent v3 fixes both without changing v2, 257e, b5904 or the exact seal
membership gate. All work here was local; no device, VM or remote calls occurred.

## Actual inputs and compiled package

`binding.5cd.disabled.json` binds the measured target serial and boot
`43bc3915-04bd-42ca-895e-26e8292911fa`, installed host UID 20011300, all 25 target
preimages, and the runtime/stage absence and existing ancestor metadata.
The 25 observations comprise 23 absent controls, the absent preserved old stop,
and the existing HAP prerequisite. The plan has **486 file members**: 23 controls,
460 runtime objects and three stage files; **22 new directories** and six guarded
existing directories. `startup_enabled=false`, compiled `execution_enabled=false`,
and generated `STARTUP_ENABLED=0` all remain disabled.

The final local package is `package-v3-final-disabled/`; its manifest and independent
readback checks are pinned in `evidence/package-verification.json`. Every payload,
plan and executor byte is covered by that package manifest. Intermediate v2 and
v3 compile directories are local diagnostic snapshots, not the final deliverable.
Large payload copies are not in the landing list: regenerate a fresh local output
from the pinned binding, source/CAS inputs and this provider:

```
python3 benchmark/2026-10-12-v1-seal-assembly/restore-v3/toutiao_provider.py \
  --compile \
  --binding benchmark/2026-10-12-v1-seal-assembly/restore-v3/binding.5cd.disabled.json \
  --out /tmp/route-b-v3-new-disabled-package
```

The output must be new. Compilation does not execute a transport. The companion
`deployment.5cd.disabled.json` provides the real self-pin, prepared manifest pin
and all 486 targets, with execution disabled. No matching new seal or authorization
is created: the old exact-SHA gate still rejects incompatible original 61b bytes.

## Source identity and deterministic derivation

The current 61b `restore-runtime-sha/index.json` independently confirms **218/221**
archive hashes, including both WebView JARs and the native libraries, in boot
`ad2ba003-0d0a-43d2-a85d-e023e7702db7`. The remaining three scripts have actual CAS
bytes in `restore-live-scripts/index.json`. `script-derivation-audit.json` proves
that archive -> current donor changes are only the known UID fields and run.sh
WID1443 -> WID33. Deriving from either source gives identical 5cd bytes:

| Script | 5cd fields | Derived SHA |
| --- | --- | --- |
| run.sh | ASX_RUNTIME_OWNER_UID=20011300; WL_PARENT_ID=0 template | 21068754c8e2cd457e943e8a9680d930beca0c3c8316dc62b8a89a81ea05ab37 |
| preseed_metasec48.sh | APP_UID48 default20011300 | 5459b2d0b5cb905fffd875fddc10cc71cf4863a4d4ff7468a6b330ad4ace9fc8 |
| prepare_jit50.sh | app_uid=20011300 | b42a28e7a29a53c162a43ac25eaf52c24906f1afdd179c9414882772ccac34c8 |

The bounded start helper requires the verified live host WID and writes it before
launch. WID33 is never projected to 5cd. The archive/live run.sh directly executes
appspawn-x; the separate integration asx-spawner template is not substituted.

Stage source bytes and metadata are backed by historical 61b alias-transaction
probes080/082/083, bracketed by identical boot001/084 observations. Their normalized
index retains every raw pin and explicitly says **historical donor**, not current
5cd deployment. The request source is donor f871e6..., then LE312/316 become20011300;
final request SHA is `011a16259c7735dcb088fab44f569bc222675855eb722bcf945c48e06c0214ca`.
Stage file metadata remains donor755/root/root for executables,644/root/root for
request, data_local_tmp labels. The new stage root policy is explicitly
755/root/root/data_local_tmp, not the existing parent's771/shell metadata.
New control directory policies and per-file controls inherit the pinned release
policy (including its existing per-target ownership choices), not nonexistent
5cd observations. Runtime mode/label are individually observed; only host UID/GID
are projected. All new runtime state directories are empty, never donor data copies.

## Transaction corrections

- Absent-before CFG: guarded candidate/observed-partial SHA removal under the
  existing root remount/restore trap; readback must prove absence. Existing-before
  CFG retains the original inert-quarantine behavior. The success state accurately
  distinguishes restored absence from quarantine.
- Directory creation: per-directory intent precedes creation; ownership is recorded
  only after mode/UID/GID/label and `dev:inode` readback. Cleanup compares that exact
  identity. Same-path replacement directories are not owned, even with equal metadata.
- Before any file-placement intent, rollback cleans all verified new directories,
  including a first-directory failure path. After file placement, explicit audit/
  stop control directories remain retained; runtime/stage cleanup is empty-only.
- Unknown, nonempty, replaced or partially initialized directories are retained.
  Cleanup returns nonzero and writes a partial receipt, never a new success receipt.
  Retry uses the same transaction and rechecks backups/objects. The code neither
  removes user data nor resolves ambiguous ownership by guessing.

## Verification and outstanding admission

`test_restore_v3.py` deep-copies the actual disabled binding into a temporary
recording-transport test. Only temporary startup authorization is enabled; all486
members,22 directories, real metadata, real source bytes and absent CFG are retained.
It calls the actual derived executor through standard provider argv. Cases cover
full apply/rollback; first mkdir failure; post-mkdir metadata and readback failure;
known nonempty data; partial send; unknown same-metadata directory; and replacement
inode. Test data removal/migration is performed only by the isolated fixture,
never by the provider. The real binding hash is checked unchanged afterward.

No deterministic byte/metadata input remains missing for this disabled compilation.
Execution admission is still pending: BMS review of new directory/control creation
policies, the complete derived final-SHA seal, a fresh target identity/absence check,
and independent authorization/lock. t0's new guardian is a separate evolving input;
this package truthfully uses the pinned historical alias/executor lineage. It does
not claim that guardian integrated or any actual 5cd restoration succeeded.
