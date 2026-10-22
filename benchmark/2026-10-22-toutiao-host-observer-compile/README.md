# T40 compile the passive host-observer candidate (exact es2abc)

Verifies that the T39 host-observer source **compiles** with the exact pinned toolchain, closing the gap
where a Node simulation passes but the real compiler might not. Compilability only — no device, sign, pack,
install or reentry change. No REA, no T38.

## Inputs (read-only, SHA-pinned from main T39)

| input | sha256 | origin |
|---|---|---|
| `inputs/sources/baseline/EntryAbility.js` | `9dc302d9…` | main T39 `snapshot-fc0e5ec0/sources/baseline` |
| `inputs/sources/candidate/EntryAbility.js` | `fc0e5ec0…` | main T39 `snapshot-fc0e5ec0/sources/candidate` |

Compiler: Linux `es2abc` `d20db2d4…`, target API 20, input filename `EntryAbility.js` — the same tool and
argv as T32. Its path is read from the T32 `compile-linux-01/receipt.json` `compiler.path` key
(`--compiler-receipt`), not hard-coded or re-published here. The binary lives in the orb a2hlab VM; it is the
only channel that reproduces the exact baseline (the Mac `es2abc` historically produced non-matching ABCs).

## Result (EXACT_BASELINE_AND_CANDIDATE_COMPILED)

| artifact | sha256 | bytes | rc |
|---|---|---|---|
| baseline `EntryAbility.abc` | `bb1eccd3…` | 3244 | 0 |
| candidate run 1 | `db781436…` | 6644 | 0 |
| candidate run 2 | `db781436…` | 6644 | 0 |

- The baseline ABC **reproduces the historical HAP member** `ets/entryability/EntryAbility.abc`
  (`bb1eccd3…`) byte-for-byte, verified immediately after the baseline compile.
- The fc0 candidate is **byte-identical across two runs** (deterministic). It is larger than the baseline
  (the passive observer fragment) and is **not** installed.
- All four VM commands (compiler-SHA pre-check + three compiles) returned rc 0.

This is compilability only: **not** a HAP pack/sign/deploy, not a device run, and not a tap-source /
white-screen / autostart claim.

## Evidence

`compile_observer.py` is the real driver. The authoritative run is the corrected re-run
`driver-run-v3/` (after peer pre-review); the first real compile is preserved alongside it. Raw `argv` /
`cmd` / `stdout` / `stderr` / `rc` / `time` and the `.abc` binaries are in the persistent dir
`$HOME/.local/share/westlake/toutiao-host-observer-compile-20261022/driver-run-v3/` (`results.json` pins
each by SHA). **The ABC binaries stay there and are not committed to git.** `check_compile.py` (Rust
selector `toutiao_host_observer_compile`) validates that receipt and, with `--negatives`, exercises the
**production** `check()` and driver on temp copies: it mutates a baseline ABC, deletes a real log, forces
`rc=7`, drifts source under `python -O` (rejected before any VM call), forces an `OSError` through the real
`run_vm` (rc125 + time + a separate driver-error file), and uses a relative `--raw` with a bad compiler
receipt (absolutized from cwd, `COMPILER_RECEIPT_UNREADABLE`). No re-compile is run.

## Deviation (compliance was not continuous)

My first attempt to locate `es2abc` ran a VM whole-disk `find / -maxdepth 9`, which violates OPS-RUNBOOK
181. The outer loop flagged it mid-run; I stopped, did not retry or widen, and let the command time out.
Both scans returned no path. The correct method then used — read `compiler.path` from the T32 receipt and
one explicit stat of that exact suffix — is what the committed driver uses. See
`evidence/DEVIATION-20261022-vm-find.md`.

No device, ADB, REA, debugger, sign, pack, install, permission change or T38.
