#pragma once
// 2026-06-01: forward to the REAL ui/ColorSpace.h instead of a minimal stub.
//
// The previous 3-line stub only declared android::ColorSpace::Named, which is
// fine for files that just need the enum, but utils/Color.cpp needs the full
// ColorSpace (float3/mat3 chromatic-adaptation math: srcLMS = matrix *
// srcWhitePoint, the Bradford adaptation matrices).  With SKIA_COMPAT on the
// include path BEFORE frameworks/native/libs/ui/include_types, this stub
// shadowed the real header and broke Color.cpp ("no viable conversion from
// 'float3' to 'float'", "invalid operands ('const mat3' and 'const float3')").
//
// SKIA_COMPAT's -I precedes ui/include_types, so #include_next continues the
// search and resolves to the real ui/ColorSpace.h (proven to cross-compile in
// the 0509-ok libhwui build, which had no ui/ColorSpace.h stub on its path).
// All hwui sources carry -I frameworks/native/libs/math/include, so the real
// header's float3/mat3 dependencies resolve.
#include_next <ui/ColorSpace.h>
