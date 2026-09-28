#!/usr/bin/env python3
"""Round 13 part 1: Patch EglManager.cpp to add missing ANativeWindow include."""
import os, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
TARGET = f'{HWUI}/renderthread/EglManager.cpp'

bak = TARGET + '.bak.r13'
if not os.path.exists(bak):
    shutil.copy(TARGET, bak)
shutil.copy(bak, TARGET)

with open(TARGET) as f:
    c = f.read()

# Add #include <android/native_window.h> after the existing #include "EglManager.h"
if '#include <android/native_window.h>' not in c:
    c = c.replace('#include "EglManager.h"',
                  '#include "EglManager.h"\n#include <android/native_window.h>')

with open(TARGET, 'w') as f:
    f.write(c)
print(f'Patched: {os.path.basename(TARGET)}')
