#include <assert.h>
#include "zlib-route.h"

int main(void)
{
    const char* root = "/system/android/lib64/westlake_native";
#ifdef U13_BASELINE_EXPECT_NO_MCD
    assert(U11ZlibRoot("/data/app/com.mcdonalds.app/lib", NULL) == NULL);
    assert(U11ZlibRoot(NULL, "/data/app/com.mcdonalds.app/lib") == NULL);
#else
    assert(strcmp(U11ZlibRoot("/data/app/com.mcdonalds.app/lib", NULL), root) == 0);
    assert(strcmp(U11ZlibRoot(NULL, "/data/app/com.mcdonalds.app/lib"), root) == 0);
#endif
    assert(strcmp(U11ZlibRoot("/data/app/im.vector.app/lib", NULL), root) == 0);
    assert(strcmp(U11ZlibRoot("/data/app/com.emn8.mobilem8.nativeapp.bk/lib", NULL), root) == 0);
    assert(U11ZlibRoot("/data/app/com.mcdonalds.app.evil/lib", NULL) == NULL);
    assert(U11ZlibRoot("/data/app/xcom.mcdonalds.app/lib", NULL) == NULL);
    assert(U11ZlibRoot("/data/app/com.other.app/lib", NULL) == NULL);
    assert(U11ZlibRoot(NULL, NULL) == NULL);
}
