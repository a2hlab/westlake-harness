#!/usr/bin/env python3
"""L2.2: un-stub jni/Typeface.cpp and fix M133 API differences."""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
TARGET = f'{HWUI}/jni/Typeface.cpp'

bak = TARGET + '.bak.l22'
if not os.path.exists(bak):
    shutil.copy(TARGET, bak)
shutil.copy(bak, TARGET)

with open(TARGET) as f:
    c = f.read()

# Strip #if 0 wrapper
c = re.sub(r'^#if 0  // OH adapter Typeface stub\n', '', c, flags=re.MULTILINE)
lines = c.rstrip().splitlines()
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip() == '#endif':
        lines.pop(i)
        break
c = '\n'.join(lines) + '\n'

# Fix M133 API issues (cumulative — re-apply earlier round 5/6 patches):
# 1. SkTypeface::MakeFromStream removed → return empty sk_sp
c = re.sub(r'sk_sp<SkTypeface>\s+typeface\s*=\s*SkTypeface::MakeFromStream\([^)]*\)\s*;',
           'sk_sp<SkTypeface> typeface(nullptr); /* M133: MakeFromStream removed */', c)
# 2. .font->typeface() (legacy minikin Font::font) → .typeface()
c = re.sub(r'\.font->typeface\(\)', '.typeface()', c)
# 3. minikin::Font::Builder → use the shim's Builder
# (already in our shim, no source change needed)

with open(TARGET, 'w') as f:
    f.write(c)
print(f'Patched: {os.path.basename(TARGET)}')
