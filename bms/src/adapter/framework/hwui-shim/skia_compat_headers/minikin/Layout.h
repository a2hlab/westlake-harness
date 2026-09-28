#ifndef MINIKIN_LAYOUT_H_STUB
#define MINIKIN_LAYOUT_H_STUB
#include "MinikinFont.h"
#include <cstdint>
#include <vector>
#include <memory>

#include "Hyphenator.h"  // P10.C round 2: canonical hyphen edit defs
namespace minikin {

class Layout {
public:
    static void purgeCaches() {}
public:
    Layout() = default;
    // P10.C round 3: ctor matching hwui/MinikinUtils.cpp call site
    Layout(const class U16StringPiece& /*text*/, const class Range& /*range*/,
           Bidi /*bidi*/, const class MinikinPaint& /*paint*/,
           StartHyphenEdit /*startHyphen*/ = (StartHyphenEdit)0,
           EndHyphenEdit /*endHyphen*/ = (EndHyphenEdit)0) {}

    size_t nGlyphs() const { return mGlyphCount; }
    int getGlyphCount() const { return mGlyphCount; }
    uint32_t getGlyphId(size_t i) const { (void)i; return 0; }
    float getX(size_t i) const { (void)i; return 0; }
    float getY(size_t i) const { (void)i; return 0; }

    const Font* getFont(size_t i) const {
        (void)i;
        static Font defaultFont;
        return &defaultFont;
    }

    FontFakery getFakery(size_t i) const {
        (void)i;
        return FontFakery();
    }

    void getBounds(MinikinRect* bounds) const {
        if (!bounds) return;
        bounds->mLeft = 0;
        bounds->mTop = -16;
        bounds->mRight = 0;
        bounds->mBottom = 4;
    }

    float getAdvance() const { return 0; }
    float getCharAdvance(size_t i) const { (void)i; return 0; }

    // P10.C: API used by hwui/MinikinUtils.cpp
    static float measureText(const U16StringPiece& /*text*/, const Range& /*range*/,
                              Bidi /*bidi*/, const MinikinPaint& /*paint*/,
                              StartHyphenEdit /*startHyphen*/ = (StartHyphenEdit)0,
                              EndHyphenEdit /*endHyphen*/ = (EndHyphenEdit)0,
                              float* /*advances*/ = nullptr) {
        return 0.0f;
    }

    size_t mGlyphCount = 0;
    std::vector<uint16_t> mGlyphIds;
    std::vector<float> mPositions;
};

}
#endif
