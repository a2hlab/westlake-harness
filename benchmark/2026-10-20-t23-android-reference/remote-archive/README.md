# Android reference remote persistence

The 65,614,789-byte private archive was uploaded to `HW248_ARTIFACT_ROOT/toutiao-t24-android-reference-20261020-f526f12717b0/reference.tar.gz`. Remote SHA-256 matches the locally readback-verified package: `f526f12717b0bb74b214a485bf4aa645dd2c59e81a70888f7a598d75c90cc4aa`.

All three actual commands returned rc 0 and exactly match the private planned argv. First, `test ! -e` and `mkdir` without `-p` require a new destination directory, under umask 077. Second, scp uploads the existing archive. Third, chmod 600 is followed by remote SHA/size/file-mode and directory-mode reads. Final file mode is 600 and directory mode is 700. No existing directory or archive was overwritten.

`sanitized-envelopes.json` records actual commands and raw streams with only home/artifact-root aliases substituted. `raw-index.json` pins the private original bytes; `results.json` states the verified remote result. The prior `window/archive-receipt.json` remains unchanged as the local-only stage. The archive contains private application/log/trace/screenshot evidence and must not be published publicly. No ADB or new capture was performed for this upload. Android different-clip motion and unconfirmed audio boundaries, and the absence of OH acceptance, remain unchanged.
