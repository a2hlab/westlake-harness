#include "lodepng.h"
#include "icon_normalize.h"
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
namespace {
void Check(bool pass, const char* signal)
{
    if (!pass) { std::fprintf(stderr, "%s\n", signal); std::exit(1); }
}
std::vector<unsigned char> Png(bool transparent)
{
    std::vector<unsigned char> rgba(16*16*4, 0), png;
    if (!transparent) for (unsigned y=4; y<12; ++y) for (unsigned x=4; x<12; ++x) {
        const auto i=(y*16+x)*4; rgba[i]=255; rgba[i+3]=255;
    }
    Check(lodepng::encode(png, rgba, 16, 16) == 0, "SPC49_REAL_PNG_ENCODE");
    return png;
}
}
int main(int argc, char** argv)
{
    Check(argc == 2, "SPC49_PROBE_ARGUMENT");
    const bool valid = std::string(argv[1]) == "valid";
    if (valid) {
        auto png=Png(false); const auto original=png;
        std::vector<unsigned char> rgba; unsigned width=0,height=0;
        Check(lodepng::decode(rgba,width,height,png)==0 && width==16 && height==16 && rgba.size()==1024,
            "SPC49_REAL_PNG_DECODE");
        Check(rgba[0]==0 && rgba[(4*16+4)*4]==255, "SPC49_PIXELS_ROUNDTRIP");
        Check(oh_adapter::NormalizeLauncherIconPng(png) && png != original, "SPC49_ICON_TRANSFORM");
        rgba.clear();
        Check(lodepng::decode(rgba,width,height,png)==0 && width==16 && height==16 && rgba[3]==255,
            "SPC49_TRANSFORMED_PIXELS");
    } else {
        for (auto png : {std::vector<unsigned char>{0,1,2,3}, std::vector<unsigned char>{137,80,78,71}}) {
            const auto original=png; std::vector<unsigned char> rgba; unsigned width=0,height=0;
            Check(lodepng::decode(rgba,width,height,png)!=0, "SPC49_CORRUPT_PNG_REJECTED");
            Check(!oh_adapter::NormalizeLauncherIconPng(png) && png==original, "SPC49_CORRUPT_INPUT_PRESERVED");
        }
        auto png=Png(false); png.resize(png.size()/2); const auto truncated=png;
        Check(!oh_adapter::NormalizeLauncherIconPng(png) && png==truncated, "SPC49_TRUNCATED_INPUT_PRESERVED");
        auto empty=Png(true); const auto original=empty;
        Check(!oh_adapter::NormalizeLauncherIconPng(empty) && empty==original, "SPC49_TRANSPARENT_NOOP");
    }
    std::puts("SPC49_PRODUCTION_CODEC_PASS");
}
