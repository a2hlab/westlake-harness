# 2026-09-27 global slack-padding interposer (#48 mitigation)
Statistical verdict (16 rounds): the non-hook mallocng corruption is a WHOLE-HEAP RANDOM adjacent
block-header smash (victims span sscronet/ICU/Mali/hilog/ipc/art) → no targeted fix possible;
mitigation must be allocator-level. This is the last concrete lever: pad every allocation with SLACK
tail bytes so a bounded overflow lands in slack, not the next musl chunk header.

| Path | What |
|------|------|
| src/westlake_pad.c | header-minimal malloc-family interposer: request n+SLACK, return unchanged; pure slack (no guard/track) |
| out/libwestlake_pad.aarch64-ohos.so | board build (gitignored; VM ~/a2hlab/ws/out-pad48/libwestlake_pad.so), sha 4e80e2eb2b2c8c86 |
| NOTES.md | verdict, design, build/props, self-test, deploy + the decisive A/B experiment |

Deploy: swap run.sh single-slot preload gwp_shim→libwestlake_pad.so; gate on `[WGWP-PAD] armed`;
~15-round A/B (feed OK + crash rate). SLACK=64 (enlarge if overrun exceeds it). Supersedes the
diagnostic guards/observers (feed-break risk far lower — pure slack, functionally transparent).
