# Boat r4: retain six binds, restore the omitted libandroid repair

Historical Boat PASS required ADC at both libandroid and runtime paths. R3 retained libandroid9cc; the actual child5058 root readback and maps confirm that omission while runtime947 was present. R4 keeps the r3 six-bind parameters and appends only `/system/android/lib64/libandroid.so`:9cc to historical ADC. ADC never replaces the U13 runtime path;947 remains there. This is a disabled review package, not a HUD/input or seal acceptance.

Historical exact recipe comparison is in `../historical-recipe-diff.json`: ten shared targets plus three private targets. It is the complete declared successful gate set, not proof that every historical generation difference must be copied. Actual historical/current linker namespace owner and PLT/GOT resolution remain unproven from maps alone. R4 does not replace the host, loader, child or provider generation.

## Reproduction and source limits

`replay_adc.py` applies the pinned49 before/after bytes to the existing pinned9cc file, writes a temporary output, and verifies every byte and whole SHA against historical ADC. `adc-replay.stdout.json`, `adc-replay.stderr.txt`, and `adc-replay.rc` preserve this run (rc0); interpreter/script/input/patch SHAs are recorded. The output is744856 bytes, SHA adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130. The historical comparison independently verified268/268 export records, native tables and dynamic dependencies unchanged.

This is a new byte reproduction, not a source compilation or historical execution log. `adc-closure.json` binds source-semantic mapping and outer's remote discovery: the remote inputs/c18-libandroid.so is ADC, but runtime-build.log corresponds to0d7b and cannot be paired with ADC. Exact historical source/build reproducibility remains unclosed. User explicitly accepted historical exact artifact reuse with this limitation. No binary is rebuilt or changed.

The semantic mapping identifies four geometry functions (47 executable bytes) plus two Bridge classname bytes. Its U13 homolog source is pinned for interpretation, not presented as the original ADC build source. The existing9cc archival input and exact patch table remain mandatory.

## Exact package and rollback

11 placement members /7 binds, independent `/data/westlake-demo/u13/boat-v2-20261013-r4`, cfg placed last. Captured boot d0e1f5eb-ac35-4c39-9e1a-7c40d9251220: libandroid9cc644/0/0/system_lib_file, runtime187755, original cfg7a954550, r4 root absent. The normalizer parses outer's same-boot319 raw output itself and compares exact membership/SHA; no count-only admission. Full input pins are in dependencies.json and captured.json.

All source/target preimages pass before first bind; namespace read diagnostics/SYS_PTRACE/no_parent guards remain. Apply requires187 and9cc, verify requires947 and ADC plus all7 metadata/SHA/inode checks. Worker still completes synchronously before global READY and original TT trigger lines. Existing43491 remains untouched.

Existing transaction backup, exact intent/failed-observation and retained-audit rollback code are unchanged apart from root/count/member additions. Rollback prevalidates all11 backups before any unmount, requires outer's existing cleanup receipt, restores libandroid first then the r3 six in reverse, restores cfg and checks full319. No parent kill, recursive audit deletion or weakened foreign-state rejection is added.

## Local-only commands

Set WORKSPACES to the shared workspace parent. From repository root:

```sh
R4=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/minimal-r4
python3 "$R4/replay_adc.py"
python3 "$R4/test_r4.py"
python3 "$R4/package/installer.py" --plan "$R4/package/plan.disabled.json"
```

To reproduce package derivation, pass captured.json to prepare.py with a new --out directory. Existing source paths use WORKSPACES or PACKAGE; no user-directory literal is allowed in the generated plan. The first rejected absolute-path draft is retained locally outside landing. Final installer/worker bytes did not change in that compiler-path correction.

Outer alone creates an enabled plan, fresh transaction and independent authorization under the existing installer CLI. Never reuse a prior9/10-member transaction. New boot/UI/owner evidence and BMS review are pending. R3 full128 proof is not valid for r4; no large regression proof is included here.

Eight narrow tests passed, covering exact11/7 order and first-six preservation, actual preview/shell syntax, caps/no_parent sites, phase-specific runtime/libandroid guards, actual executor11 placements, runtime partial-send, libandroid partial-send, and invalid9cc preimage rejection. Clean package-only preview passed with zero device calls.
