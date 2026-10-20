# T29 initial RequestBuffer 40601000: bounded static review

**40601000 is `GSERROR_NO_BUFFER` / `SURFACE_ERROR_NO_BUFFER`. The exact client implementation preserves a lower request/reply status. The server-side condition in this window remains unknown.** This review performs no device call, build, runtime change or namespace attribution. It does not diagnose the subsequent retained-cache failure.

## Evidence and distinction

The local OH header defines 40001000 as invalid arguments, 40601000 as no buffer, 40605000 as no buffer ready, 41202000 as no consumer, and 41211000 as consumer disconnected ([enum excerpt](enum.excerpt.txt), original `graphic_common_c.h:30–58,101`). These are distinct values, not spelling variants. Header source identity and every excerpt's original SHA are in [source-index.json](source-index.json). The headers are an OH6.1-labelled local snapshot, not a claimed exact source rebuild of the deployed library.

The deployed `libsurface.z.so` is SHA **8f1879f82a307d3a95555067575132918a05244fbdeee1c2f2db37834a58f4a3**. Existing NativeWindowRequestBuffer REA evidence `ev_71bca393…d4651` shows its surface virtual request at ELF0x671ec propagates the error; its invalid-input path uses40001000. New exact-ELF LLVM confirms:

- [ProducerSurface](producer-locked.llvm.txt): 0x6e0c0 calls producer vtable+0x20; 0x6e0c8 saves the returned status; 0x6e1bc returns it. The special cleanup at0x6e0e4–0x6e118 tests the41202 error category, not40601. This is not the no-consumer cleanup branch.
- [BufferClientProducer](client-request.llvm.txt): 0x331fc sends the request; after transport success,0x33210 reads an Int32 reply,0x3321c preserves a nonzero result, and0x332f4 enters return cleanup. Transport errors also have a return path. Thus a server reply is a concrete static propagation route, **not proof that this particular call used that route**; the actual IBufferProducer virtual target was not sampled.
- [Disconnect](disconnect.llvm.txt): ProducerSurface's disconnect state handling and CleanAllLocked are separate. Seeing a TextureView destroy record does not prove that this function was invoked.

## What the observed transition proves

[timeline.excerpt.txt](timeline.excerpt.txt) retains only technical WL-R29 lines from the fixed33,093,780-byte prefix; its full original SHA is indexed.

| Monotonic ns | Actual event |
|---|---|
|250797426396|consumer destroy: old OH7eef2e2790; unref called/valid/rc=`1/1/0`|
|250798932896|consumer create: returned OH7eef2e2790; ref called/valid/rc=`1/1/0`|
|253905229201|CPU request: wrapper7dadc6f3d0; OH7eef2e2790; Q=`1/1/40601000`; rc=-5; failure_stage37|

The first failed request did not reach handle/native-buffer/map/fence/flush. The later cache error cannot explain the origin of this earlier request status. The3.106296305-second create-to-error interval is **not a measured RequestBuffer duration** and does not prove a timeout.

The actual consumer source ([excerpt](consumer.excerpt.txt), original `oh_texture_view_jni.cpp:69–133`) unrefs the old window, clears the Java field, obtains a native window from the SurfaceTexture, refs it and stores the field. It contains no direct Connect/Disconnect call in this sequence. An unref rc0 does not establish final object destruction; a returned identical address does not establish either a new allocation or persistent identity. The logger's `key/ep` are diagnostic address/config bookkeeping ([excerpt](logger-epoch.excerpt.txt), original `observe29c.c:63–99`), **not server connection generations**. Both server identity and queue continuity remain unknown.

## Supported possible path; remaining source gap

`producer_surface.h:707–722` documents a concrete NO_BUFFER case: in nonblocking mode, all buffers have been requested and none is flushed. This supports that condition as a possible path only; this window has not proven the active mode, request timeout, queue size or free/requested/flushed/acquired counts. `:797–818` instead documents strict disconnect returning CONSUMER_DISCONNECTED. Neither a connection-generation change nor an allocation failure follows from40601000 alone.

The local mirror contains the relevant declarations but no matching queue implementation CPP. A bounded read of the known remote OH tree (`buffer_queue.cpp`, `buffer_queue_producer.cpp`, `producer_surface.cpp`, `buffer_client_producer.cpp`) was blocked with SSH rc255/Operation not permitted. Exact argv is retained privately at `.private/remote-source.argv.json` for the outer channel; no retry or permission bypass occurred. A new REA request also returned provider_unavailable/rc1; the existing successful wrapper REA and three new LLVM calls/rc0 are retained separately. No source branch was invented to fill these gaps.

The smallest remaining static closure is those four existing source files with revision/SHA, focused on all NO_BUFFER returns and queue connection/reset rules. A source match would establish possible conditions, not retroactively establish the live queue state. This result does not propose new device experiments or alter CC's separate retained-cache repair.
