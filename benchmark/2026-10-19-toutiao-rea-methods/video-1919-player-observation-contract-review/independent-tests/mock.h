#ifndef PLAYER_ORACLE_MOCK_H
#define PLAYER_ORACLE_MOCK_H
#include <stdarg.h>
#include <stddef.h>
#include <sys/types.h>
int oracle_vprint(int, const char *, const char *, va_list);
ssize_t oracle_write(int, const void *, size_t);
#endif
