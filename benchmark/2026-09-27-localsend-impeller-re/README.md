# 2026-09-27 LocalSend libflutter pc=0 RE (#48 horizontal)
RE of the LocalSend first-frame crash (evidence in westlake-harness/benchmark/2026-09-27-localsend-bringup).
Root cause: Impeller (GLES, default in this build — "opt-out deprecated") calls a NULL extension GL
proc on the raster thread — slot #468 (offset 0xea0) of the .bss GLES ProcTable at 0xaee000, in the
extension region past the main filler's #3512 end; the proc resolved NULL via eglGetProcAddress on OH's
GLES driver and Impeller called it unconditionally. Fix: disable Impeller (Skia GL fallback, defensive)
or --enable-software-rendering; pin the exact proc via an eglGetProcAddress logger for a targeted shim.
See NOTES.md.
