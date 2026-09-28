#!/usr/bin/env python3
# Diagnostic: log NinePatchPeeker::readChunk return path to see if
# serializedSize() != length causing PngDecoder abort.

PATH = '/home/HanBingChen/aosp/frameworks/base/libs/hwui/jni/NinePatchPeeker.cpp'

import shutil
shutil.copy(PATH, PATH + '.bak_pre_diag')

with open(PATH) as f:
    s = f.read()

# Add cstdio if missing
if '#include <cstdio>' not in s:
    s = s.replace('#include "NinePatchPeeker.h"', '#include "NinePatchPeeker.h"\n#include <cstdio>')

# Probe entry of readChunk + the npTc length check return
old_npTc = '''    if (!strcmp("npTc", tag) && length >= sizeof(Res_png_9patch)) {
        Res_png_9patch* patch = (Res_png_9patch*) data;
        size_t patchSize = patch->serializedSize();
        if (length != patchSize) {
            return false;
        }'''

new_npTc = '''    fprintf(stderr, "[NinePatchPeeker-DIAG] readChunk tag=%c%c%c%c length=%zu\\n",
            tag[0], tag[1], tag[2], tag[3], length);
    if (!strcmp("npTc", tag) && length >= sizeof(Res_png_9patch)) {
        Res_png_9patch* patch = (Res_png_9patch*) data;
        size_t patchSize = patch->serializedSize();
        fprintf(stderr, "[NinePatchPeeker-DIAG] npTc serializedSize=%zu length=%zu numXDivs=%d numYDivs=%d numColors=%d\\n",
                patchSize, length, patch->numXDivs, patch->numYDivs, patch->numColors);
        if (length != patchSize) {
            fprintf(stderr, "[NinePatchPeeker-DIAG] npTc MISMATCH — returning false (PngDecoder will abort)\\n");
            return false;
        }'''

if old_npTc in s:
    s = s.replace(old_npTc, new_npTc)
    print('NinePatchPeeker probe added')
else:
    print('FAIL: pattern not found')
    import sys
    sys.exit(1)

with open(PATH, 'w') as f:
    f.write(s)
print('OK')
