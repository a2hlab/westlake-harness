#!/usr/bin/env python3
"""L2.1: Real implementation of jni/Paint.cpp.

The file is currently #if 0 stubbed (round 5+). We:
1. Remove the #if 0 ... #endif wrappers
2. Fix the corrupted doRunAdvance() — restore minikin::getRunAdvance() with
   an inline computation (sum of per-character advances up to offset).
3. Restore the U16_GET_SUPPLEMENTARY include if missing
"""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
TARGET = f'{HWUI}/jni/Paint.cpp'

bak = TARGET + '.bak.l21'
if not os.path.exists(bak):
    shutil.copy(TARGET, bak)
shutil.copy(bak, TARGET)

with open(TARGET) as f:
    c = f.read()

# 1. Remove #if 0 / #endif wrappers
c = re.sub(r'^#if 0  // OH adapter Paint stub\n', '', c, flags=re.MULTILINE)
# Remove the matching #endif at end of file
# (it's the last #endif before any potential trailing whitespace)
lines = c.rstrip().splitlines()
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip() == '#endif':
        lines.pop(i)
        break
c = '\n'.join(lines) + '\n'

# 2. Fix the corrupted doRunAdvance line
broken = '        float result = 0.0f, buf, start, count, offset);'
fixed = '''        // L2.1: minikin::getRunAdvance computes cumulative advance up to `offset`
        // (advance is on the first char of each grapheme cluster, 0 on continuations).
        // Inline replacement to avoid dependence on minikin internal API:
        float result = 0.0f;
        for (jint i = 0; i < offset; ++i) {
            result += advancesArray[i];
        }'''

if broken in c:
    c = c.replace(broken, fixed)
    print('Fixed doRunAdvance corruption')
else:
    print('WARN: doRunAdvance broken pattern not found - may already be fixed')

# 3. Make sure U16_GET_SUPPLEMENTARY is defined (was added by an earlier round)
if 'U16_GET_SUPPLEMENTARY' not in c:
    c = '#ifndef U16_GET_SUPPLEMENTARY\n#define U16_GET_SUPPLEMENTARY(lead, trail) (((lead) << 10UL) + (trail) - 0x35FDC00UL)\n#endif\n' + c

with open(TARGET, 'w') as f:
    f.write(c)

print(f'Patched: {os.path.basename(TARGET)}')
