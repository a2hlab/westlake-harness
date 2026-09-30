#!/usr/bin/env python3
"""L2.4: un-stub jni/BitmapFactory.cpp + fix SkCanvas::ColorBehavior removal."""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
TARGET = f'{HWUI}/jni/BitmapFactory.cpp'

bak = TARGET + '.bak.l24'
if not os.path.exists(bak):
    shutil.copy(TARGET, bak)
shutil.copy(bak, TARGET)

with open(TARGET) as f:
    c = f.read()

# Strip #if 0 wrapper
c = re.sub(r'^#if 0  // OH adapter BitmapFactory stub\n', '', c, flags=re.MULTILINE)
lines = c.rstrip().splitlines()
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip() == '#endif':
        lines.pop(i)
        break
c = '\n'.join(lines) + '\n'

# SkCanvas::ColorBehavior removed in M133 — use legacy 2-arg constructor
# Pattern: SkCanvas canvas(bitmap, SkCanvas::ColorBehavior::kLegacy);
c = re.sub(
    r'SkCanvas\s+(\w+)\((\w+),\s*SkCanvas::ColorBehavior::\w+\)\s*;',
    r'SkCanvas \1(\2);  /* M133: ColorBehavior arg removed */',
    c
)

with open(TARGET, 'w') as f:
    f.write(c)
print(f'Patched: {os.path.basename(TARGET)}')
