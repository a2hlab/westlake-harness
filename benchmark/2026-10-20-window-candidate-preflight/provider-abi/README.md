# R14 injected OH operations: ABI source table

**ABI_REFERENCE_ONLY_NOT_A_PROVIDER_OR_DEPLOYMENT_CANDIDATE.** The R14 host callback interface is not an OH ABI and none of its callbacks is implemented here. This read-only audit uses master `3f429fd5ba`, its existing exact-ELF reviews, the archived OH6.1 window source/header, and already-present local OH6.1-profile headers. It does not use a current SDK header as proof of the deployed firmware. Helpful key remains **toutiao, conditional**; current playback and provider admission are unknown.

[results.json](results.json) records the eight operation signatures, layout values and missing runtime evidence. [source-index.json](source-index.json) pins 11 references with SHA and master blobs where available. The three formerly external public headers are now copied byte-for-byte under [source-profile/](source-profile/metadata.json), with their original notices and [full Apache-2.0 license](source-profile/LICENSE). Original locations remain `$WORKSPACES` aliases in the index; no personal absolute path is published. The OH6.1-labelled directory alone does not prove an upstream revision. These declarations remain source-profile evidence, not deployment evidence. The index’s `in_master` fields describe its original `master_commit`; the new copies are delivered for subsequent master landing.

## What is exact and what remains unbound

| Callback | Source authority | Required adapter / limit |
|---|---|---|
| unwrap | Master `static/r10-window-contract-review/bridge-unwrap.stdout.txt`, exact d4fa SHA `d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b`, entry0x125a00 | Actual function returns a pointer, while R14 returns int and writes `void**`. It checks `_wnd` at0 and ANW1 at0xc8, returns pointer0xc0; no directPathLive. R13 call object and resolver instance remain unbound. |
| request | `benchmark/2026-10-01-n9-first-damage/upstream/native_window.cpp:205–234` and paired header | int32 request(window,buffer**,int*fence). R14 adds ctx; use a typed thunk, not a cast. Actual loaded OH provider SHA/instance unknown. |
| handle | Same source:558–564; local BufferHandle declarations | Returns pointer, not R14's int+output-record. Validate pointer then copy/widen individual signed fields. No whole-struct reinterpretation. |
| FromNativeWindowBuffer | [Copied SDK-C native_buffer.h](source-profile/sdk-c/native_buffer/native_buffer.h):267–280 | int32 convert(windowBuffer,nativeBuffer**). Declaration found; no exact deployed provider/disassembly or borrowed-reference proof found. R14's borrowed assumption requires an actual provider contract. |
| Map / Unmap | Same header:215–241 | int32 Map(nativeBuffer,void**), int32 Unmap(nativeBuffer). Must preserve separate rc/non-null evidence and pairing. Real provider SHA/namespace and cache/lifetime semantics unknown. |
| Flush | Archived OH window source:237–280 and header Region:88–98 | int32 flush(window,buffer,int fence,**Region by value**). R14 callback accepts a rectangle pointer and ctx: a typed conversion wrapper is mandatory. |
| Abort | Archived source:322–329 and weak alias:1132 | int32 abort(window,buffer); wrapper calls CancelBuffer but drops its lower return. API rc0 cannot by itself certify lower queue ownership completion. Actual board implementation still unbound. |

The archived window source receipt identifies graphic_surface revision `0bf226a1f0a79fdbad70a0ac5565002ce69e942c` and a **historical** system ELF `8f1879f8…f4a3`; that is not a current R13 native-window identity. The main-tree R10 provider receipt pins libandroid765 and webview-shim85, not the system native-buffer/window providers. Their mapped presence or exported names cannot fill this gap.

## BufferHandle: do not import a tail-layout mistake

The existing source profile `sources/api-implementations/source-build-native691/westlake/native/hwui/oh61_buffer_handle.h:7–17` explicitly warns against the SDK's extra shared-memory `key`. The [copied source declaration](source-profile/graphic-surface/buffer_handle.h) and [copied SDK-C declaration](source-profile/sdk-c/native_window/buffer_handle.h) preserve the observed mismatch:

| AArch64 LP64 field | Common offset | Type |
|---|---:|---|
| fd / width / stride / height / size / format | 0 / 4 / 8 / 12 / 16 / 20 | six signed int32 |
| usage | 24 | uint64 |
| virAddr | 32 | pointer |

The common prefix is40 bytes. The source no-key profile has phyAddr40, reserveFds48, reserveInts52, sizeof56. The SDK-C header has key40, phyAddr48, reserveFds56, reserveInts60, sizeof64. These are source-derived layouts, not a compiled layout check or actual-buffer read. The local mirror's native_buffer.h was not used: its newer API additions and unbound revision are not authority for this OH6.1 target.

R14 `r14_handle` instead holds **int64 width,height,stride_bytes,size_bytes + int32 format**. A future handle callback must select the exact provider profile and load the common signed32 fields individually, then widen; it must not cast/copy `sizeof(r14_handle)` from the OH pointer. Negative, zero or overflowing dimensions/size/stride are rejected by the admitted module contract, not normalized into success.

## Stride units and region conversion

The archived window header's GET_STRIDE documentation states bytes and directs callers to BufferHandle. The existing SDK-C NativeBuffer_Config also marks stride bytes at line132. However the archived implementation's HandleNativeWindowGetStride (`native_window.cpp:432–439`) returns **strideAlignment**, so GET_STRIDE is not a replacement for a returned buffer's actual stride. The handle callback supplies bytes unchanged to `r14_handle.stride_bytes`; pixel-stride conversion belongs to R14 after format/bytes-per-pixel, divisibility and range checks. Actual returned stride and pixel format remain unobserved.

OH `Rect` is `{int32 x,y; uint32 w,h;}` and Region is `{Rect *rects; int32 rectNumber;}`: source-derived LP64 sizes16 and16, Region pointer at0/count at8. R14 `r14_rect` is **left,top,right,bottom**. Its flush thunk must validate bounds and construct xywh (`w=right-left`, `h=bottom-top`) plus count1, then pass Region **by value**; passing the ARect pointer as Region or directly assigning the OH function to `r14_ops.flush` is an ABI error. R14 supplies fence=-1 and a full returned-buffer rectangle. Do not silently switch to `{NULL,0}`: archived OH source:258–263 uses window-config dimensions for that fallback, which may differ from returned-buffer dimensions.

## Actual evidence still required

1. R13 must bind the video caller's current wrapper to its fromSurface/lock call under the same boot and child birth; both unwrap magic checks and the OH pointer are needed. NULL is not proof of raw OH.
2. For every injected operation, record its callable address, exact ELF SHA, load bias, symbol and namespace instance. Verify actual native-window/native-buffer versions and ABI; do not reuse current source identities or same-name libraries as proxies.
3. Bind the returned BufferHandle layout/fields and native-buffer lifetime to that provider. In particular conversion being borrowed, failure ownership and real stride/format require provider evidence beyond a header declaration.
4. Request/fence/map/unmap/flush/abort results must form the paired ownership journal; then real consecutive video frames and sound must establish playback. Host tests, a successful callback return or queue acceptance do not satisfy that gate.

No implementation, tests, binary, provider resolver or installation plan is produced. The source copies are unmodified public header evidence; they do not supply native_buffer.h’s transitive buffer_common.h dependency and are not a standalone build kit. The earlier preflight and edge-contract files are unchanged.
