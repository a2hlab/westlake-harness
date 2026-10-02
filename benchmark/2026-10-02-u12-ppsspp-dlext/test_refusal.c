#include "inputs/android_dlopen_ext.c"

int main(void) {
    android_dlextinfo info = {0};
    info.flags = 0x200;
    errno = 0;
    if (android_dlopen_ext("unreachable", RTLD_NOW, &info) != NULL || errno != ENOTSUP) return 1;
    info.flags = 0x210;
    info.library_fd = -1;
    errno = 0;
    if (android_dlopen_ext("unreachable", RTLD_NOW, &info) != NULL || errno != ENOTSUP) return 2;
    return 0;
}
