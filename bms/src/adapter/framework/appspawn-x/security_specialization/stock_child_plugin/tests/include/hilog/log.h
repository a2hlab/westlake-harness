#ifndef WESTLAKE_TEST_HILOG_LOG_H
#define WESTLAKE_TEST_HILOG_LOG_H

#define LOG_CORE 0
#define LOG_INFO 0

static inline int HiLogPrint(int type, int level, unsigned int domain,
                             const char *tag, const char *format, ...)
{
    (void)type;
    (void)level;
    (void)domain;
    (void)tag;
    (void)format;
    return 0;
}

#endif
