#ifndef MINIKIN_FONTCOLLECTION_H_STUB
#define MINIKIN_FONTCOLLECTION_H_STUB
#include "MinikinFont.h"
#include "FamilyVariant.h"
#include <memory>
#include <vector>

namespace minikin {

class FontFamily {
public:
    using Variant = FamilyVariant;
    FontFamily() = default;
    static std::shared_ptr<FontFamily> create(
        uint32_t /*localeListId*/, FamilyVariant /*variant*/,
        std::vector<std::shared_ptr<Font>>&& /*fonts*/,
        bool /*isCustomFallback*/, bool /*isDefaultFallback*/) {
        return std::make_shared<FontFamily>();
    }
    static std::shared_ptr<FontFamily> create(
        std::vector<std::shared_ptr<Font>>&& /*fonts*/) {
        return std::make_shared<FontFamily>();
    }
    FakedFont baseFontFaked(FontStyle) const { return FakedFont{}; }
    int getSupportedAxesCount() const { return 0; }
    AxisTag getSupportedAxisAt(int) const { return 0; }
    // getCoverage stub: returns an opaque empty coverage object
    struct CoverageStub { size_t length() const { return 0; } bool get(uint32_t) const { return false; } }; CoverageStub getCoverage() const { return {}; }
    bool hasGlyph(uint32_t /*ch*/, uint32_t /*vs*/) const { return false; }
    // P10.C: API used by hwui/Typeface.cpp
    FakedFont getClosestMatch(FontStyle /*style*/) const { return FakedFont{}; }
};

// FontCollection = collection of FontFamily; aliased the same in older minikin.
class FontCollection {
public:
    FontCollection() = default;
    explicit FontCollection(std::vector<std::shared_ptr<FontFamily>>&&) {}
    static std::shared_ptr<FontCollection> create(std::vector<std::shared_ptr<FontFamily>>&&) {
        return std::make_shared<FontCollection>();
    }
    // P10.C: alias used by hwui/Typeface.cpp
    static std::shared_ptr<FontCollection> createCollectionWithFamilies(std::vector<std::shared_ptr<FontFamily>>&& families) {
        return create(std::move(families));
    }
    std::shared_ptr<FontCollection> createCollectionWithVariation(const std::vector<FontVariation>&) const {
        return std::make_shared<FontCollection>();
    }
    bool hasVariationSelector(uint32_t, uint32_t) const { return false; }
    FakedFont baseFontFaked(FontStyle) const { return FakedFont{}; }
    int getSupportedAxesCount() const { return 0; }
    AxisTag getSupportedAxisAt(int) const { return 0; }
};

}
#endif
