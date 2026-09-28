#!/usr/bin/env python3
# Diagnostic patch: add fprintf probes to JavaInputStreamAdaptor::doRead
# to log JNI CallIntMethod return value and buffer contents after
# GetByteArrayRegion.  Used to localize where in cross-built libhwui's
# JavaInputStreamAdaptor the data flow is corrupted.
#
# Apply:   python3 diag_patch_doread.py
# Revert:  cp .bak_pre_diag back

import sys

PATH = '/home/HanBingChen/aosp/frameworks/base/libs/hwui/jni/CreateJavaOutputStreamAdaptor.cpp'

with open(PATH) as f:
    s = f.read()

if '[doRead-DIAG]' in s:
    print('Already patched, skipping')
    sys.exit(0)

# Insert <cstdio> include if missing
if '#include <cstdio>' not in s:
    s = s.replace('#include "Utils.h"', '#include "Utils.h"\n#include <cstdio>')

# Probe 1: after CallIntMethod, before checkException
old1 = '''            jint n = env->CallIntMethod(fJavaInputStream,
                                        gInputStream_readMethodID, fJavaByteArray, 0, requested);
            if (checkException(env)) {'''
new1 = '''            jint n = env->CallIntMethod(fJavaInputStream,
                                        gInputStream_readMethodID, fJavaByteArray, 0, requested);
            fprintf(stderr, "[doRead-DIAG] CallIntMethod requested=%d returned=%d capacity=%d totalBytesRead=%zu\\n", requested, n, fCapacity, fBytesRead);
            if (checkException(env)) {'''

if old1 not in s:
    print('FAIL: pattern 1 not found')
    sys.exit(1)
s = s.replace(old1, new1)

# Probe 2: after GetByteArrayRegion, dump first 8 bytes of buffer
old2 = '''            env->GetByteArrayRegion(fJavaByteArray, 0, n,
                                    reinterpret_cast<jbyte*>(buffer));
            if (checkException(env)) {'''
new2 = '''            env->GetByteArrayRegion(fJavaByteArray, 0, n,
                                    reinterpret_cast<jbyte*>(buffer));
            {
                unsigned char* b = reinterpret_cast<unsigned char*>(buffer);
                fprintf(stderr, "[doRead-DIAG] post GetByteArrayRegion n=%d buf[0..7]=%02x %02x %02x %02x %02x %02x %02x %02x\\n",
                        n,
                        n>0?b[0]:0, n>1?b[1]:0, n>2?b[2]:0, n>3?b[3]:0,
                        n>4?b[4]:0, n>5?b[5]:0, n>6?b[6]:0, n>7?b[7]:0);
            }
            if (checkException(env)) {'''

if old2 not in s:
    print('FAIL: pattern 2 not found')
    sys.exit(1)
s = s.replace(old2, new2)

with open(PATH, 'w') as f:
    f.write(s)

print('PATCH OK')
