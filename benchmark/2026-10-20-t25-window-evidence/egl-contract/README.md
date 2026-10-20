# T25 EGL image import contract check

The T25 run crossed geometry and CPU buffer submission, then the selected EGL implementation returned no image. A missing image is not evidence that the native client object or target constant was wrong.

The exact HWUI `a11c9154` call uses `EGL_NO_CONTEXT`, Android target `0x3140`, and unprotected attributes `[0x30d2, 1, 0x3038]`. R23 converts its tracked OH native buffer to an OH native window buffer and changes only the target to `0x34e1`. A new focused REA query of exact `libnative_image.so` `74b6ea0d`, `OHOS::SurfaceImage::CreateEGLImage` (ELF `0x14ddc`, provider `0x114ddc`), confirms that the OH native implementation also uses context 0, target `0x34e1`, and those same attributes. The contracts agree at this boundary; driver acceptance remains unknown.

`selected=0` is a unique current-display match, not an EGL error. The exact HWUI null-image branch calls `eglGetError` at `0x5dc318` and passes it to `SkDebugf`; texture creation and binding occur later on the success branch. Recover that existing error and the exact buffer descriptor before changing format or target.

`results.json` includes exact source hashes, procedure locations, REA evidence ID, bounded-search limits, three next-step suggestions and all private raw file hashes. The new REA evidence bundle includes eight reused NativeImage records plus this one new function. HWUI evidence is a new focused LLVM disassembly, not a new REA analysis. No device calls or main-tree edits were made. No video pass is claimed.
