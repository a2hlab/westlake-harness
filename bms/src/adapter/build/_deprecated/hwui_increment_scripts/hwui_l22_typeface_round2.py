#!/usr/bin/env python3
"""L2.2 Round 2: extend minikin shim with types Typeface.cpp needs."""
import os, re

COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

# Extend MinikinFont.h with missing types
mf_h = f'{COMPAT}/minikin/MinikinFont.h'
with open(mf_h) as f:
    c = f.read()

addition = '''
// L2.2: minikin types used by hwui jni/Typeface.cpp
class BufferReader {
public:
    BufferReader() = default;
    explicit BufferReader(const void*) {}
    template<typename T> T read() { return T{}; }
    const void* current() const { return nullptr; }
    size_t remaining() const { return 0; }
};

class BufferWriter {
public:
    BufferWriter() = default;
    explicit BufferWriter(void*) {}
    template<typename T> void write(const T&) {}
    size_t size() const { return 0; }
};

class MinikinFontFactory {
public:
    static MinikinFontFactory& getInstance() {
        static MinikinFontFactory instance;
        return instance;
    }
    void skip(BufferReader*) const {}
    void write(BufferWriter*, const MinikinFont*) const {}
    std::shared_ptr<MinikinFont> create(BufferReader) const { return nullptr; }
};

namespace SystemFonts {
    inline void registerFallback(const std::string&, const std::shared_ptr<FontCollection>&) {}
    inline std::shared_ptr<FontCollection> findFontCollection(const std::string&) { return nullptr; }
    inline void getFontMap(void*) {}
    inline void getFontSet(void*) {}
}
'''

if 'class BufferReader' not in c:
    # Insert at end before final closing brace
    c = c.rstrip().rstrip('}').rstrip() + addition + '\n}\n#endif\n'
    # Clean up trailing #endif if duplicated
    c = re.sub(r'#endif\s*#endif\s*$', '#endif\n', c)

with open(mf_h, 'w') as f:
    f.write(c)

# Extend FontCollection.h with getSupportedAxesCount/getSupportedAxisAt
fc_h = f'{COMPAT}/minikin/FontCollection.h'
with open(fc_h) as f:
    fc = f.read()
if 'getSupportedAxesCount' not in fc:
    fc = fc.replace('FakedFont baseFontFaked(FontStyle) const { return FakedFont{}; }',
        '''FakedFont baseFontFaked(FontStyle) const { return FakedFont{}; }
    int getSupportedAxesCount() const { return 0; }
    uint32_t getSupportedAxisAt(int) const { return 0; }''')
    with open(fc_h, 'w') as f:
        f.write(fc)

print('L2.2 round 2: minikin shims extended')
