# fd-libre cluster-6 "libnativewindow SIGSEGV" — re-diagnosed: it is an FDSAN fd-ownership abort in dlopen, NOT ANativeWindow

## Correction of the label
The U14 cluster label `signal-SIGSEGV|libnativewindow.z.so` for fd-libre is a **false match**: my `fault_lib` regex
matched a `/vendor/lib64/libnativewindow.z.so` line in the crash log's **memory-map** section, not the fault stack.
libnativewindow does NOT appear in the fault thread's backtrace. The real terminal is a **DEBUG SIGNAL(FDSAN)** abort, not
a raster SIGSEGV.

## The actual crash (U14 window1, `movers-fd-libre-1`, board 5cd; appspawn-x pid 5994, thread deckers.thibaul)
```
Reason: Signal:DEBUG SIGNAL(FDSAN)
LastFatalMessage: attempted to close file descriptor 61, expected to be unowned, actually owned by FILE* 0x0000007f9bc1e6e8
#00 ld-musl-aarch64.so.1  fdsan_error+768            (build-id a9d01819)
#01 ld-musl               fdsan_close_with_tag+688
#02 ld-musl               close+16
#03 ld-musl               load_library_header+1192
#04 ld-musl               preload_direct_deps+792
#05 ld-musl               preload_deps+152
#06 ld-musl               dlopen_impl+2396
#07 /system/bin/appspawn-x  StockOpenNamespace+208   (build-id 2a0b397c)
#08 libapp_native_loader.so ANL_Dlopen+1104          (route-a 74d1d6d4…)
#09 libnativeloader.so      westlake::nativeloader::Registry::Open+1732
#10 libnativeloader.so      OpenNativeLibrary+548
#11 libart.so               JavaVMExt::LoadNativeLibrary+2112
#12 libopenjdkjvm.so        JVM_NativeLoad+348
```

## Mechanism (why FDSAN aborts)
OH musl has fdsan (fd-ownership sanitizer). `load_library_header` opens the app's native `.so`, reads the ELF header, and
`close()`s the fd with the **unowned** tag (a plain loader close). But fdsan has fd 61 recorded as **owned by a `FILE*`**
(`0x7f9bc1e6e8`). A raw close of a FILE*-owned fd → fdsan fatal.

An fd cannot be two live owners at once, so this is a **stale fdsan tag after fd reuse**: a `FILE*` (fopen/fdopen) owned
fd 61 and claimed the fdsan tag; the `FILE*` was closed and fd 61 freed, but the **fdsan ownership tag was not cleared**;
the loader then `open()`ed the `.so`, got the recycled fd 61, and its `close()` tripped the leftover FILE* tag. (The
FILE*-owned tag is exactly what bionic/musl stdio sets via `__fsetlocking`/fdsan on `fdopen`; the leak is on the FILE*
teardown path.)

## Is it our ANativeWindow adapter? NO.
The stack is pure native-library-load: `JVM_NativeLoad → LoadNativeLibrary → OpenNativeLibrary → Registry::Open →
ANL_Dlopen → StockOpenNamespace → musl dlopen_impl → load_library_header → close`. There is **no `oh_anw_get_oh`, no
AdapterAnw/ANW1, no OHNativeWindow** anywhere. The outer's hypothesis (ANW1 wrapper pointer handed to an OH window) is
**refuted** — this is an fd-ownership/stdio bug in the dlopen path, unrelated to the surface adapter.

## Where the bug lives + fix
- **Not libnativewindow; not the ANW adapter.** The owning `FILE*` tag outliving its fd is a **stdio/fdsan teardown**
  issue. On route-A the fdsan tagging surface we ship is `libbionic_compat` (it exports the `android_fdsan_*` API the
  bionic NDK app uses). Candidate fixes, in order:
  1. **Clear the fdsan ownership tag on FILE* close** — ensure `fclose`/the FILE* teardown resets fd 61's fdsan tag to
     unowned before releasing the fd (so a later loader `close()` of the recycled fd does not see the stale FILE* tag).
     Check `libbionic_compat` stdio/fdsan shim and OH musl `fclose`.
  2. If the tag belongs to musl stdio (not our shim), this is an **OH musl `fclose`/fdsan** defect → record for upstream;
     a route-A workaround is to have the loader `close()` with the FILE* tag family, or to `android_fdsan_exchange_owner_tag`
     the fd to unowned before loader close.
- Static next step (offline): disassemble OH musl `fclose`/`__stdio_close` (build-id a9d01819) and the `libbionic_compat`
  fdsan path to see whether the fdsan tag is cleared on FILE* close; and `load_library_header`'s `open→close` to confirm
  it uses the unowned tag.

## Predicted move
- **+1 (fd-libre)** IF the stale-tag teardown is fixed — but note it is an **fd-reuse RACE** (the crash needs fd 61 to be
  recycled from a just-closed FILE* into the loader), so it is **intermittent**; one green run would not prove it fixed,
  and other apps that fopen then load a native lib could hit it too.
- Owner: route-A native-load / stdio-fdsan (libbionic_compat or OH musl), **NOT** the ANativeWindow adapter and NOT a
  Flutter/eb90 item. Not in the current U17 batch.
