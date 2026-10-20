# T30 bounded runtime peer evidence

The earlier T29 failure retained a resource-free failed Request and poisoned later acquisition. This T30 window actually exercised that failure twice: lines 337171 and 337268 record raw `40601000`, normalized `-5`, zero buffer/native/bits and no subsequent resource operations, but **retained=0**. Each paired record reports release `1/1/1`. The four textual error matches are two real failed requests plus their two pair summaries, not four requests.

The fixed 38,000,045-byte prefix has SHA `aaea4645a6ba849c4d50e2e4b05a538fef1816d7e25a4f4b3c8ad73a8800c3fc`. Identity matches the same candidate boot and child as the five matching live slots. The prefix transfer and bookend hashes were verified; global log immutability remains unknown.

The 59 R29 lines comprise 40 CPU records, 18 consumer records and one first-budget marker. No retained=1 or CPU rc=-16 appears in those bounded records. Successful request/flush records later appear on another wrapper/OH pair; these do **not** establish successful subsequent Q/flush on either failed object. Geometry succeeds later at both failed wrapper/OH addresses, but geometry success is not buffer submission proof. The original Request error cause remains unknown.

The peer independently viewed fullscreen 0s and 20s captures: a child carrying a large sack changes to an adult speaking beside the open rear of a vehicle, with different subtitles. All four screenshot hashes were verified and differ; the visual conclusion rests on content inspection, not hash difference alone. This proves content progress during this observation. Audio is not assessed by this review. Runtime cleanup and visual playback are recorded separately; no claim of complete first-error causal resolution is made.

Exact line excerpts, structured identities and frame hashes are in this package. Source-index paths refer to preserved original private evidence; the outer handles whole-window archival and final closure. This lane issued no device command.
