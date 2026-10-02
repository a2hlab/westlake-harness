#include <assert.h>
#include "zlib-route.h"

int main(void)
{
    assert(U11ZlibRoot(NULL, NULL) == NULL);
    assert(U11ZlibRoot("/data/app/ooniprobe/lib", "") == NULL);
    assert(U11ZlibRoot("/data/app/io.anuke.mindustry/lib", "") == NULL);
    assert(U11ZlibRoot("/data/app/notim.vector.app/lib", "") == NULL);
    assert(U11ZlibRoot("/data/app/im.vector.app.extra/lib", "") == NULL);
    assert(U11ZlibRoot("", "/data/app/com.emn8.mobilem8.nativeapp.bk.extra/lib") == NULL);
    assert(strcmp(U11ZlibRoot("/data/app/im.vector.app/lib", ""), "/system/android/lib64/westlake_native") == 0);
    assert(strcmp(U11ZlibRoot("", "/data/app/com.emn8.mobilem8.nativeapp.bk/lib"), "/system/android/lib64/westlake_native") == 0);
    assert(U11ZlibPackage("im.vector.app:/next", "im.vector.app"));
    assert(U11ZlibPackage("im.vector.app", "im.vector.app"));
    return 0;
}
