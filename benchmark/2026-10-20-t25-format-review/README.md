# T25 format and CPU-write boundary review

The current evidence does **not** establish format mapping as the cause of
the EGL image failure. In the selected raw prefix, four 576×1024/YV12 geometry
requests succeeded and three lock/unlock pairs reached successful flush.
The one R23 image-create attempt returned null with implementation index 0.
These results do not reveal the allocated buffer layout or validate its pixels.

Exact source paths, line ranges and SHA256 values are in
[source-index.json](source-index.json); original technical log lines and their
private source SHA are in [runtime-excerpt.json](runtime-excerpt.json).
[results.json](results.json) includes the actual production receipt's linked
object pins. No source change, build or device command was performed.

## Determined behavior

1. `geometry.c:10–25` maps Android YV12 (`0x32315659`) to OH enum 11,
   RGBX8888. Opcode 0 sets dimensions and opcode 3 sets format. This changes
   allocation configuration; it does not convert pixels or set usage.
2. R14 `window_module.c:54–85`, reached by T20, interprets OH11 as four bytes
   per pixel and returns Android format 2, pixel stride `byte_stride / 4`
   and the mapped pointer. It checks stride/size arithmetic. R15 copies the
   native handle's signed32 fields at +4/+8/+12/+16/+20. No YV12 scratch or
   pixel conversion is in this selected path.
3. T20 is the CPU-buffer access adapter, **not the decoder's pixel writer**.
   The player writes through the returned pointer. Its actual branch after
   receiving Android format 2 is not established by the adapter sources.
4. The related legacy `libandroid_webview_core_shim.c:745–797,818–825`
   preserves a YV12 request, allocates planar scratch, and converts at unlock.
   Its converter at 605–647 uses Y then V then U, with 16-byte-aligned chroma
   stride, writing packed RGBX into the OH allocation. T20 does not consume
   that private format ring. Reusing the allocation mapping alone does not
   reproduce this legacy behavior. This is source evidence, not a claim that
   the legacy path is the current producer or a validated replacement.
5. R23 `egl_import.c:57–86` changes target to OH native buffer `0x34e1` and
   forwards context and attributes. It does not convert format or change
   usage. `selected=0` means implementation index 0 was selected, not that
   selection failed. The wrapper records neither the precise driver error
   nor the buffer's format/usage.

## Unknowns that matter

| Object | Statically determined | Still unobserved for this frame |
|---|---|---|
| Geometry request | YV12 → OH RGBX8888; requested 576×1024 | Allocated buffer's actual configuration |
| CPU lock output | OH11 → Android2; four-byte pixel stride conversion | Actual returned format, stride, size and writer branch |
| Native handle | Exact surface getter offsets/widths are archived | Actual format/usage values; same-buffer link to import |
| EGL import | OH target, selected implementation, null result | Error, context/attributes and driver format/usage support |

For the exact surface object, getter evidence establishes format at raw handle
+0x14 (32 bits), usage at +0x18 (64 bits), stride at +0x08 (32 bits). These
offsets do not authorize reading an arbitrary pointer, prove its lifetime,
or supply live values. The present adapter only needs the established first
24 bytes and does not read usage.

## Minimal falsification, not a proposed fix

First inspect the **exact player** lock-return consumer: does it branch on
returned Android format 2 or write YV12 regardless? Do not substitute the
related legacy source. If a later bounded observation is authorized, record
that same owned transaction's Android output layout and native configuration,
then correlate the buffer to the import and its error/context/attributes.
Use the trusted bound getter for usage; do not add arbitrary tail reads.

A confirmed RGBX writer would falsify “missing YV12 conversion” for that
frame. A confirmed planar writer into a packed RGBX allocation would establish
a content-layout contract mismatch, but would still not by itself explain
why EGL rejected the image. Successful lock/flush does not prove correct
pixels, and equal dimensions do not prove CPU and import buffer identity.
