# Bounded Mali OH EGL image format gate

The earlier analysis had no content-bound Mali artifact and therefore could not identify a driver rejection condition. This pass analyzes the current restored driver only. It does **not** retroactively prove the historical T25 bytes or live buffer format.

The exact 16,734,912-byte driver SHA-256 is `e0cb108121981c6ad30c9e3f338c384172ef3be2dc790a457e0287a10efa2cfe`. Collection before/after SHA and stat match; the offline lane performed zero device operations.

## Evidence and result

Actual REA/Ghidra analyzed exactly two complete functions, then exported the bundle and closed the session:

- `eglCreateImageKHR`: ELF `0x33e814`, provider `0x43e814`, 848 bytes; Evidence `ev_df813acba30aa55389f3a5c7c522def614ce26cc21ef26aa4ba8c421e5585139`.
- Its direct `eglCreateImageKHRImpl`: ELF `0x33ded0`, provider `0x43ded0`, 2,372 bytes; Evidence `ev_f59c0ad6ef22cc9e339082d70354914e21ca43ede854e4b7b6793193732aea91`.

Independent LLVM disassembly of the first function agrees with REA. For OH target `0x34e1`, the wrapper obtains the buffer handle and reads its 32-bit field at `+0x14`. The pinned OH reference header identifies this as `format` (`usage` is `+0x18`). The only admitted values are **3, 12, 13, 20, 24, 25, 28, 29**. Other values, including **11**, return NULL before the core implementation. The entry does not read usage or explicitly set an EGL error on this early branch; getter side effects were not examined.

Supported values produce dma-buf attributes and reach the core with target `0x3270`, a null client buffer, and the original display/context. Format 12 produces FOURCC `0x34324241`. The core then validates and imports; success is not established by passing the wrapper. Original `IMAGE_PRESERVED=1` does not violate the core's local value check (values greater than 1 are rejected), but other validators/importers remain outside scope.

## T26 prediction and boundaries

If the actual runtime format is 11 **and** the actual create function is this exact public entry, NULL is inevitable. Geometry requesting OH11 alone proves neither premise. Format12 avoids this particular rejection, but pixel storage and conversion must match; retagging alone is not a fix. Record actual function address/provider and public buffer metadata during the already-planned experiment. Do not claim the historical T25 root cause or video acceptance from this static result.

The full raw bundle, reusable snapshot, original LLVM output, identity receipts and reference header are private persistent artifacts. `results.json` lists their exact hashes. No main-tree changes, new device reads, downloads or third function analysis occurred.
