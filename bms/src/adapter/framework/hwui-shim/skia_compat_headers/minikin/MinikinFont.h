#ifndef MINIKIN_MINIKINFONT_H_STUB
#define MINIKIN_MINIKINFONT_H_STUB
#include <cstdint>
#include <vector>
#include <string>
#include <memory>

#include "FamilyVariant.h"
#include "Hyphenator.h"  // P10.C: hyphen edit enum types
namespace minikin {

class FontCollection;  // forward

struct FontStyle {
    uint16_t weight = 400;
    uint8_t  slant = 0;
    enum Slant : uint8_t { kUpright = 0, kItalic = 1 };
    constexpr FontStyle() = default;
    constexpr FontStyle(uint16_t w, Slant s) : weight(w), slant((uint8_t)s) {}
};

using AxisTag = uint32_t;

struct FontVariation {
    uint32_t axisTag = 0;
    float value = 0.0f;
    FontVariation() = default;
    FontVariation(uint32_t t, float v) : axisTag(t), value(v) {}
};

struct FontFakery {
    bool mFakeBold = false;
    bool mFakeItalic = false;
    FontFakery() = default;
    FontFakery(bool b, bool i) : mFakeBold(b), mFakeItalic(i) {}
    bool isFakeBold() const { return mFakeBold; }
    bool isFakeItalic() const { return mFakeItalic; }
};

struct MinikinRect {
    float mLeft = 0;
    float mTop = 0;
    float mRight = 0;
    float mBottom = 0;
};

struct MinikinExtent {
    float ascent = 0;
    float descent = 0;
    float line_gap = 0;
};

// Bitfield shifts referenced by hwui MinikinSkia.cpp
constexpr int Embolden_Shift = 0;
constexpr int LinearMetrics_Shift = 1;
constexpr int Subpixel_Shift = 2;
constexpr int EmbeddedBitmaps_Shift = 3;
constexpr uint32_t Embolden_Flag = 1u << 0;
constexpr uint32_t LinearMetrics_Flag = 1u << 1;
constexpr uint32_t Subpixel_Flag = 1u << 2;
constexpr uint32_t EmbeddedBitmaps_Flag = 1u << 3;
constexpr uint32_t ForceAutoHinting_Flag = 1u << 4;
constexpr int ForceAutoHinting_Shift = 4;

class MinikinPaint {
public:
    inline bool operator==(const MinikinPaint& other) const {
        return size == other.size && scaleX == other.scaleX
            && skewX == other.skewX && paintFlags == other.paintFlags
            && letterSpacing == other.letterSpacing && wordSpacing == other.wordSpacing;
    }
    inline bool operator!=(const MinikinPaint& other) const { return !(*this == other); }
public:
    float size = 14.0f;
    float scaleX = 1.0f;
    float skewX = 0.0f;
    FontStyle fontStyle;
    int32_t letterSpacing = 0;
    int32_t wordSpacing = 0;
    uint32_t paintFlags = 0;
    uint32_t fontFlags = 0;
    uint32_t localeListId = 0;
    std::string fontFeatureSettings;
    FamilyVariant familyVariant = FamilyVariant::DEFAULT;  // alias used by some hwui code paths
    std::shared_ptr<FontCollection> font;
    MinikinPaint() = default;
    MinikinPaint(const std::shared_ptr<FontCollection>& fc) : font(fc) {}
};

enum class Bidi : uint8_t {
    LTR = 0, RTL = 1, DEFAULT_LTR = 2, DEFAULT_RTL = 3, FORCE_LTR = 4, FORCE_RTL = 5,
};

// 2026-05-02 G2.14n+: virtual method ORDER MUST match real libminikin's
// minikin/MinikinFont.h declaration order, EXACTLY:
//
//   ~MinikinFont, GetHorizontalAdvance, GetHorizontalAdvances, GetBounds,
//   GetFontExtent, GetFontPath, GetFontData, GetFontSize, GetFontIndex,
//   GetSourceId, GetAxes, createFontWithVariation
//
// Why: libhwui's MinikinFontSkia (compiled against this stub header)
// generates its vtable slot-by-slot in this declaration order.  At runtime
// libminikin.so (built with real minikin headers) dispatches virtual calls
// expecting the real declaration order.  If stub and real disagree, calls
// to typeface->GetAxes() land on a different method (e.g. GetFontData),
// returning garbage data → SIGSEGV.
//
// Previous (wrong) order: had GetSourceId/GetUniqueId/GetFontIndex/GetAxes
// before GetFontData/GetFontSize → mAxes iteration in libminikin's
// Font::prepareFont got begin=0x100 (deref of garbage vector).
//
// PROVISIONAL — when adding new virtuals here, mirror real minikin order.
// Stub class size still matches real (only vtable_ptr, no data members).
class MinikinFont {
public:
    virtual ~MinikinFont() {}
    virtual float GetHorizontalAdvance(uint32_t, const MinikinPaint&, const FontFakery&) const { return 0; }
    virtual void GetHorizontalAdvances(uint16_t*, uint32_t, const MinikinPaint&, const FontFakery&, float*) const {}
    virtual void GetBounds(MinikinRect*, uint32_t, const MinikinPaint&, const FontFakery&) const {}
    virtual void GetFontExtent(MinikinExtent*, const MinikinPaint&, const FontFakery&) const {}
    virtual const std::string& GetFontPath() const { static std::string s; return s; }
    virtual const void* GetFontData() const { return nullptr; }
    virtual size_t GetFontSize() const { return 0; }
    virtual int GetFontIndex() const { return 0; }
    virtual int GetSourceId() const { return 0; }
    virtual const std::vector<FontVariation>& GetAxes() const { static std::vector<FontVariation> v; return v; }
    virtual std::shared_ptr<MinikinFont> createFontWithVariation(const std::vector<FontVariation>&) const { return nullptr; }
    // GetUniqueId is NOT in real libminikin's vtable — keep as non-virtual to
    // preserve slot ordering.  If hwui code references it virtually, must
    // re-evaluate.
    int32_t GetUniqueId() const { return 0; }
};

class FontStub {  // helper used by Font::font field — kept for backward-compat
public:
    std::shared_ptr<MinikinFont> typeface() const {
        static std::shared_ptr<MinikinFont> defaultFont = std::make_shared<MinikinFont>();
        return defaultFont;
    }
};

// 2026-05-02 G2.14n+: Font now preserves the MinikinFont passed into Builder
// so that downstream code (libhwui's MinikinFontSkia::populateSkFont, which
// reinterpret_casts the typeface() result as MinikinFontSkia*) sees the
// REAL MinikinFontSkia instance — not a default-constructed abstract
// MinikinFont.  Previous behavior threw the MinikinFont away, and reading
// offset +4 of the abstract base returned heap-allocator metadata bytes;
// when the metadata happened to look like an SkTypeface* with refcount<=0,
// SkRefCntBase's safe_ref assert triggered sk_abort_no_print → SIGILL trap.
class Font {
public:
    Font() = default;
    FontStub* font = nullptr;  // legacy field, unused — kept for ABI compat

    // The MinikinFont this Font wraps.  Builder sets it, typeface() returns it.
    std::shared_ptr<MinikinFont> mTypeface;

    std::shared_ptr<MinikinFont> typeface() const {
        if (mTypeface) return mTypeface;
        // Defensive fallback: should never happen if Builder used correctly.
        static std::shared_ptr<MinikinFont> defaultFont = std::make_shared<MinikinFont>();
        return defaultFont;
    }
    class Builder {
    public:
        Builder(const Font& f) : mTypeface(f.mTypeface) {}
        Builder(const std::shared_ptr<MinikinFont>& tf) : mTypeface(tf) {}
        Builder& setWeight(int) { return *this; }
        Builder& setSlant(int) { return *this; }
        Builder& setStyle(FontStyle) { return *this; }
        std::shared_ptr<Font> build() {
            auto f = std::make_shared<Font>();
            f->mTypeface = mTypeface;  // PRESERVE the typeface!
            return f;
        }
    private:
        std::shared_ptr<MinikinFont> mTypeface;
    };
};

// MeasuredText defined in MeasuredText.h (P10.C)

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
    std::shared_ptr<MinikinFont> typeface() const {  // P10.C
        static std::shared_ptr<MinikinFont> defaultFont = std::make_shared<MinikinFont>();
        return defaultFont;
    }
};


inline uint32_t registerLocaleList(const std::string&) { return 0; }


class Range {
public:
    Range() = default;
    Range(uint32_t s, uint32_t e) : mStart(s), mEnd(e) {}
    uint32_t getStart() const { return mStart; }
    uint32_t getEnd() const { return mEnd; }
    uint32_t getLength() const { return mEnd - mStart; }
    // P10.C round 3: arithmetic ops used by hwui MinikinUtils.cpp
    Range operator-(size_t off) const { return Range(mStart - off, mEnd - off); }
    Range operator+(size_t off) const { return Range(mStart + off, mEnd + off); }
private:
    uint32_t mStart = 0;
    uint32_t mEnd = 0;
};

class U16StringPiece {
    const uint16_t* mData = nullptr;
    size_t mLength = 0;
public:
    U16StringPiece() = default;
    U16StringPiece(const uint16_t* d, size_t l) : mData(d), mLength(l) {}
    const uint16_t* data() const { return mData; }
    size_t size() const { return mLength; }
    size_t length() const { return mLength; }
    U16StringPiece substr(const Range& /*r*/) const { return *this; }
    U16StringPiece substr(size_t /*pos*/, size_t /*len*/) const { return *this; }
};

// P10.C round 3: free functions used by hwui/MinikinUtils.cpp
inline void getBounds(const U16StringPiece& /*text*/, const Range& /*range*/,
                      Bidi /*bidi*/, const MinikinPaint& /*paint*/,
                      StartHyphenEdit /*startHyphen*/, EndHyphenEdit /*endHyphen*/,
                      MinikinRect* out) {
    if (out) *out = MinikinRect{};
}
inline MinikinExtent getFontExtent(const U16StringPiece& /*text*/, const Range& /*range*/,
                                    Bidi /*bidi*/, const MinikinPaint& /*paint*/) {
    return MinikinExtent{};
}

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

}
#endif
