#ifndef MINIKIN_MEASUREDTEXT_H_STUB
#define MINIKIN_MEASUREDTEXT_H_STUB
#include "MinikinFont.h"
#include "Layout.h"
namespace minikin {
class Run {};
class StyleRun {};
class MeasuredText {
public:
    MeasuredText() = default;
    // P10.C round 3: signature matches hwui/MinikinUtils.cpp call
    Layout buildLayout(const class U16StringPiece& /*text*/, const class Range& /*range*/,
                       const class Range& /*contextRange*/, const class MinikinPaint& /*paint*/,
                       StartHyphenEdit /*startHyphen*/ = (StartHyphenEdit)0,
                       EndHyphenEdit /*endHyphen*/ = (EndHyphenEdit)0) const {
        return Layout{};
    }
};
}
#endif
