# T120 independent disabled-package review

Result: **PASS_DISABLED_PACKAGE_METADATA**, 93/93 checks. Reviewer rehashed the single `build-02` candidate produced by builder `0862a334f863d4de3bf3d4c4dda7ab1df7c6000e3b0e3d02e6c46f014aaf84d3`; no builder or controller was executed. Implementation bytes were hashed only, never decoded or inspected as source.

Do not confuse historical package identity with board compatibility, or an unindexed name with an absent file. The audit independently checks 24 staged/original inputs against base pins and T34 CHAIN, all 22 actual outputs, 17 unchanged historical outputs, and the 16-member cascade. Startup is disabled, unarmed and non-deployable. Its parent SHA matches the actual packaged parent, not the old 5cd parent. Four external dependency path/SHA pairs match T119 ordinary raw metadata on boot `ecb84d86-f22f-4622-9501-143a26f39cf1`; UID `20011300` is metadata only.

The author performed the build. The reviewer verified its existing argv/start/end/stdout/stderr/rc hashes and sizes: rc 0, empty stderr, complete argv matching the package record. No build rerun or T118 test repeat. Original build receipts and candidate remain in the author's persistent `.private/build-02` directory; public manifest pins are recorded in `results.json`.

Current-root comparison: 9 equal, 8 different, 5 not indexed (unknown, not missing). Per the clarified change scope, the old ROOT is neither written nor deleted and the candidate uses a separate new ROOT. The sole overwrite proposed is one init argv; restoring the exact original init bytes returns to the old ROOT. The current init SHA and before/after argv match T116. Generated `recovery.cfg` is not an init replacement. T121 promotion and actual byte-restoration readiness are separate reviews; this report does not claim deployment readiness or runtime behavior.

Reproduce offline from the peer checkout:

```sh
python3 benchmark/2026-10-23-qualified-r3-board-package/review/check_metadata.py
```

The script reads sibling `westlake-harness`, `westlake-harness-g10-env`, `westlake-harness-video` and the original `$HOME/.local/share/westlake/t34-reentry-retirement-20261021` inputs. It writes only its adjacent small `results.json`. No device, REA, controller, permissions or source changes.
