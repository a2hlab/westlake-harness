#!/usr/bin/env python3
"""Phase 3 JNI Round 1: missing header shims for libhwui JNI files."""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

def shim(name, target):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(f'#pragma once\n#include "{target}"\n')

def stub(name, content):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write('#pragma once\n' + content)

# 1. nativehelper/JNIPlatformHelp.h - 41 files need it
stub('nativehelper/JNIPlatformHelp.h', '''#include <jni.h>
// Stub: provides a few JNI plat helpers; libnativehelper not present in adapter build.
inline jobject jniCreateFileDescriptor(JNIEnv*, int) { return nullptr; }
inline int jniGetFDFromFileDescriptor(JNIEnv*, jobject) { return -1; }
inline void jniSetFileDescriptorOfFD(JNIEnv*, jobject, int) {}
''')

# 2. FrontBufferedStream.h (Skia M133 has it under utils/)
shim('FrontBufferedStream.h', 'utils/SkFrontBufferedStream.h')

# 3. ultrahdr/jpegr.h - stub
stub('ultrahdr/jpegr.h', '''#include <cstdint>
namespace ultrahdr {
struct jpegr_uncompressed_struct { void* data; size_t length; };
struct jpegr_compressed_struct { void* data; size_t length; };
typedef int status_t;
}
''')

# 4. stats_pull_atom_callback.h
stub('stats_pull_atom_callback.h', '''typedef struct AStatsManager_PullAtomMetadata AStatsManager_PullAtomMetadata;
typedef struct AStatsEvent AStatsEvent;
typedef struct AStatsEventList AStatsEventList;
typedef int (*AStatsManager_PullAtomCallback)(int32_t, AStatsEventList*, void*);
''')

# 5. SkMalloc.h - exists in m133 under private/base
shim('SkMalloc.h', 'private/base/SkMalloc.h')

# 6. gif_lib.h - stub (used by GIFMovie which we don't really need)
stub('gif_lib.h', '''typedef struct GifFileType GifFileType;
typedef int GifByteType;
typedef int ColorMapObject;
typedef int SavedImage;
typedef int GifRecordType;
inline GifFileType* DGifOpen(void*, void*, int*) { return nullptr; }
inline int DGifSlurp(GifFileType*) { return 0; }
inline int DGifCloseFile(GifFileType*, int*) { return 0; }
''')

# 7. BitmapRegionDecoder.h (in-tree path)
stub('BitmapRegionDecoder.h', '''#include <SkBitmap.h>
class SkData;
namespace android {
class BitmapRegionDecoder {
public:
    static BitmapRegionDecoder* Create(const void*, size_t) { return nullptr; }
    static BitmapRegionDecoder* Create(SkData*) { return nullptr; }
    bool decodeRegion(SkBitmap*, void*, int, int, int, int, int, int) { return false; }
    int width() const { return 0; }
    int height() const { return 0; }
};
}
''')

# 8. androidfw/Asset.h
stub('androidfw/Asset.h', '''#include <cstddef>
#include <cstdint>
namespace android {
class Asset {
public:
    enum AccessMode { ACCESS_UNKNOWN = 0, ACCESS_RANDOM = 1, ACCESS_STREAMING = 2, ACCESS_BUFFER = 3 };
    virtual ~Asset() {}
    virtual ssize_t read(void*, size_t) = 0;
    virtual off64_t seek(off64_t, int) = 0;
    virtual void close() = 0;
    virtual const void* getBuffer(bool) = 0;
    virtual off64_t getLength() const = 0;
    virtual off64_t getRemainingLength() const = 0;
    virtual int openFileDescriptor(off64_t*, off64_t*) const = 0;
    virtual bool isAllocated() const { return false; }
    virtual const char* getAssetSource() const { return ""; }
};
}
''')

# 9. __BEGIN_DECLS / __END_DECLS macros (some headers expect bionic-style)
with open(f'{COMPAT}/hwui_force_include.h') as f:
    c = f.read()
if '__BEGIN_DECLS' not in c:
    c += '''
// bionic-style macro shims (musl/libcxx-ohos doesn't define these)
#ifndef __BEGIN_DECLS
#ifdef __cplusplus
#define __BEGIN_DECLS extern "C" {
#define __END_DECLS }
#else
#define __BEGIN_DECLS
#define __END_DECLS
#endif
#endif
'''
    with open(f'{COMPAT}/hwui_force_include.h', 'w') as f:
        f.write(c)

print('Phase 3 JNI Round 1 patches applied')
