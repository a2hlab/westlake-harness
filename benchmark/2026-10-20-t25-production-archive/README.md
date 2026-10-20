# T25 production archive persistence

The original producer upload stopped at its first SSH command with rc 255 (permission denied); scp was never run. That failed receipt and the original remote-pending preparation are preserved unchanged. A new independent read-only check found the unique remote directory absent before this continuation.

The exact prepared archive was uploaded in three successful commands: SHA256 `3d44cf1a3d64d156aebadf3ff683acefedc177b3546226806721395985ca6c9c`, **67,727,850 bytes**, at `HW248_ARTIFACT_ROOT/toutiao-t25-geometry-production-20261020/production.tar.gz`. Local and remote verification both checked all **1,419 regular members**: 1,418 data files plus their manifest. The manifest SHA is `92ff9a9a7cf1c58e42916489fb447a99c27f3f37e0d78950db6559b7e536d11f`.

The continuation made explicit security changes to the original transfer plan: absent-only atomic mkdir with mode 700 instead of mkdir-p; final file mode 600; symlink rejection; and remote verification of archive membership, every member size and SHA. These are recorded actual commands, not a claim of executing the original plan verbatim. No existing directory or archive was overwritten or removed.

`sanitized-envelopes.json` contains the read-only preflight, local verification and three transfer return codes/output with private paths aliased. `private-raw-index.json` hashes the untouched original argv/stdout/stderr/rc files, including the earlier failure. `verify_archive.py` is the exact verifier sent on stdin to the final remote command; it reads the tar without extracting or executing its contents.

The archive contains the producer’s 115 landing files, 1,238 producer raw files and all 63 actual production input rows (62 distinct files), plus archive metadata/tools. This records persistence of that prepared scope, not a complete redistributable SDK. It does not change T25 approval, device state, actual binding or playback acceptance. No ADB/HDC command, build or device action was performed here.
