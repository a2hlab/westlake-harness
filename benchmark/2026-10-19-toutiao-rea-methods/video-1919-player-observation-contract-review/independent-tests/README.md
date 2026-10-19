# Independent player mirror behavior oracle

This is a black-box host test, not a copy of the mirror implementation. Supply
the standalone C mirror source after CC freezes it. Nothing is deployed and no
Android/player artifact is built. The seven frozen parent files are untouched.

```sh
TEST=benchmark/2026-10-19-toutiao-rea-methods/video-1919-player-observation-contract-review/independent-tests
python3 "$TEST/run.py" --source "$MIRROR_SOURCE" --out "$TEST/.artifacts/cc-review-01"
```

Repeat `--source` only for required mirror translation units; use `--include-dir`
for existing headers if needed. Output must be new. The runner compiles only the
supplied translation units with `write` and `__android_log_vprint` redirected to
mocks, then links the unmodified oracle. It records exact commands, source/tool
hashes, stdout, stderr and return codes. No source rewriting or provider lookup
fallback is provided. A source that cannot use these direct imports fails to link
or compile and must be reviewed, not silently adapted.

Eight separate processes check mixed varargs, filtered `%n` (ordinary,
positional, `hh` and `l`), string/write-address aliasing, 300 calls across the
256-attempt cap, long tag plus payload total length, EINTR/no retry, short
write/no retry, and null-tag forwarding. The backend checks exact priority,
tag/format pointers and entry errno. It returns a distinctive value/errno so the
wrapper cannot substitute production constants. The alias backend models
`%s%hhn` explicitly to avoid host-libc security restrictions on dynamic `%n`.
Unsupported-format skip markers are optional; their payload must not be evaluated.

`negative_control.c` is intentionally deficient: it only forwards and never
mirrors. Its expected failures prove the oracle does not approve an empty mirror.
Its passing dangerous-format cases are only harness checks, not CC validation.
`negative_control_eager.c` deliberately formats before filtering. The oracle
rejects both its filtered `%n` mutations and its changed alias-backend text.
Exact negative-control commands and output streams are embedded in
`evidence/negative-*.json`; these are intentional failures, not candidate failures.

Limits: host ABI only; no AArch64 production ABI, provider/namespace, ELF rename,
105 relocations, concurrency or counter-wrap proof. Saturating atomic operations
and cap-before-formatting still need source review. No actual CC source was
tested when this oracle was prepared. `%m` production-libc behavior is also a
source/target-ABI review item; this small portable suite does not assert a host
extension as production behavior. Direct fd2 writes are mocked; alternate output
APIs are outside this seam and must not be used to bypass the contract.
