#ifndef WESTLAKE_MUSL_TGKILL_COMPAT_H
#define WESTLAKE_MUSL_TGKILL_COMPAT_H

#include <signal.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef SYS_tgkill
#ifdef __NR_tgkill
#define SYS_tgkill __NR_tgkill
#else
#error "target sysroot does not expose tgkill syscall number"
#endif
#endif

static inline int westlake_musl_tgkill(pid_t tgid, pid_t tid, int signal_number)
{
    return (int)syscall(SYS_tgkill, tgid, tid, signal_number);
}

// Bionic exposes tgkill() from <signal.h>; the selected OH musl sysroot does
// not.  Translate only this source-level boundary and keep the kernel ABI.
#define tgkill westlake_musl_tgkill

#endif
