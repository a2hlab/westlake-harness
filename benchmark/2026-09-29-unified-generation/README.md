# Unified generation 6cb40cd6 (#66)

The previous deployment recipe depended on private build directories and a single
boot ID. A power cycle discarded its mounts. This package copies the **accepted
bytes**, including all 226 files observed under the B5 `/system/android`, 29 route
providers, host/child/config, and five ZigZag native files. It does not rebuild ART
or change the installer. The package has 274 sealed files and 14 ordered mounts.

The outer reviewer accepted B6 on #66: ART slot 0 consumes Wikipedia's SIGSEGV and
execution passes `getTheme`; HelloWorld and ZigZag regressions passed. Wikipedia
still exits to the desktop after `performCreate`; acceptance does **not** mean
Wikipedia is lit, and a typed caught NPE is not directly logged.

## Deployment

The Mac-readable package is
`/Users/zhaoyue/orca/workspaces/westlake-generation-6cb40cd6`.
The entry point is `scripts/lab/deploy_generation.sh`, also copied into the
package as `tools/deploy_generation.sh`. A Mac invocation dispatches HDC through
the `a2hlab` VM. `--dry-run` validates every file without device I/O.

```sh
scripts/lab/deploy_generation.sh <full-serial> <package-directory> --dry-run
# Acquire board_note.sh lock for your own assigned serial/lane first, then:
WESTLAKE_LANE=cc-t3 scripts/lab/deploy_generation.sh <full-serial> <package-directory>
# Only when rollback is explicitly wanted:
WESTLAKE_LANE=cc-t3 scripts/lab/deploy_generation.sh <full-serial> <package-directory> --rollback
```

Use `cx-t0` for 5ea, `cc-t3` for 5cd and the actual assigned lane for 61b. The
script does not acquire, steal or release locks. Full serials are allowlisted;
the historical truncated 61b key is rejected. Every device operation rechecks
lock, connection and boot ID. Only 5ea was executed for this task.

Prerequisites: the OH6.1 PR03/BMS setup, installed HelloWorld, ZigZag and Wikipedia,
existing mount targets and the pinned OH libc++ ABI. This is a runtime deployment
package, not a ROM flasher or APK installer. It intentionally restores the B5
runtime JAR `250958dc`; agents applying newer Java fixes must reapply their
reviewed JAR afterward and record that overlay. Platform installer bytes are
captured before deployment and checked unchanged afterward.

After reboot, run the **same deployment command**: state is keyed by serial and
boot ID, and all generation mounts are replayed from the package. There is no
new automatic startup service. Repeating the command in the same boot verifies
existing mounts and cold-launches HelloWorld without stacking another overlay.
The command is designed for reboot replay; #66 does not deliberately reboot the
board that is to remain resident. The prior #58 recovery supplied the reboot
reference evidence.

State and raw evidence are retained at
`/Users/zhaoyue/orca/workspaces/westlake-generation-state/<serial>/`.
Keep that directory for rollback. `--rollback` refuses cross-boot state or mounts
covered by another owner, unmounts its own rows in reverse order, checks every
pre-deployment file hash and restarts the original parent. Activation failures
attempt the same rollback; lock/transport/boot loss prevents unsafe continuation.
Mount intent is persisted before each bind so an interrupted status response can
be reconciled against mountinfo. Staged payloads remain for audit.

## Identity and evidence

| Artifact | SHA256 prefix |
|---|---|
| sealed generation | `6cb40cd6` |
| host | `b7205719` |
| child | `03aa6216` |
| runtime-provider | `3aa5d169` |
| original ART | `59e1bb45` |
| musl sigchain | `6d5d5538` |
| abort C bridge | `429a226c` |
| OH adapter bridge | `84695d62` |
| OH Android runtime | `9ccf64f8` |
| route openjdkjvm | `8b462862` |

The 26 preserved R155 providers are unchanged. Raw sealed manifests and prior
host closure/negative-control receipts are copied unchanged into `receipts/`.
`package-manifest.json` lists the complete deployment table and file digests.
The deployment gate checks the live parent executable, a HelloWorld child of that
parent, the child's `/proc/<pid>/root` hashes, exactly one offset-zero ART mapping,
and exactly one route-a openjdkjvm mapping. Adapter bridge paths and SHA are
checked too. Two adapter bridge instances are allowed: the accepted #58 maps
already contain two instances with the same file identity. The first #66 attempt
incorrectly required one bridge instance and rolled back; that extra requirement
was removed, while the single-ART requirement stayed intact. The failed gate and
complete rollback receipt are retained, not counted as a runtime regression.

Screenshots are the visual ground truth; process or identity gates alone do not
prove rendering. Fresh HelloWorld/ZigZag/Wikipedia images are submitted for outer
review. See `results.json` for current run IDs and honest R2 boundaries.

## Validation

All 18 deployment tests pass. The known-answer suite passes 69 tests with two
expected skips. `test_deploy_generation.py` exercises payload tampering, truncated serials, path
traversal, unsealed sources, duplicate targets, duplicate ART, wrong openjdkjvm,
missing bridge, accepted duplicate bridge, nested rollback order, foreign mount
ownership, boot changes, lost mount acknowledgements, rollback hash failure and
idempotent re-entry. The repository known-answer suite and B6 lifecycle are also
retained. The unchanged B6 contract still has the historical Wikipedia-lit and
typed-NPE failures; #66's explicit outer acceptance and packaging assignment do
not alter those raw verdicts or the spec.

## Resident run on 5ea

Run `b66-resident-5ea-20260929`, parent PID 9337:

| App | Child PID | Final screenshot | New faultlogs |
|---|---:|---|---:|
| HelloWorld | 12954 | [own interface](screens/helloworld-final.jpeg) | 0 |
| Wikipedia | 14293, exited | [desktop](screens/wikipedia-final.jpeg) | 0 |
| ZigZag | 15430 | [game title screen](screens/zigzag-final.jpeg) | 0 |

Wikipedia hilog lines 16484–16485 again show SIGSEGV 11 dispatched to ART slot 0
and `directly return`; line 19871 shows `finishActivity`/`TerminateAbility`.
These are fresh #66 observations, not substituted from #58. Outer visual sign-off
is pending. The generation remains mounted after this run; no final B5 rollback.
Same-boot re-entry retained parent 9337 and issued **zero bind-mount commands**.
