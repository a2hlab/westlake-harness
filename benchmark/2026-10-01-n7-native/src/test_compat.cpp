// Host regression test for __gnu_strerror_r and android_dlopen_ext.
//
// Compile with OH clang (aarch64-linux-ohos target) or host clang for smoke.
// Verifies: strerror_r returns buf, truncation correct, unknown errno format;
// dlopen_ext with NULL extinfo behaves identically to dlopen.

#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

extern "C" char *__gnu_strerror_r(int errnum, char *buf, size_t buflen);
extern "C" void *android_dlopen_ext(const char *filename, int flags, const void *extinfo);

static int failures = 0;

static void Check(bool ok, const char *what)
{
    if (!ok) {
        printf("FAIL: %s\n", what);
        failures++;
    } else {
        printf("PASS: %s\n", what);
    }
}

int main()
{
    // ── __gnu_strerror_r ──
    char buf[256];

    // 1. Returns buf (not a static string).
    char *r1 = __gnu_strerror_r(ENOENT, buf, sizeof(buf));
    Check(r1 == buf, "strerror_r returns caller buf");

    // 2. Content is a readable error string.
    Check(strlen(buf) > 0, "strerror_r writes non-empty string");
    Check(strstr(buf, "No such file") != nullptr || strstr(buf, "ENOENT") != nullptr ||
          strstr(buf, "2") != nullptr,
          "strerror_r contains error text");

    // 3. Truncation: small buffer, string fits with NUL.
    char small[8];
    char *r2 = __gnu_strerror_r(ENOENT, small, sizeof(small));
    Check(r2 == small, "strerror_r small buf returns buf");
    Check(small[sizeof(small) - 1] == '\0', "strerror_r truncates with NUL");
    Check(strlen(small) <= sizeof(small) - 1, "strerror_r respects buflen");

    // 4. Unknown errno: format "Unknown error %d".
    char unk[64];
    char *r3 = __gnu_strerror_r(99999, unk, sizeof(unk));
    Check(r3 == unk, "strerror_r unknown errno returns buf");
    Check(strstr(unk, "Unknown error") != nullptr || strstr(unk, "99999") != nullptr,
          "strerror_r unknown errno format");

    // 5. NULL/edge cases don't crash.
    char *r4 = __gnu_strerror_r(ENOENT, nullptr, 0);
    Check(r4 != nullptr, "strerror_r NULL buf returns fallback");

    // ── android_dlopen_ext ──
    // 6. NULL extinfo behaves like dlopen (success on a system lib).
    #if defined(__APPLE__)
    const char *syslib = "libSystem.B.dylib";
#else
    const char *syslib = "libc.so";
#endif
    void *h1 = android_dlopen_ext(syslib, RTLD_NOW, nullptr);
    void *h2 = dlopen(syslib, RTLD_NOW);
    Check((h1 != nullptr) == (h2 != nullptr), "dlopen_ext NULL extinfo matches dlopen result");
    if (h1) dlclose(h1);
    if (h2) dlclose(h2);

    // 7. NULL extinfo on nonexistent lib matches dlopen failure.
    void *h3 = android_dlopen_ext("libnonexistent_xyz.so", RTLD_NOW, nullptr);
    void *h4 = dlopen("libnonexistent_xyz.so", RTLD_NOW);
    Check((h3 == nullptr) == (h4 == nullptr), "dlopen_ext NULL extinfo matches dlopen failure");
    if (h3) dlclose(h3);
    if (h4) dlclose(h4);

    // 8. RTLD flag passthrough (RTLD_NOW vs RTLD_LAZY both accepted).
    void *h5 = android_dlopen_ext(syslib, RTLD_LAZY, nullptr);
    void *h6 = dlopen(syslib, RTLD_LAZY);
    Check((h5 != nullptr) == (h6 != nullptr), "dlopen_ext RTLD_LAZY matches dlopen");
    if (h5) dlclose(h5);
    if (h6) dlclose(h6);

    printf(failures == 0 ? "ALL PASS\n" : "FAILURES: %d\n", failures);
    return failures;
}
