// Exact Android/Bionic fd_set FORTIFY entry points consumed by ZigZag.
// The three rejection conditions mirror AOSP 16 bionic_fortify.h.

#include <stddef.h>
#include <stdlib.h>
#include <sys/select.h>

_Static_assert(FD_SETSIZE == 1024, "Bionic fd_set descriptor limit drift");
_Static_assert(sizeof(fd_set) == 128, "Bionic fd_set layout drift");

static void CheckFdSet(int fd, size_t set_size)
{
    if (fd < 0 || fd >= FD_SETSIZE || set_size < sizeof(fd_set)) {
        abort();
    }
}

void __FD_SET_chk(int fd, fd_set *set, size_t set_size)
{
    CheckFdSet(fd, set_size);
    FD_SET(fd, set);
}

int __FD_ISSET_chk(int fd, const fd_set *set, size_t set_size)
{
    CheckFdSet(fd, set_size);
    return FD_ISSET(fd, set);
}
