# Provider ABI independent source review

**ACK: source table accepted; no production-provider admission.** All 11 pinned
references match local bytes. No compile, device call or R14 edit was performed.

- **BufferHandle:** source-no-key declaration lines25–38 and SDK-key declaration
  lines52–66 agree through virAddr: six signed32 fields at0/4/8/12/16/20,
  uint64 usage24, pointer32, ending at40. LP64 gives no-key phyAddr40,
  reserveFds48/reserveInts52/sizeof56; key profile key40 + padding, phyAddr48,
  reserveFds56/reserveInts60/sizeof64. Native691 oh61_buffer_handle.h:11–16
  independently contains assertions for the no-key tail. These are source-derived,
  not a newly executed ABI probe or proof that a live pointer is readable.
- **Stride:** external_window.h:144–153 documents byte stride and recommends
  BufferHandle; native_buffer.h:124–133 says bytes. native_window.cpp:432–439
  actually returns config.strideAlignment for GET_STRIDE. The table correctly
  rejects treating that alignment as the returned buffer stride.
- **Region:** external_window.h:88–98 declares xywh Rect and pointer/count Region;
  :501–502 passes Region by value. native_window.cpp:247–255 consumes each rect,
  :258–263 substitutes window-config geometry for an empty region. LTRB→xywh
  requires checked subtraction, positive bounded dimensions and a live temporary
  Rect through the synchronous call; passing ARect* or an R14 callback directly
  is incompatible. R14's full returned-buffer dimensions fit the stated conversion.

| Format | OH enum | Android enum | bytes/pixel |
|---|---:|---:|---:|
| RGBA8888 |12|1|4|
| RGBX8888 |11|2|4|
| RGB888 |13|3|3|
| RGB565 |3|4|2|
| BGRA8888 |20|5|4|
| RGBA16_FLOAT |39|0x16|8|
| RGBA1010102 |34|0x2b|4|

All seven agree with donor f12c:3927–3954. OH values were evaluated from the
explicit starting assignments and declaration order in buffer_common.h:285–397;
six Android values are explicit in installed NDK r23b hardware_buffer.h:65–102.
BGRA5 is in the locally archived generated Android AIDL PixelFormat.h:18; it is
not declared in that public AHardwareBuffer enum. This distinction is not a
numerical mismatch and does not establish actual provider format support.

**Version caveat:** the pinned local native_buffer.h itself contains `@since 23`
at58–61. An `openharmony-6.1.0.31` directory name does not establish its upstream
revision. The table already limits it to declarations and leaves deployed
provider/lifetime unknown; preserve that qualification. No observed live stride,
format, ownership or callable instance is added by this review.

Exact source paths, line ranges and full SHA values are in results.json (the 11
original references plus the enum/donor sources). No source-table arithmetic or
signature discrepancy was found; production binding still requires separate evidence.

## Repository source delivery

The two Apache-2.0 originals are copied byte-for-byte, including copyright notices:
[OH buffer_common.h](sources/oh/buffer_common.h) and
[NDK r23b hardware_buffer.h](sources/android-ndk-r23b/hardware_buffer.h).
The existing generated PixelFormat.h has no license notice. Only its required
[BGRA_8888 enum line](sources/android-generated/PixelFormat.BGRA_8888.excerpt.txt)
is retained, verbatim from line18; no complete generated header or invented license.
Original source aliases, whole-file SHA, excerpt SHA and generation limitations
are recorded in [source-delivery.json](source-delivery.json).

The original reviewed table hashes remain in results.json, and the exact original
review is preserved under history/. The ef76ee1b7c table hashes are recorded
separately. Its three newly vendored provider headers were independently checked
byte-identical to their original references; only the equivalent repository paths
are adopted. This does not add deployed ABI/version evidence or change R14.
