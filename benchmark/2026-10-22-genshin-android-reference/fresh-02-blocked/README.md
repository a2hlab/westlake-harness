# G36 fresh attempt 02 — BLOCKED

A user-reported external state change authorized one fresh check through the original ADB entry. That single attempt again failed locally before device contact: `could not install *smartsocket* listener: Operation not permitted`. This does not establish that the Android device is offline or that the APK is faulty.

Actual interval: 2026-10-22 04:02:04.710467–04:02:05.281411 +08:00; rc1, no timeout, empty stdout. Original executable: `$HOME/Library/Android/sdk/platform-tools/adb`; arguments: `-s N100CU025C18D000128 get-state`. No explicit server restart, alternate port/server/tool/lane, permission change or delegated retry occurred. ADB itself attempted its default daemon startup, as recorded in stderr.

The APK was rehashed before this attempt: 513290344 bytes, SHA256 `abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc`. All later fresh checks, lock acquisition, installation and launch remained NOT_RUN. Cleanup was unnecessary because no lock, installation or launch occurred. Device liveness remains unknown.

`facts.txt` is copied byte-for-byte from this new private receipt directory; `raw-index.json` binds all seven original receipt/facts files. The immutable attempt directory is `$WORKSPACES/westlake-harness-g10-env/benchmark/2026-10-22-genshin-android-reference/.private/readonly-02/`. Previous readonly-01 evidence and the accepted historical ten-file package are unchanged. This addendum is path-only for outer ACK/landing; known shared Git/board restrictions were not retried. No device acceptance PASS is claimed.
