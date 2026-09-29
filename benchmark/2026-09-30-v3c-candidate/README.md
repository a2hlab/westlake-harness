# v3c candidate: offline assembly, not board validated

The previous B92/B93 package names were insufficient descriptions of live state:
B87's original host would remove the current GID 3003 fix, B92 retained old
Android aliases beside updated route libraries, and the newer-named B93 bundle's
`2-html` package still contained the older TLS library. This assembly pins bytes
individually, keeps **liblog 8c81a937 / CE runtime 9e14bf20 / host d977bd15**, and
checks every declared live hash against its effective mount source.

The latest handoff selects **TLS 39c2cfe9** and **gapfill d1a1961d**. HTML is
**excluded from the payload**, following the outer pause/removal after the new
SIGSEGV. Loader **76092855** and the native-provider fallback are excluded;
**fde6f31c** remains. This is the Java namespace route, with no JAR change here.

## Contents and identity

- `candidate/`: complete local package, copied from `westlake-generation-b87-vt-c835a93e`;
  the generation/Route-A receipt remains 74d1d6d4, while the package manifest
  identifies the new composition. See `results.json` for its full SHA-256.
- `inputs.json`, `artifacts.csv`: 11 selected artifacts, full SHA-256, source
  paths/commits, source snapshots and build-recipe hashes; three frozen resident
  manifests and run fingerprints. Only 10 of these artifacts change from B87;
  liblog is intentionally retained.
- `candidate-package.json`: reviewable copy of the final manifest; ANL/provider
  each have identical route and Android payload bytes and live hashes.
- `board-deltas.csv`, `results.json`: per-board path changes and migration limits.
- `elf-audit.json`, `evidence/elf-*.txt`: read-only AArch64 ELF checks. New TLS and
  gapfill both export JNI_OnLoad, have **zero strong undefined `_Z*`/`__cxa_*`
  symbols**, and need only `libc.so`. This is not evidence of successful loading.
- `evidence/b87-build-archive.json`: existing persistent source/toolchain archive
  for retained liblog and the VT/SQLite runtime lineage. Original package receipts
  remain historical evidence; they do not validate the newly combined package.

The requested sibling output directory is outside this session's writable roots.
The complete package is staged under this worktree; no external directory or git
metadata was written. The outer reviewer can copy it after review, without rebuild:

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-harness-bms/benchmark/2026-09-30-v3c-candidate/export_candidate.py --out /Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate
```

The helper refuses an existing destination, verifies the package before and after
copying, and includes this report and tools under `handoff/`. Only
`candidate/` is the current candidate; `candidate-*`/`work*` are ignored local
intermediates, never rollout inputs.

## Run offline checks

From the worktree root:

```sh
python3 benchmark/2026-09-30-v3c-candidate/test_candidate.py
python3 benchmark/2026-09-30-v3c-candidate/check_elf.py
agent-spec lifecycle specs/bms-v3c-assembly/t1-assemble.spec.md --code tools/spec-checks --format json
```

Exact three-board dry-run commands and outputs are in
`evidence/dry-run-{5ea,5cd,61b}.json`; all passed, all report `device_io: false`.
They invoke the unmodified, hashed `tools/deploy_generation.py --dry-run`.
`assemble.py` uses the unmodified `prepare_generation_replacement.prepare` for
10 ordinary composition steps, then explicitly normalizes aliases in the final
package. These are **offline composition steps, not an executable rollout chain**.
It refuses an existing output/work directory. `freeze_inputs.py` is for a new
reviewed input revision; do not rerun it to silently overwrite this frozen set.

## Three-board migration assessment

The table freezes recorded snapshots selected at 02:32 +0800, not boards queried
by this task. 5ea is the newer `outer-tls39c-r17e` snapshot (TLS39c already loaded);
5cd is `r17c-all-5cd`, and 61b is the accepted CE/gapfill/r17b run. Full
fingerprints and their raw-file hashes are separate fields in `results.json`;
the short fingerprint uses the batch tool's stripped-body convention.

| Board | Changed live paths | Distinct components | Add / replace | Existing CLI incremental sequence |
|---|---:|---:|---:|---|
| 5ea | 9 | 9 | 5 / 4 | blocked by alias convergence |
| 5cd | 10 | 10 | 5 / 5 | blocked by alias convergence |
| 61b | 10 | 8 | 5 / 5 | blocked by alias convergence |

61b already has the target runtime/liblog/host, but needs both paths of ANL and
provider updated. 5ea/5cd already have the new route copies and old Android aliases,
and additionally need liblog/runtime. Each snapshot agrees with all overlapping
native live hashes of its declared package. The fingerprint scope does not include
10 other manifest checks (child, sandbox, ZigZag, framework boot files); these are
listed as missing evidence, not declared verified.

**Do not equate dry-run success with a deployable transition.** The existing CLI
returns from dry-run before resident checks (`tools/deploy_generation.py:388`).
The remaining handoff requirements are:

1. **Alias transaction support:** `validate_replacement` requires exactly one
   changed file and one changed live target (`tools/deploy_generation.py:111-115`).
   A coherent route + Android update fails this rule; updating the second alias
   can also be rejected because its source file already has the new bytes.
   `test_rules` reproduces this with the 61b resident manifest. No deployer
   semantics were changed here. cx-t0 can provide a coordinated alias transaction
   with pinned bytes and rollback, or validate a complete-generation transition.
2. **Whole-generation preflight is conditional:** `deploy()` hashes all future
   Android payload paths before activation (`tools/deploy_generation.py:335-338`).
   Additions absent in the recorded package cannot satisfy that check if still
   absent after rollback. The underlying post-rollback filesystem is unknown.
   A FakeBoard reproduces rejection before any write for an absent new library;
   actual rollout needs an absence-aware preflight/rollback or evidence of all
   required underlying files. The CLI also rejects another package while the
   resident generation is active (`tools/deploy_generation.py:319-321`).
3. **New static-link provenance:** the new TLS/gapfill binary hashes and ELF
   declarations are verified. At freeze time, Mac source trees still held their
   earlier build scripts. Source-body commits 7e511ad0/56b5295c and snapshots are
   recorded, but the exact new static-link recipe/commit remains **unknown**.
   The announced `libc++.a`/`libc++abi.a` change is preserved in the outer excerpt;
   the old recipe is explicitly not claimed to reproduce these new binaries.
4. **Java overlay choice:** payload JAR remains inherited **r8b d5000c4e**.
   Recorded overlays are separate. Rollout needs the outer-selected Java
   namespace JAR with HTML loading disabled; no such JAR is silently selected or
   built here. Merely having TLS/gapfill files does not prove registration or TLS.

Consequently, `executable_incremental_steps` is **null**, not 0 or 10. A possible
whole-generation route has four phases—suspend the Java overlay, roll back owned
resident mounts, activate the coherent candidate, apply the selected Java overlay
and verify—but that route remains conditional on the above preflight. Current
board readiness is **unknown**. cx-t0 receives this package for review, not a claim
that it can be applied immediately.

## Validation and R2

Two meaningful tests cover artifact corruption, split alias rejection, the actual
legacy deployment preflight with an offline fake, retained versions, provenance,
three dry-run receipts and the new ELF checks. `lifecycle.json` records the two
Rust selectors that invoke them. R2: **offline composition verified; deployment
and runtime behavior unverified**. No board I/O, lock, screenshot, app launch,
compilation, commit or push was performed by this task.
