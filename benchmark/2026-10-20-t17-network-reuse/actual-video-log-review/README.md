# T17 observed video stages after paired network binding

The old network failure must not be reused as the current first wall. Exact
5cd child 7906/b15460, parent6067/b14025, boot5807db3d has a successful paired
media getaddrinfo/freeaddrinfo sample into exact f6. The complete captured log
interval [9297968,40929709) is 31,631,741 bytes, SHA
4c4893c463f2074619ef580c7b1179afbcaade65b9d3f03d8f8a1e7884c289eb.
This review reads those bytes only; it does not execute device commands.

| Source byte offset | Exact observed event | Interpretation limit |
|---:|---|---|
| 9443561 | TTPlayer JNI_OnLoad | Initialization reached, not playback. |
| 9504346 | ByteVC1 decoder created | Construction, not decoded frames. |
| 9517559 | `open file ok start read packet.` | Input-open/read stage reached. |
| 9517820 | Video decoder pipeline constructed | Decoder object, not output frame. |
| 9526140 | Audio graph constructed | Not audible output. |
| 9622228 | Factory output ANativeWindow=0x7e67522cd0, prewrapped=0 | Historical pointer in this child; no lifetime/caller/winner proof. |
| 9625791 | `ANativeWindow_lock: CPU rendering path not implemented` | Real unsupported-path diagnostic; no lock argument/caller/rc supplied. |
| 9636343, 31543238, 40140450 | Missing `android.media.AudioTrack.native_get_buffer_size_frames()` | Each has UnsatisfiedLinkError and AudioTrack.getBufferSizeInFrames → AJVoice.initAudioTrack stack. This is the concrete repeated audio JNI gap. |

There are zero literal `ff_listen_connect2` occurrences in this interval. There
are 254 mirrored WL-TTLOG lines; their last is at offset9526846. The existing
mirror cap prevents interpreting later silence as successful networking,
decoding or rendering. The ANW message and three later JNI exception groups are
not a global earliest-fatal proof. No URL/configuration body is copied here.
`excerpt-index.json` binds 26 exact technical lines to original source offsets,
lengths and hashes; the original range remains in the private window archive.

The smallest next work is to reuse the missing AudioTrack JNI method against
the actual selected media implementation while an already admitted observer
captures the real ANW call/object boundary. Do not rebuild networking, replace
the large shim, assume a wrapper type, or return a guessed size. If the observer
is not admitted for this window, keep the existing rollback deadline and use a
separate bounded window. A short same-item frame sequence, pause/resume and audio
observation are still needed: the outer's two different scenes could be autoplay
or an item transition and are not enough to sign continuous playback.
