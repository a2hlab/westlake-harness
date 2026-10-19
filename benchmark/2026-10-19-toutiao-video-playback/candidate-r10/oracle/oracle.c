/* Black-box host oracle; no player/Android headers or implementation internals. */
#include "mock.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sched.h>

extern int __wl_ttlog_00000659(int, const char *, const char *, ...);
static _Atomic int calls, writes, violations;
static _Thread_local int filtered, alias_case, write_mode;
static _Thread_local int expected_priority, expected_errno;
static _Thread_local const char *expected_tag, *expected_format;
static _Atomic size_t bytes;
static _Thread_local char backend_text[8192], mirror[2048];

#define CHECK(x) do { if (!(x)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); ++violations; \
} } while (0)

int oracle_vprint(int priority, const char *tag, const char *fmt, va_list ap) {
    int incoming = errno;
    ++calls;
    CHECK(priority == expected_priority);
    CHECK(tag == expected_tag); /* Preserve null and exact original arguments. */
    CHECK(fmt == expected_format);
    CHECK(incoming == expected_errno);
    if (filtered) { errno = incoming; return -1; }
    if (alias_case) {
        /* printf("%s%hhn", s, s): read string first, then store length.
         * Explicit mock avoids host-libc restrictions on dynamic %n. */
        const char *s = va_arg(ap, const char *);
        signed char *n = va_arg(ap, signed char *);
        size_t length = strlen(s);
        CHECK(length < sizeof(backend_text));
        if (length < sizeof(backend_text)) memcpy(backend_text, s, length + 1);
        *n = (signed char)length;
    } else {
        va_list copy;
        va_copy(copy, ap);
        vsnprintf(backend_text, sizeof(backend_text), fmt, copy);
        va_end(copy);
    }
    /* Deliberately non-production return/errno exposes invented return values. */
    errno = EBUSY;
    return 37;
}

ssize_t oracle_write(int fd, const void *data, size_t length) {
    ++writes;
    CHECK(fd == 2);
    CHECK(length <= 1024);
    bytes += length;
    if (length < sizeof(mirror)) {
        memcpy(mirror, data, length);
        mirror[length] = 0;
    }
    errno = EIO; /* Even a successful mirror must not leak errno. */
    if (write_mode == 1) { errno = EINTR; return -1; }
    if (write_mode == 2) return length ? (ssize_t)length - 1 : 0;
    return (ssize_t)length;
}

static void expect(int priority, const char *tag, const char *fmt) {
    expected_priority = priority;
    expected_tag = tag;
    expected_format = fmt;
    expected_errno = ENOENT;
    errno = expected_errno;
}

static void returned(int result) {
    int actual_errno = errno;
    CHECK(result == (filtered ? -1 : 37));
    CHECK(actual_errno == (filtered ? expected_errno : EBUSY));
}

static _Atomic int thread_ready, thread_go;
static void *concurrent_calls(void *arg) {
    int id = *(int *)arg;
    atomic_fetch_add(&thread_ready, 1);
    while (!atomic_load(&thread_go)) sched_yield();
    for (int i = 0; i < 1024; ++i) {
        char expected[80];
        snprintf(expected, sizeof expected, "thread=%d iteration=%d", id, i);
        expect(4, "thread-oracle", "thread=%d iteration=%d");
        returned(__wl_ttlog_00000659(4, expected_tag, expected_format, id, i));
        CHECK(!strcmp(expected, backend_text));
    }
    return NULL;
}
static void exhaust_budget(void) {
    for (int i=0; i<4096; ++i) {
        expect(4, "budget", "reserve=%d");
        returned(__wl_ttlog_00000659(4, expected_tag, expected_format, i));
    }
    CHECK(calls == 4096 && writes == 4096);
}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    const char *name = argv[1], *tag = "oracle-tag";
    if (!strcmp(name, "filtered-n-after-cap") || !strcmp(name, "alias-n-after-cap")) {
        exhaust_budget();
        name = !strcmp(name, "filtered-n-after-cap") ? "filtered-n" : "alias-n";
    }
    int initial_calls=calls, initial_writes=writes;
    if (!strcmp(name, "mixed")) {
        const char *fmt = "i=%d u=%u ll=%lld f=%.*f s=%*.*s %%";
        char expected[256];
        snprintf(expected, sizeof(expected), fmt, -17, 42u, 1234567890123LL,
                 3, 1.25, 8, 3, "abcdef");
        expect(4, tag, fmt);
        returned(__wl_ttlog_00000659(4, tag, fmt, -17, 42u, 1234567890123LL,
                                    3, 1.25, 8, 3, "abcdef"));
        CHECK(calls == 1 && writes == 1);
        CHECK(!strcmp(backend_text, expected));
        CHECK(strstr(mirror, expected) != NULL);
    } else if (!strcmp(name, "filtered-n")) {
        int n = 123; signed char hn = 67; long ln = 789;
        const char *formats[] = {"abc%n", "abc%1$n", "abc%hhn", "abc%ln"};
        filtered = 1;
        for (int i = 0; i < 4; ++i) {
            int before = writes;
            expect(2, tag, formats[i]);
            if (i == 2) returned(__wl_ttlog_00000659(2, tag, formats[i], &hn));
            else if (i == 3) returned(__wl_ttlog_00000659(2, tag, formats[i], &ln));
            else returned(__wl_ttlog_00000659(2, tag, formats[i], &n));
            CHECK(n == 123 && hn == 67 && ln == 789);
            CHECK(writes - before <= 1); /* Fixed skipped marker is optional. */
        }
        CHECK(calls == initial_calls + 4);
    } else if (!strcmp(name, "alias-n")) {
        signed char text[] = "ABCDE";
        const char *fmt = "%s%hhn";
        alias_case = 1;
        expect(4, tag, fmt);
        returned(__wl_ttlog_00000659(4, tag, fmt, (char *)text, text));
        CHECK(calls == initial_calls + 1 && writes - initial_writes <= 1);
        CHECK(!strcmp(backend_text, "ABCDE"));
        CHECK(text[0] == 5);
    } else if (!strncmp(name, "limit-", 6)) {
        int count=atoi(name+6); CHECK(count>=4095 && count<=4097);
        const char *fmt = "count=%d";
        for (int i = 0; i < count; ++i) {
            int before = writes;
            expect(4, tag, fmt);
            returned(__wl_ttlog_00000659(4, tag, fmt, i));
            CHECK(calls == i + 1);
            CHECK(writes - before == (i < 4096 ? 1 : 0));
        }
        CHECK(writes == (count<4096 ? count:4096) && bytes <= 4096u * 1024u);
    } else if (!strcmp(name, "concurrent")) {
        pthread_t threads[8]; int ids[8];
        for(int i=0;i<8;++i) { ids[i]=i; if(pthread_create(&threads[i],NULL,concurrent_calls,&ids[i])) return 3; }
        while(atomic_load(&thread_ready)!=8) sched_yield();
        atomic_store(&thread_go,1);
        for(int i=0;i<8;++i) CHECK(pthread_join(threads[i],NULL)==0);
        CHECK(calls==8192 && writes==4096 && bytes<=4096u*1024u);
    } else if (!strcmp(name, "errno-m")) {
        char expected[256]; const char *fmt="saved=%m";
        expect(4, tag, fmt); snprintf(expected,sizeof expected,fmt);
        expect(4, tag, fmt); returned(__wl_ttlog_00000659(4,tag,fmt));
        CHECK(!strcmp(backend_text,expected) && strstr(mirror,expected)!=NULL);
        CHECK(calls==1 && writes==1);
    } else if (!strcmp(name, "positional")) {
        const char *fmt="%2$d:%1$s";
        expect(4,tag,fmt); returned(__wl_ttlog_00000659(4,tag,fmt,"value",73));
        CHECK(!strcmp(backend_text,"73:value") && calls==1 && writes<=1);
    } else if (!strcmp(name, "long-format")) {
        char fmt[5001]; memset(fmt,'Q',5000);fmt[5000]=0;
        expect(4,tag,fmt);returned(__wl_ttlog_00000659(4,tag,fmt));
        CHECK(!strcmp(backend_text,fmt) && calls==1 && writes<=1);
    } else if (!strcmp(name, "long")) {
        char long_tag[1600], payload[4000];
        memset(long_tag, 'T', sizeof(long_tag) - 1); long_tag[1599] = 0;
        memset(payload, 'P', sizeof(payload) - 1); payload[3999] = 0;
        expect(4, long_tag, "%s");
        returned(__wl_ttlog_00000659(4, long_tag, expected_format, payload));
        CHECK(calls == 1 && writes == 1 && bytes <= 1024);
        CHECK(!strcmp(backend_text, payload));
    } else if (!strcmp(name, "write-error") || !strcmp(name, "short-write")) {
        write_mode = !strcmp(name, "write-error") ? 1 : 2;
        expect(4, tag, "safe=%d");
        returned(__wl_ttlog_00000659(4, tag, expected_format, 71));
        CHECK(calls == 1 && writes == 1);
        CHECK(!strcmp(backend_text, "safe=71"));
    } else if (!strcmp(name, "null-tag")) {
        expect(4, NULL, "safe");
        returned(__wl_ttlog_00000659(4, NULL, expected_format));
        CHECK(calls == 1 && writes == 1);
    } else return 2;
    printf("{\"case\":\"%s\",\"backend_calls\":%d,\"write_attempts\":%d,"
           "\"requested_bytes\":%zu,\"failures\":%d}\n",
           argv[1], (int)calls, (int)writes, (size_t)bytes, (int)violations);
    return violations ? 1 : 0;
}
