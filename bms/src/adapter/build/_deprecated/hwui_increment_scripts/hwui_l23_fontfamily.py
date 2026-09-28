#!/usr/bin/env python3
"""L2.3: un-stub jni/FontFamily.cpp + add FontFamily::create + Variant to shim."""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'
TARGET = f'{HWUI}/jni/FontFamily.cpp'

bak = TARGET + '.bak.l23'
if not os.path.exists(bak):
    shutil.copy(TARGET, bak)
shutil.copy(bak, TARGET)

with open(TARGET) as f:
    c = f.read()

# Strip #if 0 wrapper
c = re.sub(r'^#if 0  // OH adapter FontFamily stub\n', '', c, flags=re.MULTILINE)
lines = c.rstrip().splitlines()
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip() == '#endif':
        lines.pop(i)
        break
c = '\n'.join(lines) + '\n'

with open(TARGET, 'w') as f:
    f.write(c)
print(f'Patched: {os.path.basename(TARGET)}')

# Extend FontCollection.h with FontFamily::create + Variant enum
fc_h = f'{COMPAT}/minikin/FontCollection.h'
with open(fc_h) as f:
    c = f.read()
if 'static std::shared_ptr<FontFamily> create' not in c:
    c = c.replace('class FontFamily {',
        '''class FontFamily {
public:
    enum class Variant : uint8_t { DEFAULT = 0, COMPACT = 1, ELEGANT = 2 };
    static std::shared_ptr<FontFamily> create(uint32_t /*localeListId*/, Variant /*variant*/, std::vector<std::shared_ptr<class Font>>&& /*fonts*/, bool /*isCustomFallback*/, bool /*isDefaultFallback*/) {
        return std::make_shared<FontFamily>();
    }
    static std::shared_ptr<FontFamily> create(std::vector<std::shared_ptr<class Font>>&& /*fonts*/) {
        return std::make_shared<FontFamily>();
    }''')
    with open(fc_h, 'w') as f:
        f.write(c)
print('FontCollection.h: FontFamily::create added')
