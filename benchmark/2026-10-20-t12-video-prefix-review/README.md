# T12 partial stderr prefix: actual loader failures

Earlier config JSON matches were not executed player errors. This review retains actual native-loader records and distinguishes them from those configuration strings. It does not identify an exhaustive first fatal error.

The saved regular-file prefix contains 13,446,144 bytes (SHA-256 in results.json); the host command timed out after 40 seconds and has no completed postguard. The before-read inode was 66352:179838, size 41,493,147 bytes. No complete-window or stable post-read identity claim is made.

`excerpts.log` contains unchanged, selected source lines; results.json records each original zero-based byte offset, one-based line, byte length, SHA-256, and excerpt offset. Large settings JSON and URLs were not copied. Full original evidence remains at the aliased private source path.

## Findings

- Four observed attempts each fail for `libttopenssl.so`, `libavmdlbase.so`, `libavmdls.so`, `libavmdlv2.so`, and `libavmdl.so`. The candidate path under `/data/local/tmp/asx/lib/arm64-v8a/` reports `open_errno=2`; the final loader record reports no such file or directory. First retained ttopenssl candidate is source byte 246171, line 2924. Class paths include the APK zip library path, which alone does not prove successful zip fallback.
- Other real failures include sysoptimizer and wasm C++ symbol resolution, lynx missing libnapi_v8, and several missing optional-looking library names. Optionality and video causality remain unknown.
- The retained prefix has no actual ttmplayer load/failure record. Its ttmplayer references occur in oversized settings/config lines. No mffmpeg occurrence or UnsatisfiedLinkError occurs in this prefix. The separately captured maps have mffmpeg mapped and ttmplayer absent; the prefix is not a complete timeline of that snapshot.

## Smallest next investigation

Inspect the exact APK zip inventory and existing extraction manifest offline for the five failed basenames, then inspect the already captured loader basename/APK fallback implementation. Do not deploy a guessed missing-library fix or assert that these failures caused the absent player. This is evidence of actual load errors, not proof of the video causal chain. No device command or production change was performed.
