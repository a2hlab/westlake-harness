#ifndef WESTLAKE_U11_ZLIB_ROUTE_H
#define WESTLAKE_U11_ZLIB_ROUTE_H

#include <stdbool.h>
#include <string.h>

static bool U11ZlibPackage(const char* paths, const char* package)
{
    if (paths == NULL) return false;
    const size_t length = strlen(package);
    const char* cursor = paths;
    while ((cursor = strstr(cursor, package)) != NULL) {
        if ((cursor == paths || cursor[-1] == '/') &&
            (cursor[length] == '/' || cursor[length] == ':' || cursor[length] == '\0')) return true;
        cursor += length;
    }
    return false;
}

static const char* U11ZlibRoot(const char* search, const char* permitted)
{
    const char* packages[] = {"im.vector.app", "com.emn8.mobilem8.nativeapp.bk"};
    for (size_t index = 0; index < sizeof(packages) / sizeof(packages[0]); ++index) {
        if (U11ZlibPackage(search, packages[index]) || U11ZlibPackage(permitted, packages[index]))
            return "/system/android/lib64/westlake_native";
    }
    return NULL;
}

#endif
