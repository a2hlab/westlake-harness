#include <signal.h>

#ifndef WESTLAKE_EXPECT_SIGSET_SIZE
#error WESTLAKE_EXPECT_SIGSET_SIZE is required
#endif

#ifndef WESTLAKE_EXPECT_SIGACTION_SIZE
#error WESTLAKE_EXPECT_SIGACTION_SIZE is required
#endif

_Static_assert(sizeof(sigset_t) == WESTLAKE_EXPECT_SIGSET_SIZE,
               "sigset_t ABI drifted");
_Static_assert(sizeof(struct sigaction) == WESTLAKE_EXPECT_SIGACTION_SIZE,
               "struct sigaction ABI drifted");

int westlake_signal_abi_probe(void)
{
    return (int)(sizeof(sigset_t) + sizeof(struct sigaction));
}
