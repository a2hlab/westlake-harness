# N5 short window and matched U5 duplicate-library control

The initial stop criterion was insufficient for attribution: **LocalSend maps two
`liblog.so` inodes on both N5 and U5**. The same-board, same-boot, same-J6 comparison
reports **variables: 1**, grouping the two ANL aliases. The double mapping is an
existing baseline behavior, not a demonstrated N5 regression. The original N5
failure observation is retained next to the subsequent baseline result.

N5 remains **not accepted**: only LocalSend was attempted after HW/ZZ controls,
both LocalSend t20 captures show the desktop, and no claim is made about the other
five Flutter apps or aegis/catima. The temporary grant is revoked. The board was
restored to U5 and unlocked at **02:50:02**, inside the 02:34:34–03:04:19 window.

## Results

| Phase / process | bridge | runtime | appexecfwk_base | liblog | bionic_compat |
| --- | ---: | ---: | ---: | ---: | ---: |
| N5 LocalSend PID 16312 | 1 | 1 | 1 | **2** | 1 |
| U5 LocalSend PID 20054 | 1 | 1 | 1 | **2** | 1 |

Counts are distinct `(device, inode)` identities in simultaneous process maps,
not ELF segment counts. Both phases map one `liblog` from `/system/android/lib64`
and one from the current sealed route directory. Their package SHAs are different:
`8c81a937...` and `a2530a4b...`; these two payloads already coexist in U5.

- N5: device `103:30`, inodes **102523 / 96737**.
- U5: device `103:30`, inodes **100094 / 98968**.
- `duplicate-failure.json`: original candidate stop evidence.
- `duplicate-baseline.json`: subsequent U5 control and revised attribution.
- `n5-five-libraries.txt`, `u5-five-libraries.txt`: readable mapped paths/segments.
- `*-localsend-maps.txt.gz`, `maps-evidence.tar.gz`: lossless raw maps/PS evidence.
- `compare-localsend.txt`: master comparator, variables:1. The earlier branch
  comparator output is retained as `compare-localsend-legacy.txt`; it counted two
  aliases separately and ran before baseline facts existed, so is not the verdict.

Observed progress is narrower than rendering:

- U5 LocalSend throws `Flutter private preload libandroid.so: Error loading shared
  library liboh_android_runtime.so: (needed by .../westlake_flutter/libandroid.so)`.
- N5 does not show that signature and reaches Flutter plugin registration and the
  `1.raster` thread. It logs `dlopen_impl load library header failed for
  /system/lib64/libGLESv3.so`, followed by a signal 11 in `1.raster`.
- This shows the original dependency wall was crossed in this app. It does not
  prove the GLES error causes the signal, that all 57 edges work, or that
  constructors ran exactly once. Constructor count remains **unknown**.
- N5 HW/ZZ and restored U5 HW show their own UI at t20 (lane image review;
  final sign-off belongs to the outer loop). Both LocalSend t20 images are desktop.

## Approval and enforcement

The 02:30:26 outer ACK authorized **257 permanent baseline findings** and **57
N5-only findings for this one experiment**. Only the former are written to
`knowledge/gates/native-predeploy-exceptions.json`.

`--native-experiment` supplies a separate board/package-bound, timezone-aware
<=30 minute receipt. The deployer checks it before native/device operations,
includes its hash in dispatch binding, and combines its exact findings with the
permanent registry only in a temporary host file. Expired, revoked, wrong-board,
overlong or malformed scopes reject. Baseline rollback does not depend on the
candidate receipt remaining active. The original active receipt is retained only
as compressed evidence; `window.json` is now revoked.

Six scope tests and ten prior deployment-hook tests pass. The actual post-revocation
N5 dry-run rejects before Board access. Deployment, rollback, J6 restoration and
both final fingerprints completed with the real gate code. The gate implementation
itself was not weakened. Initial historical tests now use the archived empty
proposal registry, so recording approved exceptions does not rewrite old evidence.

## Collection and limitations

The master batch ran each app with 16 MiB/private-off/clock preflight, `--hilog 20
--shots 5,20 --focus-check`; LocalSend was reinstalled in both phases. HW/ZZ used
the existing controls manifest in launch-only mode. `facts-all.txt` contains the
four facts files verbatim. Five run records produced ten captured screenshots;
these are observations, not five distinct applications.

The first maps observer relied on device `awk`, which is absent. Its empty samples
and error output are retained; no singleton result is inferred from them. Before
Flutter testing it was replaced with host-side PS parsing followed by read-only
PID maps reads. Approximately one-second sampling cannot rule out unobserved
short-lived mappings. UID and PID from raw PS bind the captured startup maps to
LocalSend, which exited before t5; batch facts therefore honestly report
`child_hilog=0`, although the independently observed PID allows extraction from the
full hilog. Five-library identity counts do not prove once-only constructors.

After the candidate stop, the outer loop explicitly requested U5 LocalSend and HW
before unlock. That added baseline experiment is completed; there was no second
N5 activation. Source/report changes remain on this lane's branch, not master.

## Final state and artifacts

`end-receipt.json` verifies package paths in shell and appspawn views, J6
`2488052f...`, RUNTIME **73ecf422dba2**, BOOTIMAGE **0876029078e2**, and the original
boot ID. `unlock.json` records empty held state. `run-index.json` lists all t20
paths under `evidence/`; records, process tables, full compressed hilog and images
are retained. Raw device-command logs remain in the local `runs/` directory.
The unrun five Flutter targets and aegis/catima are explicitly listed in
`results.json`; they are not counted as passes or failures.
