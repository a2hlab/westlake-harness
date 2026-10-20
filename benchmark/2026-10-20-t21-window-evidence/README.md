# T21 six-item window evidence

Successful native lock/unlock logs do not establish a displayed feed or video playback. This closed 5cd window restored runtime files and configuration, but its final screenshot is the Westlake IME host, not a news feed.

The window lasted 1098.350549 seconds. Apply and rollback returned zero. Child 11040 logged five lock/unlock pairs with request/map/unmap/flush return zero, followed by `Skia Invalid GrBackendTexture 1200x2132`. The guarded four-slot read could not read the exited child and remains UNKNOWN. Children 8306 and 13834 have separate preserved logs; no successful visual result is inferred. Video is NOT_PASSED and audio in this window is UNKNOWN.

## Restoration and limitations

[Restoration comparison](final/restoration-comparison.json) verifies all eight comparable fields of the 518-target/812-label snapshots and the 26 supplemental entries, excluding the expected boot-line change. Physical and private original run/bridge/media/player/shim SHA values, compatibility-library absence, power 10000/10000 and absent debug parameter (106) are bound by the original receipts. Boot, PID and uptime strings are not required to stay equal across reboot.

[Final screenshot](final/images/restored-host.jpeg) was read independently: HOST_ONLY_NOT_FEED. Restored child 14567's complete private log SHA is `5d262e1bea0a12a83db83110eb70d114c6e232f0cb3bc6545c23752014163d36`; its [minimal excerpt](final/baseline-native-init-excerpt.txt) records missing `MediaPlayer.native_init`. This is not a feed-restoration pass or an investigation of random exits.

The initial unlock command included an extra argument and returned rc2 before mutation. The exact three-argument retry returned rc0; held-after stdout was empty. No separately recorded held-after rc is invented. Both attempts remain in [receipts](final/receipts/close.json).

## Facts and source binding

[Original facts](final/facts.txt), reproduced byte-for-byte with the existing helper:

```
TOTAL keys=4 screenshots_captured=4/4 alive_t5=0 alive_last=0 alive_unknown=4
```

[Technical-source pins](final/main-technical-evidence.json) bind immutable MAIN commit `ecc26cb9ed`, including its 101 technical excerpts and three complete candidate-log hashes. [Input manifest](final/candidate-inputs.json), original apply/rollback plans and [source index](final/source-index.json) bind the executed objects. Public helper copies are sanitized historical execution evidence, not generic rerun tools; exact originals are in the private archive. No new source build or device call was performed by this evidence lane.

## Durable raw package

The allowlist contains the complete `BASE20/t21-5cd-window-01`, `t21-readonly-01`, `t21-candidate-inputs`, and exactly four helpers: `t21_exec.py`, `t21_launch.py`, `t21_outer.py`, `t21_wait_boot.py`. It includes failed/retried commands, partial hilog timeout, all full logs, snapshots, inputs, images and immutable technical-source blobs. No unrelated window is included. BASE20 resolves under `$HOME/.local/share/westlake/toutiao-resume-20261020`.

Tar SHA: `74f2ca7b0baa6ce310687ca0b6ebf85d0c254b93d85ac5de2392adb2cca793cb`; 6,813,546 bytes; 8,166 members. Every member was read back and checked against its recorded SHA and size. See [local verification](archive/local-verification.json).

The first SSH attempt returned 255 under the lane sandbox; its sanitized stdout/stderr/rc and raw hashes are preserved. [Original pending receipt](archive/pending.json) remains pending. Outer execution uses the exact three argv in `.private/archive-01/remote-commands.private.json`; raw receipt and tar remain in that persistent directory. Future remote success must be a separate sidecar and must not rewrite the original pending receipt or tar.

## Reproduction of the evidence checks

`build_final.py --write`, `prepare_archive.py --out NEW_PERSISTENT_DIR --close CLOSE_JSON`, and `publish_archive_receipt.py --write` create fresh outputs and reject existing destinations. `upload_archive.py --execute` is explicit and stops at the first failed transfer command. `finalize_packet.py` defaults to read-only verification; only `--write` writes package manifests. These are local evidence and archive operations, not device execution entry points.
