# W04 bounded drivers: offline revision of the prepared scripts

The original recovery script counted paths rather than comparing private hashes, omitted actual recovery UI, and could unlock without all recovery gates. The original exec script deleted existing evidence, silently read identities, selected children by appspawn name, and adopted whatever lock was current. These independent replacements preserve the original files and repair those concrete gaps.

`exec_driver.py` executes one exact outer-signed apply argv, one normal reboot, one normal icon (20-second initial observation), then immediately discovers fresh parent/host and optional child, collects the candidate view, and captures an additional70seconds only after collection succeeds. It uses actual apply/after.run.sh. A renamed child is eligible by PPID/UID; multiple eligible children are unknown. A selected child's exe and full identity still must verify. No automatic second icon, retry of a write, directory deletion, retention or unlock is performed.

`recover_driver.py` executes the exact signed rollback argv, reboots once, actually invokes the reviewed recovery normal-icon UI for30seconds, restores original power serially after UI, and discovers the restored parent/host (no optional-child dependency). Exact original physical and parent-private five hashes, both compat absences including symlinks,18guardian SHA values, HAP/cfg, debug errNum106 with original process rc, power30000/86400000 and boot/parent identity bookends must all pass before unlock. The image verdict remains for the outer reviewer; successful screenshot collection is never labeled feed/video pass. Any incomplete restoration retains the lock and receipts for outer handling within the unchanged deadline.

Every subprocess has full actual argv, bytes stdout/stderr, numeric rc (124 on host timeout), and timestamps in an exclusive receipt directory. Shell calls require a unique zero remote marker in addition to local rc0. The session always uses the original signed admission holder/start and never adopts a different current holder or starts a new timer. The normal driver ends by1100seconds, recovery by1800seconds from the original start; there is no extension mechanism. Read-only reboot readiness polling is bounded; writes are never retried.

## Invocation

Use a new window containing its original signed admission.json, exact apply.argv.json or rollback.argv.json, data/fresh.json and reviewed data/inputs. Replace the SHA arguments with the actual immutable files, not a copied older window. The operation argv is verified against the same repo/window/holder/start and reviewed transport/executor; helper-pins.json binds the actual main helpers.

```sh
python3 exec_driver.py --repo "$MAIN" --window "$W" --hdc "$HDC" --admission-sha "$ORIGIN_ADMISSION_SHA" --operation-argv-sha "$APPLY_ARGV_SHA" --execute
python3 recover_driver.py --repo "$MAIN" --window "$W" --hdc "$HDC" --admission-sha "$ORIGIN_ADMISSION_SHA" --operation-argv-sha "$ROLLBACK_ARGV_SHA" --execute
```

Without --execute, these entrypoints print preview-only and invoke no transport; that preview does not certify actual admission. `exec-reviewed` and `recover-reviewed` must not already exist. On failure do not delete them or retry the driver; the outer reviews exact partial receipts and selects the existing recovery route. No candidate runtime source was changed.

Five host tests exercise real timeout bytes and exclusive output, renamed/ambiguous child selection, actual restore-function ordering under explicit device seams, real generated compat shell rejection, and false private/control/config/HAP/power/debug gates. They are offline evidence only. The sample baseline source is the already committed bound-data-01; no new production build or device execution occurred.
