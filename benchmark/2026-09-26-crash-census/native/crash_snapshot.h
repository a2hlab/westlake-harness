#pragma once
#include <signal.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Call after fork and before enabling the observer; directory must already exist.
 * No handler is installed. Initialization is deliberately outside signal context. */
int wl_crash_snapshot_init(const char *directory);
/* Records only; preserves errno and the supplied siginfo/ucontext bytes.
 * Bounded capture, not an assertion that DWARF unwinding succeeded. */
void wl_crash_snapshot(int signal_number, const siginfo_t *info, const void *context);
#ifdef __cplusplus
}
#endif
