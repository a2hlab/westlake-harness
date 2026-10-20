# T18 five-item candidate window

Runtime restoration is not feed restoration. This closed 1,483.28-second window restored the original five-item state but ended on the Westlake IME host, not the news feed. The baseline splash path reported `MediaPlayer.native_init` missing. The final screenshot was independently read. No random-exit cause is assigned.

The candidate showed a real news feed. The user explicitly confirmed hearing the “house on the 65th floor” clip on 5cd: **PASS_USER_CONFIRMED_CLIP_AUDIO**. This is a scoped human audible observation, not an instrumented audio test, direct proof of getter invocation/return, or a general audio/API freeze. Video remains **NOT_PASSED**: the video page stayed on a cover and the selected log interval records CPU ANativeWindow_lock unimplemented and 249 drawPicture `ret:-19` failures.

`checkpoint-01/packet-final/range/runtime-log-review.json` is the byte-exact peer assessment. Its fixed literal counts and first/last offsets were independently checked against the complete 6,639,414-byte interval. The absence of the earlier getter-name/UnsatisfiedLinkError literals in that interval does not prove invocation. Downstream audio write reports maxWriteSize 38400 greater than mBufferSize 9600. The later human receipt supplies the separate audible observation; it does not rewrite the earlier checkpoint's unknown status.

The observer actually attempted connection, got no stop reply, and produced zero fromSurface/lock samples. Its host cleanup did not verify; the separate outer finally cleanup did verify. The server crash dump, both cleanup outcomes and original connection failure are preserved. No object/provider observation or debugger success is claimed.

The original apply-plan rollback returned 0. Independent local comparison confirms the same eight comparable fields across 518 main snapshot targets/812 labels and byte-identical 26-target supplement content except its boot line. Power is restored to 10000/10000; the debug log key is absent (106). The final exact media-path read corrects an earlier missing-path read without deleting it. Unlock returned 0; held-after returned 1 with empty stdout.

## Evidence layout

- `checkpoint-01/`: immutable candidate checkpoint, exact deployment/build pins, two original candidate images, observer results and scoped peer log analysis.
- `final/`: final close, user audio receipt, restoration comparison, original host-only image, baseline technical excerpt, unchanged run_facts stdout and public/raw SHA index.
- `archive/receipt.json`: local tar verification and remote pending status. All full logs, failed attempts, command triplets, snapshots, observer output, helpers and candidate inputs are private archive members. Original production and source-closure archives remain separate.
- `.private/archive-01/remote-commands.private.json`: three exact upload/verification argv for outer execution, not public source or an automatic device action.

No full stderr, media URL/token or large binary enters the public landing list. The complete original bytes remain in the persistent archive. Source/build pins distinguish the bridge candidate JSON SHA from the dca530 runtime DSO SHA. New build logs are not historical mc46 final build logs.

## Reproduction of this evidence packaging

`build_final.py --write` creates a fresh final directory using local records; its default is read-only. `prepare_archive.py --out PERSISTENT_OUT --close CLOSE_JSON` packages local files and verifies every member; upload is opt-in and was not invoked by this lane. `finalize_packet.py --write` freezes the public manifest; the default verifies it. No device or build commands were issued for this packet.
