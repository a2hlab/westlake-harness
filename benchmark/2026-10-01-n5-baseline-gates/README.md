# N5 versus signed U5: native baseline exception review

The earlier 28/78 N5 rejection did not distinguish a candidate regression from
an incomplete static model of the signed baseline. With identical system inputs,
**U5 rejects 131 findings and N5 rejects 183**. There are **126 shared findings,
57 N5-only findings, and 5 U5-only findings eliminated by N5**. None is silently
waived. Both remain ineligible under the current empty exception registry.

All 57 new findings concern byte-identical U5 libraries reached after the new
Flutter runtime search edge. All 57 needed basenames exist in the device view.
Physical existence is established; visibility, owner reuse and one-time runtime
initialization are **not**. These need explicit review and the conditional device
experiment, not a static PASS claim.

## Evidence and scope

- Signed U5: `../2026-10-01-u5-sweep/{results.json,facts-all.txt}`; outer reviewed
  24 own-UI results in the three-board sweep. This does not prove every unresolved
  native call safe; flaky outcomes are separately recorded in the U5 repeat report.
- Package identities are unchanged: U5 `7bc02de7...`, N5 `b446d8db...`.
  Only the original two ANL aliases differ between payloads. This task added only
  `native-checks` data, never payload/manifest bytes or namespace paths.
- Device boot before inventory, after inventory and after ELF collection:
  `f828d689-82ab-4bc8-8e15-421332d63721`.
- 3278 path/SHA rows: 2829 `/system/lib64`, 67 `/system/android/lib64`,
  382 `/vendor/lib64`; 3129 unique ELF SHA values. Every file was retrieved or
  satisfied by a local package file with the same SHA, then SHA-verified and
  inspected by host `llvm-readelf -d --wide`. Zero fetch/hash/ELF failures.
- Both sidecars receive 3180 system-file entries after excluding 98 targets
  already supplied by package mounts. Snapshot files never shadow package targets.
- Strict gate implementation is unchanged. It does not traverse namespace inherit
  or switch dependency owner. A physically present file outside declared search
  paths remains a visibility finding, not an assertion that the device lacks it.
- The complete inventory adds 77 previously unmodeled library directories to both
  reports. Their presence increases findings; it does not imply a runtime change.

| Gate finding | U5 | N5 |
| --- | ---: | ---: |
| N1 unresolved calls | 22 | 22 |
| N1 unknown target/namespace | 6 | 6 |
| N2 unresolved domain dependency | 15 | 67 |
| N2 dynamic effective path unknown | 6 | 6 |
| N2 uncovered library directory | 82 | 82 |

All 15 U5 and 67 N5 dependency findings have physical candidates in the snapshot.
N5 removes the Flutter `libandroid -> liboh_android_runtime` finding and four
private-facade `libc.so` findings. It newly traverses unchanged runtime/bridge and
support libraries, producing the 57 additional visibility findings. The two full
reports retain searched paths, candidate paths, SONAME, NEEDED and exact issue IDs.

## Review request

`EXCEPTION-PROPOSAL.md` enumerates **314 separately bound package findings**;
`exception-proposal.json` supplies object, reason, U5 evidence, physical candidates,
SHA identities, package/input binding and pending approval for every row.
`delta.json` lists all 57 candidate-only and 5 removed findings. The semantic
comparison removes package-specific issue IDs and search/candidate evidence only;
full evidence remains in the proposal. The 57 candidate-only rows are not presented
as already approved baseline exceptions.

Outer approval is required by the 02:14:45 ACK before any registry entry is added.
The registry is still empty; no N5 deployment, lock, app launch or device write
occurred. Deployment wiring stays on `feat/bms-route-deploy`, not master.
After explicit approval, bind exceptions to these exact reports, re-run the real
gates for **both candidate and U5 rollback**, and only then take the <=30 minute
5ea window: HW/ZZ, six Flutter keys, aegis/catima, singleton/constructor evidence,
U5 rollback with runtime fingerprint `73ecf422dba2` and boot image `0876029078e2`.

## Reproduction and collection

Run from this report directory's repository. Scripts derive workspace/home paths.

```sh
python3 benchmark/2026-10-01-n5-baseline-gates/collect.py
python3 benchmark/2026-10-01-n5-baseline-gates/snapshot.py
python3 benchmark/2026-10-01-n5-baseline-gates/compare.py
python3 benchmark/2026-10-01-n5-baseline-gates/report.py
agent-spec lifecycle specs/native-n5/t2-baseline-exceptions.spec.md --code tools/spec-checks
```

Device access is exclusively `orb -m a2hlab` -> `hdc_mac.sh -t <5ea>`:

```sh
cat /proc/sys/kernel/random/boot_id
find /system/lib64 /system/android/lib64 /vendor/lib64 \( -type f -o -type l \) -name '*.so*' -exec sha256sum {} \;
hdc file recv <source-library> <local-SHA-cache>
```

The last line denotes the hdc operation, not a device shell command. No helper or
readelf was sent to the device. `commands.jsonl.gz` preserves all actual argv;
`inventory-raw.txt`, `inventory.json`, `metadata.json.gz`, `snapshot.json.gz` preserve
raw hashes and all dynamic metadata. Compression is lossless. The ~1 GiB ELF cache
is local under `elf/` and duplicated into the two package sidecars, excluded from
git; repeat collection verifies every file against inventory. Small source,
receipts, exact exception proposals and test evidence are committed.

## Subsequent outer disposition

The 02:30:26 ACK approved 257 baseline entries and granted 57 candidate-only
entries for one temporary experiment. The proposal and original rejected reports
above remain historical evidence. See `../2026-10-01-n5-window/` for registration,
revocation, board results and the matched U5 double-mapping control.
