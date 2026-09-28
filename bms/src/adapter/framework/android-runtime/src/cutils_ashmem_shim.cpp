/*
 * cutils_ashmem_shim.cpp — adapter implementation of the two libcutils ashmem
 * entry points referenced by android_database_SQLiteConnection.cpp and
 * androidfw/CursorWindow.cpp.
 *
 * OH/musl has no /dev/ashmem and the cross-compiled libcutils does not export
 * ashmem_* (verified: readelf libcutils.so → 0 ashmem symbols).  ashmem here is
 * only used to obtain a file-backed, mmap(MAP_SHARED)-able region for
 * CursorWindow inflation and for SQLiteConnection blob-fd streaming.  A
 * memfd-backed region provides identical semantics (anonymous, RAM-backed,
 * shareable via fd) without the ashmem driver.
 *
 * ashmem_set_prot_region is a no-op: on real ashmem it only shrinks the prot
 * mask for FUTURE mmaps and never down-protects an already-established mapping,
 * which is exactly the path CursorWindow::maybeInflate relies on (it mmaps RW,
 * then "sets" PROT_READ, then still memcpys into the live RW mapping).
 *
 * HanBing 铁律 3 compliant: native adapter glue, no ART involvement.
 */

#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <stddef.h>

#ifndef __NR_memfd_create
#  if defined(__aarch64__)
#    define __NR_memfd_create 279
#  endif
#endif

#ifndef MFD_CLOEXEC
#  define MFD_CLOEXEC 0x0001U
#endif

extern "C" {

int ashmem_create_region(const char* name, size_t size) {
    int fd = -1;
#ifdef __NR_memfd_create
    fd = (int)syscall(__NR_memfd_create, name ? name : "adapter-ashmem",
                      MFD_CLOEXEC);
#endif
    if (fd < 0) {
        // Fallback: anonymous temp file under /data/local/tmp (RAM-ish, unlinked).
        char tmpl[] = "/data/local/tmp/adapter-ashmem-XXXXXX";
        fd = mkstemp(tmpl);
        if (fd < 0) return -1;
        unlink(tmpl);
    }
    if (ftruncate(fd, (off_t)size) < 0) {
        int e = errno;
        close(fd);
        errno = e;
        return -1;
    }
    return fd;
}

// No-op: see file header. Existing mappings are never down-protected by ashmem.
int ashmem_set_prot_region(int /*fd*/, int /*prot*/) {
    return 0;
}

}  // extern "C"
