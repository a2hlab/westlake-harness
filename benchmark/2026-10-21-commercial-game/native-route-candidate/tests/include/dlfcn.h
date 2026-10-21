#ifndef WESTLAKE_ANL_HOST_TEST_DLFCN_H
#define WESTLAKE_ANL_HOST_TEST_DLFCN_H

#include_next <dlfcn.h>

#ifndef NS_NAME_MAX
#define NS_NAME_MAX 255
#endif

typedef struct Dl_namespace {
    char name[NS_NAME_MAX + 1];
} Dl_namespace;

#endif
