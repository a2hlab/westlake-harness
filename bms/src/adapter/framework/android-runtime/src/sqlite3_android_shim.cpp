/*
 * sqlite3_android_shim.cpp — adapter minimal, no-ICU implementation of the
 * two AOSP sqlite3_android entry points referenced by
 * android_database_SQLiteConnection.cpp / android_database_SQLiteGlobal.cpp.
 *
 * Why a shim (and not the real external/sqlite/android/sqlite3_android.cpp):
 *   The real implementation drags in ICU (unicode/ucol.h, uiter, ustring) and
 *   PhoneNumberUtils (libphonenumber).  Those Android telephony/contacts
 *   collators & SQL functions are NOT used by Room / androidx.sqlite, which is
 *   all noice needs.  Pulling ICU + libphonenumber into liboh_android_runtime
 *   would explode the dependency surface for zero benefit on this wall.
 *
 * What nativeOpen actually needs (android_database_SQLiteConnection.cpp:165):
 *   err = register_android_functions(db, UTF16_STORAGE);   // must return SQLITE_OK
 *   ...and any schema column declared `COLLATE LOCALIZED|UNICODE|PHONEBOOK`
 *   must resolve at prepare() time, else "no such collation sequence".
 *
 * So this shim registers LOCALIZED / UNICODE / PHONEBOOK collation names
 * (both UTF8 and UTF16 text-reps) backed by a plain byte comparator
 * (BINARY-equivalent).  Existence is what matters for prepare(); ordering is
 * locale-naive but correct enough for Room's internal bookkeeping and for any
 * app that doesn't rely on locale collation order.  No custom SQL functions
 * are registered (Room uses none of _DELETE_FILE/_LOG/PHONE_NUMBERS_EQUAL/...).
 *
 * HanBing 铁律 3 compliant: native IPC-boundary adapter code in
 * liboh_android_runtime.so, no ART / class_linker / vtable involvement.
 */

#include <string.h>
#include <sqlite3.h>

extern "C" {

// Plain byte comparator for UTF8 collation (BINARY-equivalent, but registered
// under the Android collation names so schemas referencing them prepare OK).
static int coll_utf8(void* /*arg*/, int llen, const void* lhs,
                     int rlen, const void* rhs) {
    int n = llen < rlen ? llen : rlen;
    int c = (n > 0) ? memcmp(lhs, rhs, (size_t)n) : 0;
    if (c != 0) return c < 0 ? -1 : 1;
    if (llen == rlen) return 0;
    return llen < rlen ? -1 : 1;
}

// 16-bit code-unit comparator for UTF16 collation.
static int coll_utf16(void* /*arg*/, int llen, const void* lhs,
                      int rlen, const void* rhs) {
    const unsigned short* a = (const unsigned short*)lhs;
    const unsigned short* b = (const unsigned short*)rhs;
    int an = llen / 2, bn = rlen / 2;
    int n = an < bn ? an : bn;
    for (int i = 0; i < n; ++i) {
        if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
    }
    if (an == bn) return 0;
    return an < bn ? -1 : 1;
}

static void register_one(sqlite3* handle, const char* name) {
    if (!handle) return;
    sqlite3_create_collation(handle, name, SQLITE_UTF8,  nullptr, coll_utf8);
    sqlite3_create_collation(handle, name, SQLITE_UTF16, nullptr, coll_utf16);
}

// AOSP signature: int register_android_functions(sqlite3*, int uit16Storage)
int register_android_functions(sqlite3* handle, int /*utf16Storage*/) {
    register_one(handle, "LOCALIZED");
    register_one(handle, "UNICODE");
    register_one(handle, "PHONEBOOK");
    return SQLITE_OK;
}

// AOSP signature: int register_localized_collators(sqlite3*, const char* locale, int utf16Storage)
int register_localized_collators(sqlite3* handle, const char* /*systemLocale*/,
                                 int /*utf16Storage*/) {
    register_one(handle, "LOCALIZED");
    register_one(handle, "PHONEBOOK");
    return SQLITE_OK;
}

}  // extern "C"
