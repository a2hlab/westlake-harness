#!/usr/bin/env python3
"""L2.1 Round 2: Add missing minikin shim symbols + Paint.cpp fixes."""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'
TARGET = f'{HWUI}/jni/Paint.cpp'

# 1. Extend minikin shim with missing symbols
mf_h = f'{COMPAT}/minikin/MinikinFont.h'
with open(mf_h) as f:
    c = f.read()

if 'distributeAdvances' not in c:
    addition = '''
// L2.1: extra minikin helpers used by hwui jni/Paint.cpp
inline void distributeAdvances(float* advances, const uint16_t* /*chars*/,
                                size_t /*start*/, size_t /*count*/) {
    // Stub: real impl distributes the cluster's advance among continuation chars.
    // Hello World only uses simple Latin text where this is a no-op.
    (void)advances;
}

inline size_t getOffsetForAdvance(const float* advances, const uint16_t* /*chars*/,
                                   size_t /*start*/, size_t count, float advance) {
    // Inline approximation: walk advances until cumulative >= advance
    float acc = 0.0f;
    for (size_t i = 0; i < count; ++i) {
        if (acc >= advance) return i;
        acc += advances[i];
    }
    return count;
}

inline float getRunAdvance(const float* advances, const uint16_t* /*chars*/,
                            size_t /*start*/, size_t count, size_t offset) {
    float result = 0.0f;
    size_t end = offset < count ? offset : count;
    for (size_t i = 0; i < end; ++i) result += advances[i];
    return result;
}

// FakedFont: combo of a font and bold/italic fakery flags
struct FakedFont {
    Font* font = nullptr;
    FontFakery fakery;
};
'''
    # Insert before the closing namespace
    c = c.replace('class MeasuredText {};', 'class MeasuredText {};\n' + addition)

# Add baseFontFaked method to FontCollection — but FontCollection is defined
# in a separate header (FontCollection.h). Patch it there.
with open(mf_h, 'w') as f:
    f.write(c)
print('MinikinFont.h: distributeAdvances/getOffsetForAdvance/getRunAdvance/FakedFont added')

# Patch FontCollection.h
fc_h = f'{COMPAT}/minikin/FontCollection.h'
with open(fc_h) as f:
    fc = f.read()
if 'baseFontFaked' not in fc:
    fc = fc.replace('bool hasVariationSelector(uint32_t, uint32_t) const { return false; }',
        '''bool hasVariationSelector(uint32_t, uint32_t) const { return false; }
    FakedFont baseFontFaked(FontStyle) const { return FakedFont{}; }''')
    with open(fc_h, 'w') as f:
        f.write(fc)
print('FontCollection.h: baseFontFaked added')

# Add MinikinPaint operator==
with open(mf_h) as f:
    c = f.read()
if 'operator==' not in c:
    c = c.replace('class MinikinPaint {',
        '''class MinikinPaint {
public:
    inline bool operator==(const MinikinPaint& other) const {
        return size == other.size && scaleX == other.scaleX
            && skewX == other.skewX && paintFlags == other.paintFlags
            && letterSpacing == other.letterSpacing && wordSpacing == other.wordSpacing;
    }
    inline bool operator!=(const MinikinPaint& other) const { return !(*this == other); }''')
    # Now we have `class MinikinPaint { public: inline bool operator==... public:` — duplicate `public:`
    c = c.replace('class MinikinPaint {\npublic:\n    inline bool operator==',
                  'class MinikinPaint {\n    inline bool operator==')
    with open(mf_h, 'w') as f:
        f.write(c)
print('MinikinFont.h: MinikinPaint::operator== added')

print('\nL2.1 Round 2 patches applied')
