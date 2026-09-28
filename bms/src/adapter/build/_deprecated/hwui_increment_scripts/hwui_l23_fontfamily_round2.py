#!/usr/bin/env python3
"""L2.3 Round 2: extend Font::Builder + FontFamily with more API."""
import os, re

COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

# 1. Update MinikinFont.h to give Font::Builder more methods
mf_h = f'{COMPAT}/minikin/MinikinFont.h'
with open(mf_h) as f:
    c = f.read()

old = '''    class Builder {
    public:
        Builder(const Font&) {}
        Builder(const std::shared_ptr<MinikinFont>&) {}
        Font build() { return Font(); }
    };'''
new = '''    class Builder {
    public:
        Builder(const Font&) {}
        Builder(const std::shared_ptr<MinikinFont>&) {}
        Builder& setWeight(int) { return *this; }
        Builder& setSlant(int) { return *this; }
        Builder& setStyle(FontStyle) { return *this; }
        std::shared_ptr<Font> build() { return std::make_shared<Font>(); }
    };'''

if old in c:
    c = c.replace(old, new)
    print('Font::Builder extended')

# Add AxisTag typedef
if 'using AxisTag' not in c and 'typedef uint32_t AxisTag' not in c:
    c = c.replace('struct FontVariation {',
        'using AxisTag = uint32_t;\n\nstruct FontVariation {')
    print('AxisTag typedef added')

with open(mf_h, 'w') as f:
    f.write(c)

# 2. Add FontFamily::create + getCoverage to FontCollection.h
# But FontFamily is the parent of FontCollection in our shim — we need to put
# create() on FontFamily, not FontCollection. Let me rewrite FontCollection.h.
fc_h = f'{COMPAT}/minikin/FontCollection.h'
with open(fc_h, 'w') as f:
    f.write('''#ifndef MINIKIN_FONTCOLLECTION_H_STUB
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
    void* getCoverage() const { return nullptr; }
    bool hasGlyph(uint32_t /*ch*/, uint32_t /*vs*/) const { return false; }
};

// FontCollection = collection of FontFamily; aliased the same in older minikin.
class FontCollection {
public:
    FontCollection() = default;
    explicit FontCollection(std::vector<std::shared_ptr<FontFamily>>&&) {}
    static std::shared_ptr<FontCollection> create(std::vector<std::shared_ptr<FontFamily>>&&) {
        return std::make_shared<FontCollection>();
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
''')
print('FontCollection.h: rewritten with FontFamily/FontCollection both having create/getCoverage')
