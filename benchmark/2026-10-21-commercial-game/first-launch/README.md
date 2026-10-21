# G06: bounded first-launch preparation for spare 5ea

The G05 uninstall draft treated an empty package-list response as absence. That is not a successful recovery. This successor does not uninstall: it retains a verified new Genshin installation for continued debugging, stops only its proven UID through the existing BMS `cold_stop`, and restores this board's original screen/power/logging state. A read error, foreign package change, unproven installation or failed stop returns nonzero. `board_run.before_unlock` then retains the lock.

This is offline preparation, not a device result. No APK was executed and no device command was issued by this lane. G06's three human scenarios remain pending. Screenshots, audio, first fatal, provider selection and playability are UNKNOWN/NOT_TESTED.

## Actual fresh inputs

- Same boot before/after: `45339478-78d4-4211-ac17-6975440de5ce`.
- Runtime fingerprint `fd464714645b`, 124 actual member hashes; boot fingerprint `ee927db88a67`, 36 members. The member files, not just the short aggregate, are indexed in `fresh-inputs.json` and copied under `evidence/`.
- Original focus is `SCBScreenLock10`, power is SLEEP, Timeout=30000ms and OverrideTimeout=10000ms. No 61b imehost/guardian recovery is imposed on 5ea.
- Successful full package-list read does not contain `com.miHoYo.Yuanshen`. This is rechecked under the new lock, not inferred from grep rc=1.
- Original hilog has four 16.0M buffers and privacy `true ` (trailing space). The exact outer read is retained. Complete size tokens pass through the real BMS `size_bytes`; restore uses decimal bytes, not `16`.
- APK SHA is `abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc`, 513290344 bytes. Metadata SHA is separately `fe623c5bb4f2b7b1dcedd54e996d82922ed5b3e2e07df28d658ceec2d4b9b85c`.

`native_sidecars=[]` means no additional sidecars. The existing installer extracts the APK's selected-ABI libraries; do not repack the APK or copy Boat C7/C4. After installation, retain the actual nativeLibraryDir and extracted member hashes as observations, not an additional speculative provider gate.

## Minimal hooks and scope

`prepare.py` validates the real local APK and G05 receipts, then emits a disabled board_run plan and unsigned hook config. It does not acquire a lock or contact HDC. The main checkout is an explicit argument, so source pins can be refreshed after G07 lands.

`recovery_hook.py before` is the existing board_run `after_lock` hook. It records the complete holder (lane, PID, timestamp), boot and start; compares all 160 fresh member hashes; verifies target absence and ten sandbox data roots before the original installer can modify them; and records power, foreground and logging. It refuses a changed preimage. It performs only reads.

`restore` is `before_unlock`. For a present package it requires this window's BMS record, matching boot/APK/metadata/UID and unchanged complete bundle readback; it reuses `cold_stop`, verifies no UID consumer, and inventories retained directories. It issues no uninstall, recursive removal, signals to a system parent, runtime swap, reboot or install. It returns Home then the original SLEEP/lockscreen and 30000/10000 power, and restores each hilog buffer and privacy value. Partial/unknown install identity or restore failure retains the lock for the outer operator; this is deliberately not universal recovery.

The generated shard name is exactly `shards`, matching `window/shards/**/genshin/record.json`. One target record is accepted; old/multiple records refuse. A failed admission before any writes may have no context file; recovery then refuses automatic unlock so the operator can inspect the read-only failure.

## Timing and observations

`stop_new_tests_by_minute=20` only prevents starting a new key. `window_limit_minutes` is not a board_run timer and is deliberately omitted. Existing per-command timeouts plus the outer operator's actual 1200/1800-second timeline govern this window; no new scheduler is introduced. The recovery hook refuses future/expired holder times, but this is not an end-to-end watchdog.

The plan requests G07's `wait_seconds=60, shots=[5,20,60]`. Do not enable it with the old board_run implementation: that implementation silently uses only 5/20 and stops the app. Wait/shot support and its new source pin require outer confirmation. A resource/login prompt ends observation without account/consent actions. Do not launch again merely to obtain a later screenshot.

The existing BMS saves install/launch hilog, ps, maps, screenshots and records. It does not itself guarantee early child birth/fd2 coverage. The execution card identifies that serial collection seam; missing early coverage stays UNKNOWN, never inferred from static JNI or zero log matches. The T23 PID-tail helper uses `-P/-z/-L/-v epoch`, never `-x` with `-z`; preserve logs if the child exits after capture and mark postguard unknown.

## Validation and evidence

`check_receipt.py` validates the local manifest and invokes the actual Python recovery tests. Rust `commercial_game_first_launch_receipt` calls that checker. Tests exercise the real recovery decision function and BMS's actual lost-marker handling; they do not claim a full device transaction.

The original pre-fix test output is retained separately. The old buffer parser's omitted decimal cases were a real coverage gap, not a device success. New tests consume the actual 5ea logging read and reject malformed tokens, disconnected/empty BMS responses, wrong boot/holder/window, old/wrong install identity, UID/bundle drift and a surviving target.

Private originals remain under the lane's `.private/g06-01/` and `COMMERCIAL_PRIVATE` (`$HOME/.local/share/westlake/commercial-game-20261021`). The public manifest excludes APK, full package inventory, user paths and private command files. No main-tree or prior G05 evidence was modified.
